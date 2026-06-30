#!/usr/bin/env python3
"""
data_fetcher.py
Fetches historical OHLCV from Binance public API and caches in SQLite.
Only free endpoints — no API keys required.
"""

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from tqdm import tqdm

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
MAX_PER_CALL = 1000

CACHE_DB = Path("backtest_cache.db")


def _init_db() -> None:
    """Create SQLite cache table if not exists."""
    conn = sqlite3.connect(CACHE_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS klines (
            symbol    TEXT    NOT NULL,
            interval  TEXT    NOT NULL,
            open_time INTEGER NOT NULL,
            open      REAL,
            high      REAL,
            low       REAL,
            close     REAL,
            volume    REAL,
            PRIMARY KEY (symbol, interval, open_time)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_klines ON klines (symbol, interval, open_time)"
    )
    conn.commit()
    conn.close()


_init_db()


def _from_cache(symbol: str, interval: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    """Return cached rows within the requested range."""
    conn = sqlite3.connect(CACHE_DB)
    query = """
        SELECT open_time, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND interval = ?
          AND open_time >= ? AND open_time <= ?
        ORDER BY open_time
    """
    df = pd.read_sql_query(query, conn, params=(symbol, interval, start_ms, end_ms))
    conn.close()
    if df.empty:
        return df
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.set_index("open_time", inplace=True)
    return df


def _to_cache(symbol: str, interval: str, df: pd.DataFrame) -> None:
    """Write rows to SQLite cache."""
    if df.empty:
        return
    conn = sqlite3.connect(CACHE_DB)
    rows: List[tuple] = []
    for ts, row in df.iterrows():
        rows.append((
            symbol, interval,
            int(ts.timestamp() * 1000),
            float(row["open"]), float(row["high"]),
            float(row["low"]), float(row["close"]),
            float(row["volume"]),
        ))
    conn.executemany(
        """
        INSERT OR REPLACE INTO klines
        (symbol, interval, open_time, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


def _fetch_chunk(symbol: str, interval: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    """Fetch one chunk from Binance public klines."""
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": MAX_PER_CALL,
    }
    r = requests.get(BINANCE_KLINES, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    if not isinstance(data, list) or len(data) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.set_index("open_time", inplace=True)
    df.sort_index(inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


def fetch_all(
    symbol: str,
    interval: str = "1h",
    start_ms: Optional[int] = None,
    end_ms: Optional[int] = None,
    progress: bool = True,
) -> pd.DataFrame:
    """
    Fetch all historical klines for a symbol/interval, using SQLite cache
    and paginating via Binance API. Respects rate limits (sleep 0.2s per call).
    """
    # Default: 6 months ago → now
    if end_ms is None:
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    if start_ms is None:
        start_ms = end_ms - 180 * 24 * 3600 * 1000  # ~180 days

    # --- Try cache first ---
    cached = _from_cache(symbol, interval, start_ms, end_ms)
    if not cached.empty:
        # Check coverage: if we have data from start to end, use it
        cached_start = int(cached.index[0].timestamp() * 1000)
        cached_end = int(cached.index[-1].timestamp() * 1000)
        if cached_start <= start_ms + 3600 * 1000 and cached_end >= end_ms - 3600 * 1000:
            return cached[(cached.index.astype("int64") // 10**6 >= start_ms) &
                          (cached.index.astype("int64") // 10**6 <= end_ms)]

    # --- Fetch from Binance ---
    all_chunks: List[pd.DataFrame] = []
    cursor = start_ms
    pbar = tqdm(desc=f"Fetching {symbol} {interval}", unit="chunk") if progress else None

    while cursor < end_ms:
        chunk_end = min(cursor + MAX_PER_CALL * _interval_ms(interval), end_ms)
        try:
            df = _fetch_chunk(symbol, interval, cursor, chunk_end)
        except Exception as e:
            print(f"[WARN] Binance fetch failed for {symbol} @ {interval}: {e}")
            break

        if df.empty:
            break

        all_chunks.append(df)
        _to_cache(symbol, interval, df)

        last_ts = int(df.index[-1].timestamp() * 1000)
        if last_ts <= cursor:
            break
        cursor = last_ts + 1
        time.sleep(0.2)  # rate limit

        if pbar:
            pbar.update(1)

    if pbar:
        pbar.close()

    if not all_chunks:
        # Fall back to whatever cache we have in range
        return _from_cache(symbol, interval, start_ms, end_ms)

    combined = pd.concat(all_chunks)
    combined = combined[~combined.index.duplicated(keep="last")]
    combined.sort_index(inplace=True)
    # Filter to requested range
    combined = combined[
        (combined.index.astype("int64") // 10**6 >= start_ms) &
        (combined.index.astype("int64") // 10**6 <= end_ms)
    ]
    return combined


def _interval_ms(interval: str) -> int:
    """Return approximate ms per interval for chunk sizing."""
    mapping = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
               "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
    return mapping.get(interval, 3_600_000)


def get_available_coins() -> List[str]:
    """Return the list of supported coins."""
    return [
        "BTC", "ETH", "SOL", "BNB", "XRP",
        "ADA", "AVAX", "LINK", "DOT", "DOGE",
    ]


if __name__ == "__main__":
    # Quick smoke test
    df = fetch_all("BTCUSDT", "1h")
    print(df.head())
