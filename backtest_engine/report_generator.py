#!/usr/bin/env python3
"""
report_generator.py
Generate HTML reports and embedded charts from backtest results.
"""

import base64
import io
from typing import Dict, List, Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

from .backtester import Trade
from .metrics import calculate, by_coin, by_direction, monthly


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64


def generate(trades: List[Trade], output_path: str = "backtest_report.html") -> str:
    """Generate a self-contained HTML report with all charts and tables."""
    if not trades:
        html = "<html><body><h1>No trades found</h1></body></html>"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path

    # Sort by entry time
    trades_sorted = sorted(trades, key=lambda t: t.entry_time)
    pnls = [t.pnl_pct for t in trades_sorted]
    equity = np.cumsum(pnls).tolist()
    dates = [t.entry_time[:10] for t in trades_sorted]

    # 1. Equity Curve
    fig1, ax1 = plt.subplots(figsize=(12, 5))
    ax1.plot(equity, color="#2e7d32", linewidth=1.5, label="Equity")
    ax1.axhline(y=0, color="black", linewidth=0.5, linestyle="--")
    ax1.set_title("Equity Curve (Cumulative P&L %)")
    ax1.set_xlabel("Trade Number")
    ax1.set_ylabel("Cumulative P&L (%)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    equity_b64 = _fig_to_base64(fig1)

    # 2. Drawdown Chart
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    equity_arr = np.array(equity)
    peak = np.maximum.accumulate(equity_arr)
    drawdown = peak - equity_arr
    ax2.fill_between(range(len(drawdown)), drawdown, color="#c62828", alpha=0.5, label="Drawdown")
    ax2.set_title("Drawdown from Peak (%)")
    ax2.set_xlabel("Trade Number")
    ax2.set_ylabel("Drawdown (%)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    dd_b64 = _fig_to_base64(fig2)

    # 3. Trade P&L Distribution
    fig3, ax3 = plt.subplots(figsize=(12, 5))
    ax3.hist(pnls, bins=30, color="#1976d2", alpha=0.7, edgecolor="black")
    ax3.axvline(x=0, color="#c62828", linestyle="--", linewidth=2, label="Breakeven")
    ax3.set_title("Trade P&L Distribution")
    ax3.set_xlabel("P&L (%)")
    ax3.set_ylabel("Frequency")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    dist_b64 = _fig_to_base64(fig3)

    # 4. Monthly Returns
    monthly_data = monthly(trades)
    months = sorted(monthly_data.keys())
    returns = [monthly_data[m]["avg_trade_pct"] for m in months]
    bar_colors = ["#2e7d32" if r > 0 else "#c62828" for r in returns]
    fig4, ax4 = plt.subplots(figsize=(12, 5))
    ax4.bar(months, returns, color=bar_colors, alpha=0.8, edgecolor="black")
    ax4.axhline(y=0, color="black", linewidth=0.5)
    ax4.set_title("Monthly Returns (%)")
    ax4.set_xlabel("Month")
    ax4.set_ylabel("Return (%)")
    ax4.tick_params(axis="x", rotation=45)
    ax4.grid(True, alpha=0.3)
    monthly_b64 = _fig_to_base64(fig4)

    # 5. Win Rate by Coin
    coin_data = by_coin(trades)
    coins = sorted(coin_data.keys())
    win_rates = [coin_data[c]["win_rate"] for c in coins]
    fig5, ax5 = plt.subplots(figsize=(10, 5))
    bars = ax5.barh(coins, win_rates, color=["#2e7d32" if wr >= 50 else "#c62828" for wr in win_rates])
    ax5.axvline(x=50, color="black", linewidth=0.5, linestyle="--")
    ax5.set_title("Win Rate by Coin (%)")
    ax5.set_xlabel("Win Rate (%)")
    ax5.grid(True, alpha=0.3, axis="x")
    for bar, wr in zip(bars, win_rates):
        ax5.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2, f"{wr:.1f}%", va="center")
    coin_b64 = _fig_to_base64(fig5)

    # Overall metrics
    summary = calculate(trades)
    dir_summary = by_direction(trades)

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Crypto Backtest Report</title>
<style>
body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 20px; background: #f5f5f5; color: #333; }}
.container {{ max-width: 1300px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
h1, h2 {{ color: #222; margin-top: 0; }}
h1 {{ border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 16px 0; }}
.metric-card {{ background: #e8f5e9; padding: 14px; border-radius: 6px; text-align: center; }}
.metric-label {{ font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
.metric-value {{ font-size: 20px; font-weight: bold; color: #2e7d32; margin-top: 4px; }}
.metric-value.neg {{ color: #c62828; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px; }}
th, td {{ padding: 8px; border-bottom: 1px solid #ddd; text-align: left; }}
th {{ background: #4CAF50; color: white; font-weight: 600; }}
tr:hover {{ background: #f1f1f1; }}
.positive {{ color: #2e7d32; font-weight: bold; }}
.negative {{ color: #c62828; font-weight: bold; }}
.chart {{ margin: 20px 0; text-align: center; }}
.chart img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
.header-meta {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
</style>
</head>
<body>
<div class="container">
<h1>Crypto Signal Bot — Backtest Report</h1>
<div class="header-meta">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

<h2>Overall Metrics</h2>
<div class="metric-grid">
  <div class="metric-card"><div class="metric-label">Total Trades</div><div class="metric-value">{summary['total_trades']}</div></div>
  <div class="metric-card"><div class="metric-label">Win Rate</div><div class="metric-value{' neg' if summary['win_rate'] < 50 else ''}">{summary['win_rate']:.1f}%</div></div>
  <div class="metric-card"><div class="metric-label">Profit Factor</div><div class="metric-value{' neg' if summary['profit_factor'] < 1 else ''}">{summary['profit_factor']:.2f}</div></div>
  <div class="metric-card"><div class="metric-label">Max Drawdown</div><div class="metric-value neg">{summary['max_drawdown']:.2f}%</div></div>
  <div class="metric-card"><div class="metric-label">Sharpe Ratio</div><div class="metric-value">{summary['sharpe_ratio']:.2f}</div></div>
  <div class="metric-card"><div class="metric-label">Expectancy</div><div class="metric-value{' neg' if summary['expectancy'] < 0 else ''}">{summary['expectancy']:.2f}%</div></div>
  <div class="metric-card"><div class="metric-label">Avg Trade</div><div class="metric-value{' neg' if summary['avg_trade_pct'] < 0 else ''}">{summary['avg_trade_pct']:.2f}%</div></div>
  <div class="metric-card"><div class="metric-label">Avg Win</div><div class="metric-value">{summary['avg_win_pct']:.2f}%</div></div>
  <div class="metric-card"><div class="metric-label">Avg Loss</div><div class="metric-value neg">{summary['avg_loss_pct']:.2f}%</div></div>
  <div class="metric-card"><div class="metric-label">Avg Hold</div><div class="metric-value">{summary['avg_hold_candles']:.0f} candles</div></div>
</div>

<h2>Direction Breakdown</h2>
<table>
<tr><th>Direction</th><th>Trades</th><th>Win Rate</th><th>Avg Trade</th><th>Profit Factor</th><th>Best</th><th>Worst</th></tr>
<tr><td>LONG</td><td>{dir_summary['LONG']['total_trades']}</td><td>{dir_summary['LONG']['win_rate']:.1f}%</td><td class="{'positive' if dir_summary['LONG']['avg_trade_pct'] > 0 else 'negative'}">{dir_summary['LONG']['avg_trade_pct']:.2f}%</td><td>{dir_summary['LONG']['profit_factor']:.2f}</td><td>{dir_summary['LONG']['best_trade']:.2f}%</td><td class="negative">{dir_summary['LONG']['worst_trade']:.2f}%</td></tr>
<tr><td>SHORT</td><td>{dir_summary['SHORT']['total_trades']}</td><td>{dir_summary['SHORT']['win_rate']:.1f}%</td><td class="{'positive' if dir_summary['SHORT']['avg_trade_pct'] > 0 else 'negative'}">{dir_summary['SHORT']['avg_trade_pct']:.2f}%</td><td>{dir_summary['SHORT']['profit_factor']:.2f}</td><td>{dir_summary['SHORT']['best_trade']:.2f}%</td><td class="negative">{dir_summary['SHORT']['worst_trade']:.2f}%</td></tr>
</table>

<h2>Equity Curve</h2>
<div class="chart"><img src="data:image/png;base64,{equity_b64}" alt="Equity Curve"></div>
<h2>Drawdown Chart</h2>
<div class="chart"><img src="data:image/png;base64,{dd_b64}" alt="Drawdown"></div>
<h2>Trade P&L Distribution</h2>
<div class="chart"><img src="data:image/png;base64,{dist_b64}" alt="Distribution"></div>
<h2>Monthly Returns</h2>
<div class="chart"><img src="data:image/png;base64,{monthly_b64}" alt="Monthly Returns"></div>
<h2>Win Rate by Coin</h2>
<div class="chart"><img src="data:image/png;base64,{coin_b64}" alt="Win Rate by Coin"></div>

<h2>All Trades</h2>
<table>
<tr>
  <th>#</th><th>Entry</th><th>Exit</th><th>Coin</th><th>Dir</th>
  <th>Entry $</th><th>Exit $</th><th>Reason</th><th>P&L</th><th>Hold</th>
</tr>
"""

    for i, t in enumerate(trades_sorted, 1):
        pnl_class = "positive" if t.pnl_pct > 0 else "negative"
        html += (
            f"<tr><td>{i}</td><td>{t.entry_time[:19]}</td><td>{t.exit_time[:19]}</td>"
            f"<td>{t.symbol}</td><td>{t.direction.upper()}</td>"
            f"<td>{t.entry_price}</td><td>{t.exit_price}</td><td>{t.exit_reason}</td>"
            f"<td class='{pnl_class}'>{t.pnl_pct:.2f}%</td><td>{t.hold_candles}</td></tr>"
        )

    html += "</table></div></body></html>"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
