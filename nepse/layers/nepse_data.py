"""
NEPSE data via merolagani.com public API.
All functions return plain dicts/lists — no formatting here.
"""
import asyncio
import logging
import aiohttp
from config import ML_BASE, HEADERS

log = logging.getLogger(__name__)


def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False)
    return aiohttp.ClientSession(
        connector=connector,
        headers=HEADERS,
        timeout=aiohttp.ClientTimeout(total=15),
    )


async def fetch_market_summary() -> dict:
    """Returns overall, turnover list, sector list, broker list, stock list."""
    try:
        async with _make_session() as s:
            async with s.get(ML_BASE, params={"type": "market_summary"}) as r:
                data = await r.json(content_type=None)
                return data
    except Exception as e:
        log.warning("market_summary error: %s", e)
        return {}


async def fetch_stock_detail(symbol: str) -> dict:
    """Returns detailed data for a single stock symbol."""
    try:
        async with _make_session() as s:
            async with s.get(ML_BASE, params={"type": "stock_detail", "symbol": symbol.upper()}) as r:
                data = await r.json(content_type=None)
                return data or {}
    except Exception as e:
        log.warning("stock_detail(%s) error: %s", symbol, e)
        return {}


async def fetch_latest_price(symbol: str) -> float:
    """Quick LTP fetch for alert checking."""
    try:
        data = await fetch_market_summary()
        for item in data.get("turnover", {}).get("detail", []):
            if item.get("s", "").upper() == symbol.upper():
                return float(item.get("lp", 0))
    except Exception:
        pass
    return 0.0


async def fetch_prices_bulk(symbols: list) -> dict:
    """Returns {SYMBOL: ltp} for all symbols from market summary."""
    try:
        data = await fetch_market_summary()
        prices = {}
        for item in data.get("turnover", {}).get("detail", []):
            sym = item.get("s", "").upper()
            if sym and item.get("lp"):
                prices[sym] = float(item["lp"])
        return prices
    except Exception:
        return {}


async def fetch_ipo_list() -> list:
    """Returns list of active IPO/FPO/right issues."""
    try:
        async with _make_session() as s:
            async with s.get(ML_BASE, params={"type": "ipo"}) as r:
                data = await r.json(content_type=None)
                if isinstance(data, list):
                    return data
                return data.get("data", []) if isinstance(data, dict) else []
    except Exception as e:
        log.warning("ipo error: %s", e)
        return []


async def fetch_news() -> list:
    """Returns latest NEPSE news items."""
    try:
        async with _make_session() as s:
            async with s.get(ML_BASE, params={"type": "market_news"}) as r:
                data = await r.json(content_type=None)
                if isinstance(data, list):
                    return data[:10]
                return data.get("data", [])[:10] if isinstance(data, dict) else []
    except Exception as e:
        log.warning("news error: %s", e)
        return []
