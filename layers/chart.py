"""
Chart Generator
Produces a candlestick chart (PNG bytes) with:
  - EMA 21 / 50 / 200 overlays
  - VWAP line
  - RSI subplot
  - MACD histogram subplot
  - Buy signal markers (green ▲) and Sell signal markers (red ▼)
  - ATR-based stop / TP lines when a fresh signal exists
"""
import io
from datetime import datetime, timezone
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice

from layers.l2_technical import fetch_ohlcv


# ── Colour palette (dark theme) ───────────────────────────────────────────────
BG       = "#0d1117"
PANEL_BG = "#161b22"
TEXT     = "#e6edf3"
GRID     = "#21262d"
GREEN    = "#3fb950"
RED      = "#f85149"
YELLOW   = "#e3b341"
BLUE     = "#58a6ff"
PURPLE   = "#bc8cff"
ORANGE   = "#ffa657"
GREY     = "#8b949e"


def _candle_colors(df: pd.DataFrame):
    up = df["close"] >= df["open"]
    body_color = [GREEN if u else RED for u in up]
    wick_color = [GREEN if u else RED for u in up]
    return body_color, wick_color


async def generate_chart(
    asset: str,
    signal: Optional[dict] = None,
    timeframe: str = "1h",
    candles: int = 80,
) -> bytes:
    """
    Returns PNG image bytes.
    signal: optional dict with keys direction, entry_low, entry_high, stop_loss, tp1, tp2.
    """
    df = await fetch_ohlcv(asset, timeframe, limit=candles + 210)

    # Compute indicators
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    df["ema21"]  = EMAIndicator(c, window=21).ema_indicator()
    df["ema50"]  = EMAIndicator(c, window=50).ema_indicator()
    df["ema200"] = EMAIndicator(c, window=200).ema_indicator()
    try:
        df["vwap"] = VolumeWeightedAveragePrice(h, l, c, v).volume_weighted_average_price()
    except Exception:
        df["vwap"] = c

    macd_obj = MACD(c, window_fast=12, window_slow=26, window_sign=9)
    df["macd_hist"] = macd_obj.macd_diff()
    df["macd_line"] = macd_obj.macd()
    df["macd_signal"] = macd_obj.macd_signal()

    df["rsi"] = RSIIndicator(c, window=14).rsi()

    # Detect buy/sell crossover signals on the chart
    df["buy_signal"]  = (df["macd_hist"] > 0) & (df["macd_hist"].shift(1) <= 0) & (c > df["ema200"])
    df["sell_signal"] = (df["macd_hist"] < 0) & (df["macd_hist"].shift(1) >= 0) & (c < df["ema200"])

    # Trim to display window
    df = df.iloc[-candles:].copy()
    df = df.dropna(subset=["ema200"])

    # ── Layout ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 10), facecolor=BG)
    gs = gridspec.GridSpec(
        4, 1, figure=fig,
        height_ratios=[3.5, 1, 1, 0.8],
        hspace=0.08,
    )
    ax_candle = fig.add_subplot(gs[0])
    ax_vol    = fig.add_subplot(gs[1], sharex=ax_candle)
    ax_rsi    = fig.add_subplot(gs[2], sharex=ax_candle)
    ax_macd   = fig.add_subplot(gs[3], sharex=ax_candle)

    for ax in (ax_candle, ax_vol, ax_rsi, ax_macd):
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=GREY, labelsize=8)
        ax.spines[:].set_color(GRID)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()

    plt.setp(ax_candle.get_xticklabels(), visible=False)
    plt.setp(ax_vol.get_xticklabels(), visible=False)
    plt.setp(ax_rsi.get_xticklabels(), visible=False)

    x = np.arange(len(df))
    dates = df.index

    # ── Candlesticks ──────────────────────────────────────────────────────────
    width = 0.6
    for i, (_, row) in enumerate(df.iterrows()):
        color = GREEN if row["close"] >= row["open"] else RED
        # Body
        ax_candle.bar(
            x[i], abs(row["close"] - row["open"]),
            bottom=min(row["open"], row["close"]),
            width=width, color=color, linewidth=0,
        )
        # Wick
        ax_candle.plot(
            [x[i], x[i]], [row["low"], row["high"]],
            color=color, linewidth=0.8,
        )

    # ── EMA lines ─────────────────────────────────────────────────────────────
    ax_candle.plot(x, df["ema21"].values,  color=YELLOW, linewidth=1.0, label="EMA21",  alpha=0.9)
    ax_candle.plot(x, df["ema50"].values,  color=ORANGE, linewidth=1.0, label="EMA50",  alpha=0.9)
    ax_candle.plot(x, df["ema200"].values, color=PURPLE, linewidth=1.2, label="EMA200", alpha=0.9)
    ax_candle.plot(x, df["vwap"].values,   color=BLUE,   linewidth=0.9, label="VWAP",   alpha=0.7, linestyle="--")

    # ── Buy / Sell signal markers ─────────────────────────────────────────────
    buy_x  = x[df["buy_signal"].values]
    buy_y  = df["low"].values[df["buy_signal"].values] * 0.999
    sell_x = x[df["sell_signal"].values]
    sell_y = df["high"].values[df["sell_signal"].values] * 1.001

    ax_candle.scatter(buy_x,  buy_y,  marker="^", color=GREEN, s=80, zorder=5, label="Buy signal")
    ax_candle.scatter(sell_x, sell_y, marker="v", color=RED,   s=80, zorder=5, label="Sell signal")

    # ── Signal levels (if a live signal is passed) ────────────────────────────
    if signal:
        entry = (signal["entry_low"] + signal["entry_high"]) / 2
        sl    = signal["stop_loss"]
        tp1   = signal["tp1"]
        tp2   = signal["tp2"]
        ax_candle.axhline(entry, color=BLUE,   linewidth=1.0, linestyle="-",  alpha=0.9, label=f"Entry {entry:,.2f}")
        ax_candle.axhline(sl,    color=RED,    linewidth=1.0, linestyle="--", alpha=0.8, label=f"SL {sl:,.2f}")
        ax_candle.axhline(tp1,   color=GREEN,  linewidth=1.0, linestyle="--", alpha=0.8, label=f"TP1 {tp1:,.2f}")
        ax_candle.axhline(tp2,   color=GREEN,  linewidth=0.8, linestyle=":",  alpha=0.6, label=f"TP2 {tp2:,.2f}")

        # Fill between entry and SL (risk zone) and entry and TP1 (reward zone)
        ax_candle.axhspan(min(entry, sl), max(entry, sl), alpha=0.07, color=RED)
        ax_candle.axhspan(min(entry, tp1), max(entry, tp1), alpha=0.07, color=GREEN)

    # ── Candle axis styling ───────────────────────────────────────────────────
    legend = ax_candle.legend(
        loc="upper left", fontsize=7, facecolor=PANEL_BG,
        edgecolor=GRID, labelcolor=TEXT, ncol=4,
    )
    asset_clean = asset.replace("/", "")
    price_now = float(df["close"].iloc[-1])
    fmt_p = f"${price_now:,.2f}" if price_now >= 1 else f"${price_now:.6f}"
    ax_candle.set_title(
        f"  {asset_clean}  {timeframe.upper()}  ·  {fmt_p}  ·  "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        color=TEXT, fontsize=11, loc="left", pad=8,
    )
    ax_candle.grid(color=GRID, linewidth=0.5, alpha=0.6)
    ax_candle.set_ylabel("Price", color=GREY, fontsize=8)

    # ── Volume bars ───────────────────────────────────────────────────────────
    vol_colors = [GREEN if df["close"].iloc[i] >= df["open"].iloc[i] else RED for i in range(len(df))]
    ax_vol.bar(x, df["volume"].values, color=vol_colors, alpha=0.6, linewidth=0)
    ax_vol.set_ylabel("Volume", color=GREY, fontsize=7)
    ax_vol.grid(color=GRID, linewidth=0.4, alpha=0.4)

    # ── RSI panel ─────────────────────────────────────────────────────────────
    rsi_vals = df["rsi"].values
    ax_rsi.plot(x, rsi_vals, color=YELLOW, linewidth=1.0)
    ax_rsi.axhline(70, color=RED,   linewidth=0.7, linestyle="--", alpha=0.6)
    ax_rsi.axhline(30, color=GREEN, linewidth=0.7, linestyle="--", alpha=0.6)
    ax_rsi.axhline(50, color=GREY,  linewidth=0.5, linestyle=":",  alpha=0.4)
    ax_rsi.fill_between(x, rsi_vals, 70, where=(rsi_vals >= 70), alpha=0.15, color=RED)
    ax_rsi.fill_between(x, rsi_vals, 30, where=(rsi_vals <= 30), alpha=0.15, color=GREEN)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel("RSI", color=GREY, fontsize=7)
    ax_rsi.grid(color=GRID, linewidth=0.4, alpha=0.4)
    rsi_now = rsi_vals[-1]
    ax_rsi.text(
        x[-1] + 0.5, rsi_now, f"{rsi_now:.0f}",
        color=YELLOW, fontsize=7, va="center",
    )

    # ── MACD panel ────────────────────────────────────────────────────────────
    hist = df["macd_hist"].values
    hist_colors = [GREEN if v >= 0 else RED for v in hist]
    ax_macd.bar(x, hist, color=hist_colors, alpha=0.7, linewidth=0)
    ax_macd.plot(x, df["macd_line"].values,   color=BLUE,   linewidth=0.8, label="MACD")
    ax_macd.plot(x, df["macd_signal"].values, color=ORANGE, linewidth=0.8, label="Signal")
    ax_macd.axhline(0, color=GREY, linewidth=0.5, alpha=0.5)
    ax_macd.set_ylabel("MACD", color=GREY, fontsize=7)
    ax_macd.grid(color=GRID, linewidth=0.4, alpha=0.4)

    # ── X-axis labels ─────────────────────────────────────────────────────────
    tick_step = max(1, len(df) // 10)
    tick_positions = x[::tick_step]
    tick_labels = [dates[i].strftime("%m/%d %H:%M") for i in range(0, len(df), tick_step)]
    ax_macd.set_xticks(tick_positions)
    ax_macd.set_xticklabels(tick_labels, rotation=30, ha="right", fontsize=7, color=GREY)

    # ── Watermark ─────────────────────────────────────────────────────────────
    fig.text(
        0.5, 0.01,
        "@hcglivesignalbot  •  Paper trade only  •  Not financial advice",
        ha="center", fontsize=7, color=GREY, alpha=0.7,
    )

    plt.tight_layout(rect=[0, 0.02, 1, 1])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
