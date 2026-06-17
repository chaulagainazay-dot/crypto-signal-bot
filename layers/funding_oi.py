"""Funding rates + Open Interest from Bybit & OKX public APIs."""
import asyncio
import aiohttp
from utils.fmt import fp, mill, pct, header, SEP, SEP2, kv, row, footer, npt_time, score_grade

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "AVAXUSDT", "LINKUSDT", "DOTUSDT", "ADAUSDT", "MATICUSDT"]

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False)
    return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=10))


# ── Funding Rates ─────────────────────────────────────────────────────────────

async def _bybit_funding(session: aiohttp.ClientSession, symbol: str) -> dict:
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        async with session.get(url, params={"category": "linear", "symbol": symbol}) as r:
            data = await r.json()
            item = data["result"]["list"][0]
            return {
                "symbol": symbol,
                "price": float(item.get("lastPrice", 0)),
                "funding_rate": float(item.get("fundingRate", 0)),
                "next_funding": item.get("nextFundingTime", ""),
                "oi": float(item.get("openInterest", 0)),
                "source": "bybit",
            }
    except Exception:
        return None


async def _okx_funding(session: aiohttp.ClientSession, symbol: str) -> dict:
    try:
        okx_sym = symbol.replace("USDT", "-USDT-SWAP")
        url = "https://www.okx.com/api/v5/public/funding-rate"
        async with session.get(url, params={"instId": okx_sym}) as r:
            data = await r.json()
            item = data["data"][0]
            return {
                "symbol": symbol,
                "funding_rate": float(item.get("fundingRate", 0)),
                "next_funding": item.get("nextFundingTime", ""),
                "source": "okx",
            }
    except Exception:
        return None


async def _bybit_oi(session: aiohttp.ClientSession, symbol: str) -> dict:
    try:
        url = "https://api.bybit.com/v5/market/open-interest"
        async with session.get(url, params={
            "category": "linear", "symbol": symbol, "intervalTime": "1h", "limit": 3
        }) as r:
            data = await r.json()
            items = data["result"]["list"]
            if len(items) < 2:
                return None
            oi_now  = float(items[0]["openInterest"])
            oi_prev = float(items[-1]["openInterest"])
            oi_chg  = (oi_now - oi_prev) / oi_prev * 100 if oi_prev else 0
            return {"symbol": symbol, "oi": oi_now, "oi_chg_pct": oi_chg}
    except Exception:
        return None


async def fetch_funding_oi(symbols: list = None) -> list:
    if symbols is None:
        symbols = SYMBOLS[:8]
    results = []
    async with _make_session() as session:
        tasks = [_bybit_funding(session, s) for s in symbols]
        funding_data = await asyncio.gather(*tasks, return_exceptions=True)
        oi_tasks = [_bybit_oi(session, s) for s in symbols]
        oi_data  = await asyncio.gather(*oi_tasks, return_exceptions=True)
    oi_map = {}
    for item in oi_data:
        if isinstance(item, dict):
            oi_map[item["symbol"]] = item
    for item in funding_data:
        if isinstance(item, dict):
            oi_info = oi_map.get(item["symbol"], {})
            item["oi_chg_pct"] = oi_info.get("oi_chg_pct", 0)
            results.append(item)
    return results


# ── Format ────────────────────────────────────────────────────────────────────

def _funding_signal(rate: float) -> str:
    """Interpret funding rate as contrarian signal."""
    if rate > 0.0005:   return "🔴 Longs paying — short bias"
    if rate > 0.0003:   return "🟠 Elevated — cautious long"
    if rate < -0.0003:  return "🟢 Shorts paying — long bias"
    if rate < -0.0001:  return "🟡 Slightly negative — watch"
    return "⚪ Neutral"

def _oi_signal(chg: float) -> str:
    if chg > 5:   return "🟢 OI spike +{:.1f}%".format(chg)
    if chg > 2:   return "🟡 OI rising +{:.1f}%".format(chg)
    if chg < -5:  return "🔴 OI dump {:.1f}%".format(chg)
    if chg < -2:  return "🟠 OI falling {:.1f}%".format(chg)
    return "⚪ OI flat {:.1f}%".format(chg)


def format_funding_oi(data: list) -> str:
    if not data:
        return "❌ Could not fetch funding data. Try again later."
    lines = [header("📊", "Funding Rates & Open Interest"), ""]
    for item in data:
        rate     = item.get("funding_rate", 0) * 100
        oi       = item.get("oi", 0)
        oi_chg   = item.get("oi_chg_pct", 0)
        price    = item.get("price", 0)
        sym      = item["symbol"].replace("USDT", "/USDT")
        rate_pct = f"{rate:+.4f}%"
        lines.append(f"*{sym}*  {fp(price)}")
        lines.append(f"  Funding: `{rate_pct}`  {_funding_signal(item.get('funding_rate', 0))}")
        if oi:
            lines.append(f"  OI: `{mill(oi)}`  {_oi_signal(oi_chg)}")
        lines.append("")
    lines.append(footer("Funding resets 3× daily · Extreme = contrarian signal"))
    return "\n".join(lines)


def format_oi_spikes(data: list) -> str:
    """Highlight only coins with significant OI changes."""
    spikes = [d for d in data if abs(d.get("oi_chg_pct", 0)) > 3]
    if not spikes:
        return f"{header('📈', 'Open Interest Tracker')}\n\n_No significant OI spikes in the last hour._\n\n{footer()}"
    lines = [header("📈", "Open Interest Spikes"), ""]
    for item in sorted(spikes, key=lambda x: abs(x.get("oi_chg_pct", 0)), reverse=True):
        sym  = item["symbol"].replace("USDT", "/USDT")
        oi   = item.get("oi", 0)
        chg  = item.get("oi_chg_pct", 0)
        icon = "🚀" if chg > 0 else "💥"
        lines.append(f"{icon} *{sym}*  OI `{mill(oi)}`  `{chg:+.1f}%` (1h)")
    lines.append("")
    lines.append(footer("OI spike + price up = bullish · OI spike + price down = bearish"))
    return "\n".join(lines)
