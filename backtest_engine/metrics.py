#!/usr/bin/env python3
"""
metrics.py
Performance and risk metric calculations from a list of Trade objects.
"""

from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime

import numpy as np
from statistics import mean, stdev

from .backtester import Trade


def calculate(trades: List[Trade]) -> Dict[str, Any]:
    """Return full metrics dictionary from a list of trades."""
    if not trades:
        return _empty_metrics()

    total = len(trades)
    wins = [t for t in trades if t.pnl_pct > 0]
    losses = [t for t in trades if t.pnl_pct <= 0]
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = (win_count / total) * 100.0 if total else 0.0
    loss_rate = (loss_count / total) * 100.0 if total else 0.0

    avg_win = mean([t.pnl_pct for t in wins]) if wins else 0.0
    avg_loss = mean([t.pnl_pct for t in losses]) if losses else 0.0
    avg_trade = mean([t.pnl_pct for t in trades])

    gross_wins = sum(t.pnl_pct for t in wins)
    gross_losses = abs(sum(t.pnl_pct for t in losses))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    # Equity curve + drawdown
    equity = np.cumsum([t.pnl_pct for t in trades])
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_drawdown = float(np.max(drawdown)) if len(drawdown) else 0.0

    # Sharpe ratio
    pnls = np.array([t.pnl_pct for t in trades])
    if len(pnls) > 1 and np.std(pnls) > 0:
        sharpe = float(np.mean(pnls) / np.std(pnls) * np.sqrt(len(pnls)))
    else:
        sharpe = 0.0

    # Expectancy
    expectancy = (win_rate / 100.0 * avg_win) + (loss_rate / 100.0 * avg_loss)

    avg_hold = mean([t.hold_candles for t in trades])
    best = max(t.pnl_pct for t in trades)
    worst = min(t.pnl_pct for t in trades)

    # Partial exit stats
    partial_count = sum(1 for t in trades if t.partial_tp1)

    return {
        "total_trades": total,
        "wins": win_count,
        "losses": loss_count,
        "win_rate": round(win_rate, 2),
        "loss_rate": round(loss_rate, 2),
        "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
        "avg_trade_pct": round(avg_trade, 4),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "expectancy": round(expectancy, 4),
        "avg_hold_candles": round(avg_hold, 2),
        "best_trade": round(best, 4),
        "worst_trade": round(worst, 4),
        "partial_exits": partial_count,
        "gross_profit": round(gross_wins, 4),
        "gross_loss": round(gross_losses, 4),
    }


def by_coin(trades: List[Trade]) -> Dict[str, Dict[str, Any]]:
    """Break down metrics by coin symbol."""
    groups = defaultdict(list)
    for t in trades:
        groups[t.symbol].append(t)
    return {sym: calculate(trades) for sym, trades in groups.items()}


def by_direction(trades: List[Trade]) -> Dict[str, Dict[str, Any]]:
    """Break down metrics by LONG/SHORT."""
    longs = [t for t in trades if t.direction == "long"]
    shorts = [t for t in trades if t.direction == "short"]
    return {
        "LONG": calculate(longs),
        "SHORT": calculate(shorts),
    }


def monthly(trades: List[Trade]) -> Dict[str, Dict[str, Any]]:
    """Break down metrics by month (YYYY-MM)."""
    groups = defaultdict(list)
    for t in trades:
        month = t.entry_time[:7]  # YYYY-MM
        groups[month].append(t)
    return {m: calculate(trades) for m, trades in groups.items()}


def _empty_metrics() -> Dict[str, Any]:
    return {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "loss_rate": 0.0,
        "avg_win_pct": 0.0,
        "avg_loss_pct": 0.0,
        "avg_trade_pct": 0.0,
        "profit_factor": 0.0,
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "expectancy": 0.0,
        "avg_hold_candles": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "partial_exits": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
    }
