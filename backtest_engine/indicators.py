#!/usr/bin/env python3
"""
indicators.py
Compute all technical indicators on a OHLCV DataFrame.
Uses pandas-ta (pure Python, no C library needed).
"""

from typing import Dict, Optional

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with all required indicators appended as columns."""
    if df.empty or len(df) < 200:
        raise ValueError("DataFrame too short for indicators (need ≥ 200 rows)")

    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    df = df.copy()

    # EMA
    df["ema21"] = EMAIndicator(c, window=21).ema_indicator()
    df["ema200"] = EMAIndicator(c, window=200).ema_indicator()

    # RSI
    df["rsi"] = RSIIndicator(c, window=14).rsi()

    # MACD
    macd = MACD(c, window_fast=12, window_slow=26, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    # ATR
    df["atr"] = AverageTrueRange(h, l, c, window=14).average_true_range()

    # ADX
    adx = ADXIndicator(h, l, c, window=14)
    df["adx"] = adx.adx()

    # Volume SMA(20) + volume confirmation
    df["volume_sma20"] = v.rolling(window=20).mean()

    # MACD histogram change (for increasing/decreasing detection)
    df["macd_hist_prev"] = df["macd_hist"].shift(1)
    df["macd_hist_change"] = df["macd_hist"] - df["macd_hist_prev"]

    # Price vs EMA21 distance
    df["price_above_ema21"] = df["close"] > df["ema21"]

    return df.dropna()


def get_indicator_summary(df: pd.DataFrame) -> Dict[str, float]:
    """Return the latest values of all indicators as a dict."""
    last = df.iloc[-1]
    return {
        "price": float(last["close"]),
        "ema21": float(last["ema21"]),
        "ema200": float(last["ema200"]),
        "rsi": float(last["rsi"]),
        "macd": float(last["macd"]),
        "macd_signal": float(last["macd_signal"]),
        "macd_hist": float(last["macd_hist"]),
        "macd_hist_change": float(last["macd_hist_change"]),
        "atr": float(last["atr"]),
        "adx": float(last["adx"]),
        "volume": float(last["volume"]),
        "volume_sma20": float(last["volume_sma20"]),
    }
