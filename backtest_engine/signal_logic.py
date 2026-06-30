#!/usr/bin/env python3
"""
signal_logic.py
Signal generation rules matching the current bot strategy.
"""

from typing import Optional, Dict, Any

import pandas as pd


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add boolean signal columns to the DataFrame based on the strategy.

    LONG when ALL true:
        - RSI < 40
        - Close > EMA21
        - MACD histogram > 0 AND increasing (current > previous)
        - ADX > 20
        - Volume > 1.2 * Volume SMA20

    SHORT when ALL true:
        - RSI > 65
        - Close < EMA21
        - MACD histogram < 0 AND decreasing (current < previous)
        - ADX > 20
        - Volume > 1.2 * Volume SMA20
    """
    df = df.copy()

    long_cond = (
        (df["rsi"] < 40)
        & (df["close"] > df["ema21"])
        & (df["macd_hist"] > 0)
        & (df["macd_hist_change"] > 0)
        & (df["adx"] > 20)
        & (df["volume"] > 1.2 * df["volume_sma20"])
    )

    short_cond = (
        (df["rsi"] > 65)
        & (df["close"] < df["ema21"])
        & (df["macd_hist"] < 0)
        & (df["macd_hist_change"] < 0)
        & (df["adx"] > 20)
        & (df["volume"] > 1.2 * df["volume_sma20"])
    )

    df["signal_long"] = long_cond
    df["signal_short"] = short_cond
    df["signal_any"] = long_cond | short_cond
    return df


def compute_levels(price: float, atr: float, direction: str) -> Dict[str, float]:
    """
    Calculate entry, stop-loss, TP1, TP2 based on ATR.

    Entry zone = EMA21 ± (ATR * 0.3)
    Stop loss = Entry ± (ATR * 1.5)
    TP1 = Entry ± (ATR * 2.5)
    TP2 = Entry ± (ATR * 4.0)
    """
    entry_zone = atr * 0.3
    sl = atr * 1.5
    tp1 = atr * 2.5
    tp2 = atr * 4.0

    if direction == "long":
        entry_low = price - entry_zone
        entry_high = price + entry_zone
        stop = entry_low - sl
        take1 = entry_low + tp1
        take2 = entry_low + tp2
    else:  # short
        entry_low = price - entry_zone
        entry_high = price + entry_zone
        stop = entry_high + sl
        take1 = entry_high - tp1
        take2 = entry_high - tp2

    return {
        "entry_low": round(entry_low, 4),
        "entry_high": round(entry_high, 4),
        "entry_mid": round((entry_low + entry_high) / 2, 4),
        "stop_loss": round(stop, 4),
        "tp1": round(take1, 4),
        "tp2": round(take2, 4),
    }
