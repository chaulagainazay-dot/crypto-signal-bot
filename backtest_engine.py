#!/usr/bin/env python3
"""
backtest_engine.py
Real backtesting engine for the crypto signal bot.

Fetches historical OHLCV from Binance public API (free, no key required),
computes technical indicators, runs a candle-by-candle walk-forward backtest,
and outputs metrics + an HTML report with charts.

Usage:
    python backtest_engine.py
    python backtest_engine.py --coins BTC ETH --timeframes 1h 4h
"""

import argparse
import base64
import io
import json
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# Technical indicators — ta library (pure Python, no C library dependencies).
# pandas-ta and ta-lib are also supported if installed; swap imports below if desired.
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange

# ── Configuration ───────────────────────────────────────────────────────────

BINANCE_API = "https://api.binance.com/api/v3/klines"
MAX_PER_REQUEST = 1000          # Binance hard limit per call
DEFAULT_TOTAL_CANDLES = 1500    # enough history for EMA200 + backtest room

# Assets & timeframes (prompt defaults)
COINS = ["BTC", "ETH", "SOL", "BNB", "XRP"]
TIMEFRAMES = ["1h", "4h", "1d"]

# Signal thresholds
RSI_LONG_MAX = 40
RSI_SHORT_MIN = 65
ADX_MIN = 20
MAX_HOLD_CANDLES = 50

# Risk / reward multipliers (ATR-based)
ENTRY_ZONE_MULT = 0.5
SL_MULT = 1.5
TP1_MULT = 3.0
TP2_MULT = 5.0

# Output files
JSON_FILE = "backtest_results.json"
HTML_FILE = "backtest_report.html"


# ── Data fetching ───────────────────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str, limit: int = 1000,
                 end_time: Optional[int] = None) -> pd.DataFrame:
    """Fetch a single chunk of OHLCV from Binance public klines endpoint."""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if end_time:
        params["endTime"] = end_time

    r = requests.get(BINANCE_API, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"Empty or invalid response for {symbol} {interval}")

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])

    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.set_index("open_time", inplace=True)
    df.sort_index(inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


def fetch_all_history(symbol: str, interval: str,
                      total_candles: int = DEFAULT_TOTAL_CANDLES) -> pd.DataFrame:
    """Paginate backwards through Binance to fetch total_candles of history."""
    chunks: List[pd.DataFrame] = []
    end_time = None
    remaining = total_candles

    while remaining > 0:
        limit = min(MAX_PER_REQUEST, remaining)
        try:
            df = fetch_klines(symbol, interval, limit=limit, end_time=end_time)
        except Exception as e:
            print(f"  [WARN] Fetch failed at end_time={end_time}: {e}")
            break

        if len(df) == 0:
            break

        chunks.append(df)
        end_time = int(df.index[0].timestamp() * 1000) - 1
        remaining -= len(df)
        time.sleep(0.25)  # be polite to Binance public API

    if not chunks:
        return pd.DataFrame()

    combined = pd.concat(chunks)
    combined = combined[~combined.index.duplicated(keep="last")]
    combined.sort_index(inplace=True)
    return combined.tail(total_candles)


# ── Indicators ──────────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute RSI, MACD, EMAs, ATR, ADX and drop warm-up rows."""
    c, h, l = df["close"], df["high"], df["low"]

    df["ema21"] = EMAIndicator(c, window=21).ema_indicator()
    df["ema200"] = EMAIndicator(c, window=200).ema_indicator()
    df["rsi"] = RSIIndicator(c, window=14).rsi()

    macd = MACD(c, window_fast=12, window_slow=26, window_sign=9)
    df["macd_hist"] = macd.macd_diff()

    df["atr"] = AverageTrueRange(h, l, c, window=14).average_true_range()
    df["adx"] = ADXIndicator(h, l, c, window=14).adx()

    return df.dropna()


# ── Signal logic ─────────────────────────────────────────────────────────────

def check_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Mark candles that satisfy the entry criteria."""
    df = df.copy()

    # Previous histogram for crossover detection
    df["macd_hist_prev"] = df["macd_hist"].shift(1)

    # LONG: RSI < 40, price > EMA21, MACD hist turns positive, ADX > 20
    long_cond = (
        (df["rsi"] < RSI_LONG_MAX)
        & (df["close"] > df["ema21"])
        & (df["macd_hist"] > 0)
        & (df["macd_hist_prev"] < 0)
        & (df["adx"] > ADX_MIN)
    )

    # SHORT: RSI > 65, price < EMA21, MACD hist turns negative, ADX > 20
    short_cond = (
        (df["rsi"] > RSI_SHORT_MIN)
        & (df["close"] < df["ema21"])
        & (df["macd_hist"] < 0)
        & (df["macd_hist_prev"] > 0)
        & (df["adx"] > ADX_MIN)
    )

    df["signal_long"] = long_cond
    df["signal_short"] = short_cond
    return df


# ── Trade simulation ─────────────────────────────────────────────────────────

def simulate_trade(df: pd.DataFrame, idx: int, direction: str) -> Optional[Dict]:
    """
    Simulate a single trade opened at candle `idx`.
    Looks ahead up to MAX_HOLD_CANDLES to find the first hit of SL / TP1 / TP2.
    Returns a trade dict or None if no future candles exist.
    """
    entry_row = df.iloc[idx]
    ema21 = entry_row["ema21"]
    atr = entry_row["atr"]

    # Entry zone midpoint used as the backtest entry price
    entry_price = ema21

    # Risk levels
    if direction == "long":
        stop = entry_price - (atr * SL_MULT)
        tp1 = entry_price + (atr * TP1_MULT)
        tp2 = entry_price + (atr * TP2_MULT)
    else:
        stop = entry_price + (atr * SL_MULT)
        tp1 = entry_price - (atr * TP1_MULT)
        tp2 = entry_price - (atr * TP2_MULT)

    future = df.iloc[idx + 1: idx + 1 + MAX_HOLD_CANDLES]
    if len(future) == 0:
        return None

    exit_price = None
    exit_reason = None
    exit_idx = None

    for j, (_, row) in enumerate(future.iterrows()):
        if direction == "long":
            # Conservative: stop-loss checked first
            if row["low"] <= stop:
                exit_price = stop
                exit_reason = "stop_loss"
                exit_idx = j
                break
            if row["high"] >= tp2:
                exit_price = tp2
                exit_reason = "tp2"
                exit_idx = j
                break
            if row["high"] >= tp1:
                exit_price = tp1
                exit_reason = "tp1"
                exit_idx = j
                break
        else:
            if row["high"] >= stop:
                exit_price = stop
                exit_reason = "stop_loss"
                exit_idx = j
                break
            if row["low"] <= tp2:
                exit_price = tp2
                exit_reason = "tp2"
                exit_idx = j
                break
            if row["low"] <= tp1:
                exit_price = tp1
                exit_reason = "tp1"
                exit_idx = j
                break

    # If nothing hit within the hold window, close at the last candle's close
    if exit_price is None:
        last = future.iloc[-1]
        exit_price = last["close"]
        exit_reason = "timeout"
        exit_idx = len(future) - 1

    # P&L calculation
    if direction == "long":
        pnl_pct = (exit_price - entry_price) / entry_price * 100.0
    else:
        pnl_pct = (entry_price - exit_price) / entry_price * 100.0

    return {
        "entry_time": entry_row.name.isoformat(),
        "exit_time": future.iloc[exit_idx].name.isoformat() if exit_idx is not None else None,
        "direction": direction,
        "entry_price": round(float(entry_price), 4),
        "exit_price": round(float(exit_price), 4),
        "stop_loss": round(float(stop), 4),
        "tp1": round(float(tp1), 4),
        "tp2": round(float(tp2), 4),
        "exit_reason": exit_reason,
        "hold_candles": (exit_idx + 1) if exit_idx is not None else len(future),
        "pnl_pct": round(float(pnl_pct), 4),
        "atr": round(float(atr), 4),
        "rsi": round(float(entry_row["rsi"]), 2),
        "adx": round(float(entry_row["adx"]), 2),
        "ema21": round(float(ema21), 4),
    }


# ── Metrics ─────────────────────────────────────────────────────────────────

def calculate_metrics(trades: List[Dict]) -> Dict:
    """Compute full backtest statistics from a list of trade dicts."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_profit_pct": 0.0,
            "avg_loss_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "avg_hold_candles": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "long_trades": 0,
            "short_trades": 0,
            "long_win_rate": 0.0,
            "short_win_rate": 0.0,
        }

    total = len(trades)
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]

    win_cnt = len(wins)
    loss_cnt = len(losses)

    win_rate = (win_cnt / total) * 100.0 if total else 0.0

    avg_profit = float(np.mean([t["pnl_pct"] for t in wins])) if wins else 0.0
    avg_loss = float(np.mean([t["pnl_pct"] for t in losses])) if losses else 0.0

    gross_profit = sum(t["pnl_pct"] for t in wins)
    gross_loss = abs(sum(t["pnl_pct"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Drawdown from equity curve (cumulative P&L after each trade)
    equity = np.cumsum([t["pnl_pct"] for t in trades])
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_drawdown = float(np.max(drawdown)) if len(drawdown) else 0.0

    # Sharpe (simplified — assumes each trade is an independent return observation)
    pnls = np.array([t["pnl_pct"] for t in trades])
    if len(pnls) > 1 and np.std(pnls) > 0:
        sharpe = float(np.mean(pnls) / np.std(pnls) * np.sqrt(len(pnls)))
    else:
        sharpe = 0.0

    avg_hold = float(np.mean([t["hold_candles"] for t in trades]))
    best = float(np.max(pnls)) if len(pnls) else 0.0
    worst = float(np.min(pnls)) if len(pnls) else 0.0

    longs = [t for t in trades if t["direction"] == "long"]
    shorts = [t for t in trades if t["direction"] == "short"]

    long_win_rate = (
        (len([t for t in longs if t["pnl_pct"] > 0]) / len(longs)) * 100.0
        if longs else 0.0
    )
    short_win_rate = (
        (len([t for t in shorts if t["pnl_pct"] > 0]) / len(shorts)) * 100.0
        if shorts else 0.0
    )

    return {
        "total_trades": total,
        "win_rate": round(win_rate, 2),
        "avg_profit_pct": round(avg_profit, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_hold_candles": round(avg_hold, 2),
        "best_trade": round(best, 4),
        "worst_trade": round(worst, 4),
        "long_trades": len(longs),
        "short_trades": len(shorts),
        "long_win_rate": round(long_win_rate, 2),
        "short_win_rate": round(short_win_rate, 2),
    }


# ── Backtest runner (single symbol/timeframe) ──────────────────────────────

def run_backtest(symbol: str, interval: str) -> Dict:
    """Run the full backtest for one symbol / timeframe combination."""
    print(f"\n[Backtest] {symbol} @ {interval}")

    try:
        df = fetch_all_history(symbol, interval)
    except Exception as e:
        print(f"  [ERROR] Failed to fetch data: {e}")
        return {"symbol": symbol, "interval": interval, "error": str(e)}

    if len(df) < 250:
        print(f"  [SKIP] Insufficient data: {len(df)} candles")
        return {"symbol": symbol, "interval": interval, "error": "Insufficient data"}

    df = compute_indicators(df)
    if len(df) < 50:
        print(f"  [SKIP] Insufficient data after indicators: {len(df)} candles")
        return {"symbol": symbol, "interval": interval,
                "error": "Insufficient data after indicators"}

    df = check_signals(df)

    trades: List[Dict] = []
    last_signal_idx = -MAX_HOLD_CANDLES  # prevent overlapping trades

    for i in range(len(df)):
        if i < 200:           # skip warm-up / indicator settling
            continue
        if i <= last_signal_idx + MAX_HOLD_CANDLES:
            continue

        if df["signal_long"].iloc[i]:
            trade = simulate_trade(df, i, "long")
            if trade:
                trades.append(trade)
                last_signal_idx = i
        elif df["signal_short"].iloc[i]:
            trade = simulate_trade(df, i, "short")
            if trade:
                trades.append(trade)
                last_signal_idx = i

    metrics = calculate_metrics(trades)

    print(f"  Trades: {metrics['total_trades']}")
    print(f"  Win Rate: {metrics['win_rate']:.2f}%")
    print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")

    return {
        "symbol": symbol,
        "interval": interval,
        "trades": trades,
        "metrics": metrics,
    }


# ── HTML report generation ───────────────────────────────────────────────────

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64


def generate_html_report(results: List[Dict]) -> str:
    """Build a self-contained HTML report with embedded matplotlib charts."""
    # Flatten all trades across symbols / timeframes
    all_trades: List[Dict] = []
    for r in results:
        if "trades" not in r or "error" in r:
            continue
        for t in r["trades"]:
            t_copy = dict(t)
            t_copy["symbol"] = r["symbol"]
            t_copy["interval"] = r["interval"]
            all_trades.append(t_copy)

    if not all_trades:
        return (
            "<!DOCTYPE html><html><body><h1>No trades found</h1></body></html>"
        )

    all_trades_sorted = sorted(all_trades, key=lambda x: x["entry_time"])
    pnls = [t["pnl_pct"] for t in all_trades_sorted]
    equity = np.cumsum(pnls).tolist()

    # ── Chart 1: Equity Curve ─────────────────────────────────────────────
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(equity, color="#2e7d32", linewidth=1.5)
    ax1.set_title("Combined Equity Curve (Cumulative P&L %)")
    ax1.set_xlabel("Trade Number")
    ax1.set_ylabel("Cumulative P&L (%)")
    ax1.grid(True, alpha=0.3)
    equity_b64 = _fig_to_base64(fig1)

    # ── Chart 2: Drawdown ───────────────────────────────────────────────────
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    equity_arr = np.array(equity)
    peak = np.maximum.accumulate(equity_arr)
    drawdown = peak - equity_arr
    ax2.fill_between(range(len(drawdown)), drawdown, color="#c62828", alpha=0.5)
    ax2.set_title("Drawdown from Peak (%)")
    ax2.set_xlabel("Trade Number")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True, alpha=0.3)
    dd_b64 = _fig_to_base64(fig2)

    # ── Chart 3: Trade Distribution ───────────────────────────────────────
    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.hist(pnls, bins=30, color="#1976d2", alpha=0.7, edgecolor="black")
    ax3.axvline(x=0, color="#c62828", linestyle="--", linewidth=2)
    ax3.set_title("Trade P&L Distribution")
    ax3.set_xlabel("P&L (%)")
    ax3.set_ylabel("Frequency")
    ax3.grid(True, alpha=0.3)
    dist_b64 = _fig_to_base64(fig3)

    # ── Chart 4: Monthly Returns ────────────────────────────────────────────
    monthly: Dict[str, float] = {}
    for t in all_trades_sorted:
        dt = datetime.fromisoformat(t["entry_time"]).strftime("%Y-%m")
        monthly[dt] = monthly.get(dt, 0.0) + t["pnl_pct"]

    months = sorted(monthly.keys())
    returns = [monthly[m] for m in months]
    bar_colors = ["#2e7d32" if r > 0 else "#c62828" for r in returns]

    fig4, ax4 = plt.subplots(figsize=(10, 4))
    ax4.bar(months, returns, color=bar_colors, alpha=0.8, edgecolor="black")
    ax4.set_title("Monthly Returns (%)")
    ax4.set_xlabel("Month")
    ax4.set_ylabel("Return (%)")
    ax4.tick_params(axis="x", rotation=45)
    ax4.axhline(y=0, color="black", linewidth=0.5)
    ax4.grid(True, alpha=0.3)
    monthly_b64 = _fig_to_base64(fig4)

    # ── Metrics table rows ──────────────────────────────────────────────────
    metric_rows = ""
    for r in results:
        if "metrics" not in r or "error" in r:
            continue
        m = r["metrics"]
        metric_rows += (
            f"<tr>"
            f"<td>{r['symbol']}</td>"
            f"<td>{r['interval']}</td>"
            f"<td>{m['total_trades']}</td>"
            f"<td>{m['win_rate']}%</td>"
            f"<td>{m['profit_factor']}</td>"
            f"<td>{m['max_drawdown']}%</td>"
            f"<td>{m['sharpe_ratio']}</td>"
            f"<td>{m['avg_hold_candles']}</td>"
            f"<td>{m['long_trades']}</td>"
            f"<td>{m['short_trades']}</td>"
            f"</tr>"
        )

    overall_total = len(all_trades)
    overall_wins = len([t for t in all_trades if t["pnl_pct"] > 0])
    overall_win_rate = (overall_wins / overall_total * 100.0) if overall_total else 0.0
    overall_pnl = sum(pnls)

    longs = [t for t in all_trades if t["direction"] == "long"]
    shorts = [t for t in all_trades if t["direction"] == "short"]

    recent_rows = ""
    for t in all_trades_sorted[-20:]:
        pnl_class = "positive" if t["pnl_pct"] > 0 else "negative"
        recent_rows += (
            f"<tr>"
            f"<td>{t['entry_time'][:19]}</td>"
            f"<td>{t['symbol']}</td>"
            f"<td>{t['direction'].upper()}</td>"
            f"<td>{t['entry_price']}</td>"
            f"<td>{t['exit_price']}</td>"
            f"<td>{t['exit_reason']}</td>"
            f"<td class='{pnl_class}'>{t['pnl_pct']}%</td>"
            f"</tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Crypto Signal Bot — Backtest Report</title>
<style>
body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 20px; background: #f5f5f5; color: #333; }}
.container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
h1, h2 {{ color: #222; margin-top: 0; }}
h1 {{ border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }}
th, td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
th {{ background: #4CAF50; color: white; font-weight: 600; }}
tr:hover {{ background: #f1f1f1; }}
.metric {{ display: inline-block; margin: 8px; padding: 14px; background: #e8f5e9; border-radius: 6px; min-width: 140px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
.metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
.metric-value {{ font-size: 22px; font-weight: bold; color: #2e7d32; margin-top: 4px; }}
.chart {{ margin: 20px 0; text-align: center; }}
.chart img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
.positive {{ color: #2e7d32; font-weight: bold; }}
.negative {{ color: #c62828; font-weight: bold; }}
.header-meta {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
</style>
</head>
<body>
<div class="container">
<h1>Crypto Signal Bot — Backtest Report</h1>
<div class="header-meta">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

<h2>Overall Summary</h2>
<div>
  <div class="metric">
    <div class="metric-label">Total Trades</div>
    <div class="metric-value">{overall_total}</div>
  </div>
  <div class="metric">
    <div class="metric-label">Win Rate</div>
    <div class="metric-value {'positive' if overall_win_rate >= 50 else 'negative'}">{overall_win_rate:.2f}%</div>
  </div>
  <div class="metric">
    <div class="metric-label">Total P&L</div>
    <div class="metric-value {'positive' if overall_pnl >= 0 else 'negative'}">{overall_pnl:.2f}%</div>
  </div>
  <div class="metric">
    <div class="metric-label">Long Trades</div>
    <div class="metric-value">{len(longs)}</div>
  </div>
  <div class="metric">
    <div class="metric-label">Short Trades</div>
    <div class="metric-value">{len(shorts)}</div>
  </div>
</div>

<h2>Per-Symbol / Timeframe Metrics</h2>
<table>
<tr>
  <th>Symbol</th><th>TF</th><th>Trades</th><th>Win Rate</th>
  <th>Profit Factor</th><th>Max DD</th><th>Sharpe</th>
  <th>Avg Hold</th><th>Longs</th><th>Shorts</th>
</tr>
{metric_rows}
</table>

<h2>Equity Curve</h2>
<div class="chart"><img src="data:image/png;base64,{equity_b64}" alt="Equity Curve"></div>

<h2>Drawdown Chart</h2>
<div class="chart"><img src="data:image/png;base64,{dd_b64}" alt="Drawdown"></div>

<h2>Trade Distribution</h2>
<div class="chart"><img src="data:image/png;base64,{dist_b64}" alt="Distribution"></div>

<h2>Monthly Returns</h2>
<div class="chart"><img src="data:image/png;base64,{monthly_b64}" alt="Monthly Returns"></div>

<h2>Recent Trades</h2>
<table>
<tr>
  <th>Entry Time</th><th>Symbol</th><th>Direction</th>
  <th>Entry</th><th>Exit</th><th>Reason</th><th>P&L</th>
</tr>
{recent_rows}
</table>
</div>
</body>
</html>"""
    return html


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Crypto Signal Bot Backtest Engine")
    parser.add_argument("--coins", nargs="+", default=COINS, help="Coins to backtest")
    parser.add_argument("--timeframes", nargs="+", default=TIMEFRAMES, help="Timeframes to backtest")
    parser.add_argument("--candles", type=int, default=DEFAULT_TOTAL_CANDLES, help="Historical candles to fetch")
    args = parser.parse_args()

    print("=" * 60)
    print("Crypto Signal Bot — Backtest Engine")
    print("=" * 60)
    print(f"Coins      : {', '.join(args.coins)}")
    print(f"Timeframes : {', '.join(args.timeframes)}")
    print(f"Candles    : {args.candles}")
    print("=" * 60)

    results: List[Dict] = []

    for coin in args.coins:
        for tf in args.timeframes:
            symbol = f"{coin}USDT"
            try:
                result = run_backtest(symbol, tf)
                results.append(result)
            except Exception as e:
                print(f"  [ERROR] {symbol} {tf}: {e}")
                results.append({
                    "symbol": symbol,
                    "interval": tf,
                    "error": str(e),
                })

    # Save JSON
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[OK] Results saved to {JSON_FILE}")

    # Generate HTML
    html = generate_html_report(results)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[OK] Report saved to {HTML_FILE}")

    # Terminal summary
    all_trades = []
    for r in results:
        if "trades" in r:
            all_trades.extend(r["trades"])

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total trades: {len(all_trades)}")
    if all_trades:
        total_pnl = sum(t["pnl_pct"] for t in all_trades)
        wins = [t for t in all_trades if t["pnl_pct"] > 0]
        losses = [t for t in all_trades if t["pnl_pct"] <= 0]
        print(f"Combined P&L: {total_pnl:.2f}%")
        print(f"Win rate: {(len(wins)/len(all_trades)*100):.2f}%")
        if wins and losses:
            pf = sum(t["pnl_pct"] for t in wins) / abs(sum(t["pnl_pct"] for t in losses))
            print(f"Profit factor: {pf:.2f}")
        if wins:
            print(f"Avg win: {np.mean([t['pnl_pct'] for t in wins]):.2f}%")
        if losses:
            print(f"Avg loss: {np.mean([t['pnl_pct'] for t in losses]):.2f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
