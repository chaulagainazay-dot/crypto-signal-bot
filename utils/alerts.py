"""Custom price alert manager — set/list/delete alerts, check them every 5 min."""
import asyncio
import aiohttp
import logging
from utils.db import get_active_alerts, trigger_alert, delete_alert
from utils.fmt import fp, header, footer, SEP

log = logging.getLogger(__name__)

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False)
    return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=8))


async def _get_prices(symbols: list) -> dict:
    """Batch price fetch via Bybit."""
    prices = {}
    async with _make_session() as session:
        for sym in symbols:
            norm = sym.upper().replace("/", "").replace("-", "")
            if not norm.endswith("USDT"):
                norm += "USDT"
            try:
                url = "https://api.bybit.com/v5/market/tickers"
                async with session.get(url, params={"category": "spot", "symbol": norm}) as r:
                    data = await r.json()
                    price = float(data["result"]["list"][0]["lastPrice"])
                    prices[sym.upper()] = price
            except Exception:
                pass
    return prices


async def check_alerts(bot=None) -> list:
    """Check all active alerts against current prices. Returns triggered list."""
    alerts = await get_active_alerts()
    if not alerts:
        return []
    symbols = list({a["symbol"] for a in alerts})
    prices  = await _get_prices(symbols)
    triggered = []
    for alert in alerts:
        sym   = alert["symbol"].upper()
        price = prices.get(sym)
        if price is None:
            continue
        cond   = alert["condition"]
        target = alert["target_price"]
        hit = (cond == "above" and price >= target) or (cond == "below" and price <= target)
        if hit:
            await trigger_alert(alert["id"])
            triggered.append({**alert, "current_price": price})
            if bot:
                await _send_alert_notification(bot, alert, price)
    return triggered


async def _send_alert_notification(bot, alert: dict, price: float):
    direction = "🔼" if alert["condition"] == "above" else "🔽"
    sym    = alert["symbol"]
    target = alert["target_price"]
    text = (
        f"🔔 *Price Alert Triggered!*\n\n"
        f"{direction} *{sym}* is now {fp(price)}\n"
        f"Your alert: `{alert['condition']} {fp(target)}`"
    )
    try:
        await bot.send_message(chat_id=alert["chat_id"], text=text, parse_mode="Markdown")
    except Exception as e:
        log.warning(f"Alert notification failed: {e}")


def parse_alert_command(text: str) -> dict:
    """Parse '/alert BTC above 70000' or '/alert ETH below 2500'"""
    parts = text.strip().split()
    if len(parts) < 4:
        return None
    _, symbol, condition, price_str = parts[0], parts[1], parts[2].lower(), parts[3]
    if condition not in ("above", "below", ">", "<"):
        return None
    condition = "above" if condition in ("above", ">") else "below"
    try:
        price = float(price_str.replace(",", "").replace("$", ""))
    except ValueError:
        return None
    return {"symbol": symbol.upper(), "condition": condition, "target_price": price}


def format_alerts_list(alerts: list) -> str:
    if not alerts:
        return (
            f"{header('🔔', 'Price Alerts')}\n\n"
            "_No active alerts._\n\n"
            "Set one with:\n"
            "`/alert BTC above 70000`\n"
            "`/alert ETH below 2500`\n\n"
            f"{footer()}"
        )
    lines = [header("🔔", "Active Price Alerts"), ""]
    for i, a in enumerate(alerts, 1):
        direction = "🔼" if a["condition"] == "above" else "🔽"
        lines.append(f"{i}. {direction} *{a['symbol']}* `{a['condition']} {fp(a['target_price'])}`  `#{a['id']}`")
    lines.append("")
    lines.append("_Remove: `/delalert <id>`_")
    lines.append(f"\n{footer()}")
    return "\n".join(lines)
