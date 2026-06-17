"""
L2 — Technical Analysis
Pure aiohttp direct REST calls — no CCXT, no market-loading overhead.
Fallback chain: OKX → Bybit → Binance → Gemini → Kraken
All endpoints are public, no API keys required.
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import pandas as pd
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=12)

# Use Google DNS to bypass ISP-level blocking of crypto exchange domains
def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver)
    return aiohttp.ClientSession(connector=connector)

# ── Symbol / timeframe maps ───────────────────────────────────────────────────

def _binance_sym(s): return s.replace("/", "")          # BTC/USDT → BTCUSDT
def _okx_sym(s):     return s.replace("/", "-")         # BTC/USDT → BTC-USDT
def _bybit_sym(s):   return s.replace("/", "")          # BTC/USDT → BTCUSDT

GEMINI_SYM = {
    "BTC/USDT":"btcusd","ETH/USDT":"ethusd","SOL/USDT":"solusd",
    "LTC/USDT":"ltcusd","XRP/USDT":"xrpusd","DOGE/USDT":"dogeusd",
    "LINK/USDT":"linkusd","ADA/USDT":"adausd","AVAX/USDT":"avaxusd",
    "BNB/USDT":"bnbusd",
}
KRAKEN_SYM = {
    "BTC/USDT":"XBTUSD","ETH/USDT":"ETHUSD","SOL/USDT":"SOLUSD",
    "XRP/USDT":"XRPUSD","LTC/USDT":"LTCUSD","ADA/USDT":"ADAUSD",
    "LINK/USDT":"LINKUSD","DOT/USDT":"DOTUSD","AVAX/USDT":"AVAXUSD",
    "DOGE/USDT":"XDGUSD",
}
COINGECKO_IDS = {
    "BTC":"bitcoin","ETH":"ethereum","SOL":"solana","BNB":"binancecoin",
    "XRP":"ripple","ADA":"cardano","AVAX":"avalanche-2","DOT":"polkadot",
    "LINK":"chainlink","MATIC":"matic-network","TON":"the-open-network",
    "DOGE":"dogecoin","LTC":"litecoin","UNI":"uniswap","ATOM":"cosmos",
    "NEAR":"near","OP":"optimism","ARB":"arbitrum",
}

OKX_TF    = {"1m":"1m","5m":"5m","15m":"15m","1h":"1H","4h":"4H","1d":"1D"}
BYBIT_TF  = {"1m":"1","5m":"5","15m":"15","1h":"60","4h":"240","1d":"D"}
BINANCE_TF= {"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1d":"1d"}
KRAKEN_TF = {"1m":1,"5m":5,"15m":15,"1h":60,"4h":240,"1d":1440}
GEMINI_TF = {"1m":"1m","5m":"5m","15m":"15m","1h":"1hr","4h":"6hr","1d":"1day"}

# ── Per-source OHLCV fetchers ─────────────────────────────────────────────────

async def _okx_ohlcv(session, symbol, tf, limit):
    url = "https://www.okx.com/api/v5/market/candles"
    params = {"instId": _okx_sym(symbol), "bar": OKX_TF.get(tf,"1H"), "limit": str(limit)}
    async with session.get(url, params=params, timeout=TIMEOUT) as r:
        d = await r.json()
    if d.get("code") != "0":
        raise ValueError(f"OKX: {d.get('msg')}")
    # [[ts, o, h, l, c, vol, volCcy, ...], ...] newest first
    rows = [[int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])]
            for x in d["data"]]
    rows.reverse()
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts")


async def _bybit_ohlcv(session, symbol, tf, limit):
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category":"spot","symbol":_bybit_sym(symbol),
              "interval":BYBIT_TF.get(tf,"60"),"limit":str(limit)}
    async with session.get(url, params=params, timeout=TIMEOUT) as r:
        d = await r.json()
    if d.get("retCode") != 0:
        raise ValueError(f"Bybit: {d.get('retMsg')}")
    rows = [[int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])]
            for x in d["result"]["list"]]
    rows.reverse()
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts")


async def _binance_ohlcv(session, symbol, tf, limit):
    for domain in ["api.binance.com", "api1.binance.com", "data.binance.com"]:
        try:
            url = f"https://{domain}/api/v3/klines"
            params = {"symbol":_binance_sym(symbol),"interval":BINANCE_TF.get(tf,"1h"),"limit":str(limit)}
            async with session.get(url, params=params, timeout=TIMEOUT) as r:
                data = await r.json()
            if isinstance(data, list):
                rows = [[int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])]
                        for x in data]
                df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
                df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
                return df.set_index("ts")
        except Exception:
            continue
    raise ValueError("Binance: all domains failed")


async def _gemini_ohlcv(session, symbol, tf, limit):
    sym = GEMINI_SYM.get(symbol)
    if not sym:
        raise ValueError(f"Gemini: no mapping for {symbol}")
    url = f"https://api.gemini.com/v2/candles/{sym}/{GEMINI_TF.get(tf,'1hr')}"
    async with session.get(url, timeout=TIMEOUT) as r:
        data = await r.json()
    rows = sorted(data, key=lambda x: x[0])[-limit:]
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.set_index("ts")


async def _kraken_ohlcv(session, symbol, tf, limit):
    sym = KRAKEN_SYM.get(symbol)
    if not sym:
        raise ValueError(f"Kraken: no mapping for {symbol}")
    url = "https://api.kraken.com/0/public/OHLC"
    params = {"pair": sym, "interval": KRAKEN_TF.get(tf, 60)}
    async with session.get(url, params=params, timeout=TIMEOUT) as r:
        d = await r.json()
    if d.get("error"):
        raise ValueError(f"Kraken: {d['error']}")
    key = list(d["result"].keys())[0]
    rows = [[float(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[6])]
            for x in d["result"][key][-limit:]]
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"].astype(int), unit="s", utc=True)
    return df.set_index("ts")


# ── Per-source ticker fetchers ────────────────────────────────────────────────

async def _okx_ticker(session, symbol):
    url = "https://www.okx.com/api/v5/market/ticker"
    async with session.get(url, params={"instId": _okx_sym(symbol)}, timeout=TIMEOUT) as r:
        d = await r.json()
    x = d["data"][0]
    price = float(x["last"])
    open24 = float(x["open24h"])
    return {"price": price, "high_24h": float(x["high24h"]), "low_24h": float(x["low24h"]),
            "change_pct": round((price - open24) / open24 * 100, 2), "volume_24h": float(x["volCcy24h"])}


async def _bybit_ticker(session, symbol):
    url = "https://api.bybit.com/v5/market/tickers"
    async with session.get(url, params={"category":"spot","symbol":_bybit_sym(symbol)}, timeout=TIMEOUT) as r:
        d = await r.json()
    x = d["result"]["list"][0]
    price = float(x["lastPrice"])
    prev = float(x["prevPrice24h"])
    return {"price": price, "high_24h": float(x["highPrice24h"]), "low_24h": float(x["lowPrice24h"]),
            "change_pct": round((price - prev) / prev * 100, 2), "volume_24h": float(x.get("turnover24h", 0))}


async def _binance_ticker(session, symbol):
    url = "https://api.binance.com/api/v3/ticker/24hr"
    async with session.get(url, params={"symbol": _binance_sym(symbol)}, timeout=TIMEOUT) as r:
        x = await r.json()
    return {"price": float(x["lastPrice"]), "high_24h": float(x["highPrice"]),
            "low_24h": float(x["lowPrice"]), "change_pct": float(x["priceChangePercent"]),
            "volume_24h": float(x["quoteVolume"])}


async def _coingecko_ticker(session, symbol):
    base = symbol.split("/")[0]
    cg_id = COINGECKO_IDS.get(base)
    if not cg_id:
        raise ValueError(f"CoinGecko: no id for {base}")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    async with session.get(url, params={"vs_currency":"usd","ids":cg_id}, timeout=TIMEOUT) as r:
        data = await r.json()
    c = data[0]
    return {"price": float(c["current_price"]), "high_24h": float(c["high_24h"]),
            "low_24h": float(c["low_24h"]), "change_pct": float(c["price_change_percentage_24h"] or 0),
            "volume_24h": float(c["total_volume"])}


# ── Public API with fallback chain ────────────────────────────────────────────

_OHLCV_SOURCES = [
    ("OKX",     _okx_ohlcv),
    ("Bybit",   _bybit_ohlcv),
    ("Binance", _binance_ohlcv),
    ("Gemini",  _gemini_ohlcv),
    ("Kraken",  _kraken_ohlcv),
]

_TICKER_SOURCES = [
    ("OKX",       _okx_ticker),
    ("Bybit",     _bybit_ticker),
    ("Binance",   _binance_ticker),
    ("CoinGecko", _coingecko_ticker),
]


async def fetch_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 300) -> pd.DataFrame:
    errors = []
    async with _make_session() as session:
        for name, fn in _OHLCV_SOURCES:
            try:
                df = await fn(session, symbol, timeframe, limit)
                if len(df) > 10:
                    logger.debug(f"OHLCV {symbol}/{timeframe} via {name}")
                    return df
            except Exception as e:
                errors.append(f"{name}: {e}")
                logger.debug(f"OHLCV {symbol} {name} failed: {e}")
    raise RuntimeError(f"All OHLCV sources failed for {symbol}: {'; '.join(errors)}")


async def fetch_ticker(symbol: str) -> dict:
    async with _make_session() as session:
        for name, fn in _TICKER_SOURCES:
            try:
                t = await fn(session, symbol)
                logger.debug(f"Ticker {symbol} via {name}")
                return t
            except Exception as e:
                logger.debug(f"Ticker {symbol} {name} failed: {e}")
    return {"price": 0, "high_24h": 0, "low_24h": 0, "change_pct": 0, "volume_24h": 0}


async def close_exchange():
    pass  # no persistent connections to close


# ── Connectivity test ─────────────────────────────────────────────────────────

async def test_all_sources() -> list[tuple[str, bool, str]]:
    """Returns list of (name, ok, detail) for all sources."""
    results = []
    async with _make_session() as session:
        for name, fn in _OHLCV_SOURCES:
            try:
                df = await asyncio.wait_for(fn(session, "BTC/USDT", "1h", 5), timeout=10)
                price = df["close"].iloc[-1]
                results.append((name, True, f"BTC ${price:,.0f}"))
            except Exception as e:
                results.append((name, False, str(e)[:60]))
    return results


# ── Indicators ────────────────────────────────────────────────────────────────

def _compute_indicators(df: pd.DataFrame) -> dict:
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    ema21  = float(EMAIndicator(c, window=21).ema_indicator().iloc[-1])
    ema50  = float(EMAIndicator(c, window=50).ema_indicator().iloc[-1])
    ema200 = float(EMAIndicator(c, window=200).ema_indicator().iloc[-1])
    rsi    = float(RSIIndicator(c, window=14).rsi().iloc[-1])
    macd_o = MACD(c, window_fast=12, window_slow=26, window_sign=9)
    macd_hist = float(macd_o.macd_diff().iloc[-1])
    atr    = float(AverageTrueRange(h, l, c, window=14).average_true_range().iloc[-1])
    adx    = float(ADXIndicator(h, l, c, window=14).adx().iloc[-1])
    try:
        vwap = float(VolumeWeightedAveragePrice(h, l, c, v).volume_weighted_average_price().iloc[-1])
    except Exception:
        vwap = float(c.iloc[-1])
    return {"ema21":ema21,"ema50":ema50,"ema200":ema200,"rsi":rsi,
            "macd_hist":macd_hist,"atr":atr,"adx":adx,"vwap":vwap}


def _classify_regime(adx, atr, df):
    series = AverageTrueRange(df["high"],df["low"],df["close"],window=14).average_true_range().dropna()
    if len(series) < 20: return "ranging"
    pct = series.rank(pct=True).iloc[-1] * 100
    if pct > 90: return "chaotic"
    return "trending" if adx > 25 else "ranging"


def _score_ta(ind, price, regime):
    if regime == "chaotic": return 0.0, "neutral"
    score, direction = 0.0, "neutral"
    if price > ind["ema200"] and price > ind["ema50"]:
        score += 0.40; direction = "long"
    elif price < ind["ema200"] and price < ind["ema50"]:
        score -= 0.40; direction = "short"
    rsi = ind["rsi"]
    if direction == "long":
        if rsi > 70:           score -= 0.20
        elif 45 <= rsi <= 65:  score += 0.15
        elif rsi < 40:         score += 0.05
    elif direction == "short":
        if rsi < 30:           score += 0.20
        elif 35 <= rsi <= 55:  score -= 0.15
        elif rsi > 60:         score -= 0.05
    if   direction == "long"  and ind["macd_hist"] > 0: score += 0.20
    elif direction == "short" and ind["macd_hist"] < 0: score -= 0.20
    elif direction == "long"  and ind["macd_hist"] < 0: score -= 0.10
    elif direction == "short" and ind["macd_hist"] > 0: score += 0.10
    d21  = abs(price - ind["ema21"]) / max(ind["ema21"], 1e-9)
    dvwap= abs(price - ind["vwap"])  / max(ind["vwap"],  1e-9)
    if d21 < 0.005 or dvwap < 0.003:
        score += 0.20 if direction == "long" else -0.20
    return max(-1.0, min(1.0, score)), direction


def _compute_levels(price, atr, direction):
    sd = 1.5 * atr
    el, eh = price * 0.998, price * 1.002
    if direction == "long":
        return {"entry_low":el,"entry_high":eh,"stop_loss":el-sd,"tp1":el+1.5*sd,"tp2":el+2.5*sd}
    elif direction == "short":
        return {"entry_low":el,"entry_high":eh,"stop_loss":eh+sd,"tp1":eh-1.5*sd,"tp2":eh-2.5*sd}
    return {"entry_low":el,"entry_high":eh,"stop_loss":price-sd,"tp1":price+1.5*sd,"tp2":price+2.5*sd}


@dataclass
class TAResult:
    asset: str; price: float; ta_score: float; regime: str
    ema21: float; ema50: float; ema200: float; rsi: float
    macd_hist: float; atr: float; vwap: float; adx: float
    entry_low: float; entry_high: float
    stop_loss_long: float; stop_loss_short: float
    tp1_long: float; tp1_short: float
    tp2_long: float; tp2_short: float
    direction_bias: str


async def analyze(asset: str) -> TAResult:
    df_1h, df_15m = await asyncio.gather(
        fetch_ohlcv(asset, "1h",  limit=250),
        fetch_ohlcv(asset, "15m", limit=200),
    )
    price   = float(df_1h["close"].iloc[-1])
    ind_1h  = _compute_indicators(df_1h)
    ind_15m = _compute_indicators(df_15m)
    regime  = _classify_regime(ind_1h["adx"], ind_1h["atr"], df_1h)
    s1h, direction = _score_ta(ind_1h, price, regime)
    s15m, d15 = _score_ta(ind_15m, price, regime)
    blended = (s1h*0.7 + s15m*0.3) if d15 == direction else (s1h*0.5 + s15m*0.1)
    blended = max(-1.0, min(1.0, blended))
    lv = _compute_levels(price, ind_1h["atr"], direction)
    return TAResult(
        asset=asset, price=price, ta_score=blended, regime=regime,
        ema21=ind_1h["ema21"], ema50=ind_1h["ema50"], ema200=ind_1h["ema200"],
        rsi=ind_1h["rsi"], macd_hist=ind_1h["macd_hist"],
        atr=ind_1h["atr"], vwap=ind_1h["vwap"], adx=ind_1h["adx"],
        entry_low=lv["entry_low"], entry_high=lv["entry_high"],
        stop_loss_long =lv["stop_loss"] if direction=="long"  else 0,
        stop_loss_short=lv["stop_loss"] if direction=="short" else 0,
        tp1_long =lv["tp1"] if direction=="long"  else 0,
        tp1_short=lv["tp1"] if direction=="short" else 0,
        tp2_long =lv["tp2"] if direction=="long"  else 0,
        tp2_short=lv["tp2"] if direction=="short" else 0,
        direction_bias=direction,
    )
