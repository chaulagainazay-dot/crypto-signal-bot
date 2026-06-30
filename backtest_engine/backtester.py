#!/usr/bin/env python3
"""
backtester.py
Walk-forward candle-by-candle simulation engine.
Handles partial exits (TP1 = 50% position, TP2 = remaining 50%).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from tqdm import tqdm

from .signal_logic import compute_levels


@dataclass
class Trade:
    """Represents a single simulated trade."""
    entry_time: str
    exit_time: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    exit_price: float
    exit_reason: str
    pnl_pct: float
    hold_candles: int
    rsi_at_entry: float
    adx_at_entry: float
    atr_at_entry: float
    partial_tp1: bool = False
    pnl_tp1_pct: float = 0.0


def _simulate_trade(df: pd.DataFrame, idx: int, direction: str) -> Optional[Trade]:
    """Simulate one trade starting at candle `idx`. Max 50 candles forward."""
    entry_row = df.iloc[idx]
    atr = entry_row["atr"]
    ema21 = entry_row["ema21"]
    levels = compute_levels(ema21, atr, direction)
    entry_price = levels["entry_mid"]
    stop = levels["stop_loss"]
    tp1 = levels["tp1"]
    tp2 = levels["tp2"]

    future = df.iloc[idx + 1: idx + 1 + 50]
    if len(future) == 0:
        return None

    exit_price = None
    exit_reason = None
    exit_idx = None
    hit_tp1 = False
    pnl_tp1 = 0.0

    for j, (_, row) in enumerate(future.iterrows()):
        if direction == "long":
            # Check stop loss first (conservative)
            if row["low"] <= stop:
                if hit_tp1:
                    # 50% already exited at TP1, remaining 50% hit SL
                    exit_price = stop
                    exit_reason = "stop_loss_after_tp1"
                else:
                    exit_price = stop
                    exit_reason = "stop_loss"
                exit_idx = j
                break
            # Check TP2
            if row["high"] >= tp2:
                if not hit_tp1:
                    # Full position hit TP2 directly
                    exit_price = tp2
                    exit_reason = "tp2"
                else:
                    # Remaining 50% hit TP2
                    exit_price = tp2
                    exit_reason = "tp2_after_tp1"
                exit_idx = j
                break
            # Check TP1 (first time only)
            if not hit_tp1 and row["high"] >= tp1:
                hit_tp1 = True
                pnl_tp1 = (tp1 - entry_price) / entry_price * 100.0
                # Continue tracking remaining 50%
                continue
        else:  # short
            if row["high"] >= stop:
                if hit_tp1:
                    exit_price = stop
                    exit_reason = "stop_loss_after_tp1"
                else:
                    exit_price = stop
                    exit_reason = "stop_loss"
                exit_idx = j
                break
            if row["low"] <= tp2:
                if not hit_tp1:
                    exit_price = tp2
                    exit_reason = "tp2"
                else:
                    exit_price = tp2
                    exit_reason = "tp2_after_tp1"
                exit_idx = j
                break
            if not hit_tp1 and row["low"] <= tp1:
                hit_tp1 = True
                pnl_tp1 = (entry_price - tp1) / entry_price * 100.0
                continue

    # If nothing hit, timeout at last candle
    if exit_price is None:
        last = future.iloc[-1]
        exit_price = last["close"]
        exit_reason = "timeout"
        exit_idx = len(future) - 1

    # P&L calculation
    if hit_tp1:
        # 50% at TP1, 50% at final exit
        if direction == "long":
            pnl_exit = (exit_price - entry_price) / entry_price * 100.0
        else:
            pnl_exit = (entry_price - exit_price) / entry_price * 100.0
        total_pnl = (pnl_tp1 * 0.5) + (pnl_exit * 0.5)
    else:
        if direction == "long":
            total_pnl = (exit_price - entry_price) / entry_price * 100.0
        else:
            total_pnl = (entry_price - exit_price) / entry_price * 100.0

    return Trade(
        entry_time=entry_row.name.isoformat(),
        exit_time=future.iloc[exit_idx].name.isoformat() if exit_idx is not None else future.iloc[-1].name.isoformat(),
        symbol=entry_row.name,
        direction=direction,
        entry_price=round(entry_price, 4),
        stop_loss=round(stop, 4),
        tp1=round(tp1, 4),
        tp2=round(tp2, 4),
        exit_price=round(exit_price, 4),
        exit_reason=exit_reason,
        pnl_pct=round(total_pnl, 4),
        hold_candles=(exit_idx + 1) if exit_idx is not None else len(future),
        rsi_at_entry=round(float(entry_row["rsi"]), 2),
        adx_at_entry=round(float(entry_row["adx"]), 2),
        atr_at_entry=round(float(atr), 4),
        partial_tp1=hit_tp1,
        pnl_tp1_pct=round(pnl_tp1, 4),
    )


def run(df: pd.DataFrame, symbol: str, progress: bool = True) -> List[Trade]:
    """Run walk-forward backtest on a DataFrame with signals."""
    trades: List[Trade] = []
    last_signal_idx = -50

    # Ensure signals exist
    if "signal_long" not in df.columns or "signal_short" not in df.columns:
        raise ValueError("DataFrame missing signal columns. Run generate_signals() first.")

    iterator = tqdm(range(len(df)), desc=f"Backtesting {symbol}", unit="candle") if progress else range(len(df))

    for i in iterator:
        if i < 200:
            continue
        if i <= last_signal_idx + 50:
            continue

        if df["signal_long"].iloc[i]:
            trade = _simulate_trade(df, i, "long")
            if trade:
                trades.append(trade)
                last_signal_idx = i
        elif df["signal_short"].iloc[i]:
            trade = _simulate_trade(df, i, "short")
            if trade:
                trades.append(trade)
                last_signal_idx = i

    return trades
