"""Background TP/SL tracker — checks open signals against live price every 10 min."""
import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from utils.db import get_pending_signals, close_signal
from utils.fmt import fp, pct, npt_time

log = logging.getLogger(__name__)

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False)
    return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=8))


async def _get_price(session: aiohttp.ClientSession, symbol: str) -> float:
    """Fetch last price from Bybit, fallback to Binance."""
    sym = symbol.upper().replace("/", "").replace("-", "") + "USDT" \
        if "USDT" not in symbol.upper() else symbol.upper().replace("/", "")
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        async with session.get(url, params={"category": "spot", "symbol": sym}) as r:
            data = await r.json()
            return float(data["result"]["list"][0]["lastPrice"])
    except Exception:
        pass
    try:
        url = f"https://api.binance.com/api/v3/ticker/price"
        async with session.get(url, params={"symbol": sym}) as r:
            data = await r.json()
            return float(data["price"])
    except Exception:
        return None


async def check_signals(bot=None, chat_id: str = None) -> list:
    """Check all pending signals. Returns list of resolved signals."""
    signals = await get_pending_signals()
    if not signals:
        return []

    resolved = []
    async with _make_session() as session:
        for sig in signals:
            asset  = sig["asset"]
            sl     = sig.get("stop_loss")
            tp1    = sig.get("tp1")
            tp2    = sig.get("tp2")
            dir_   = sig.get("direction", "LONG").upper()

            # Skip if missing critical levels
            if not sl or not tp1:
                continue

            # Check expiry
            if sig.get("expires_at"):
                try:
                    exp = datetime.fromisoformat(sig["expires_at"])
                    if datetime.now(timezone.utc) > exp.replace(tzinfo=timezone.utc):
                        await close_signal(sig["id"], "expired", 0, 0)
                        resolved.append({**sig, "outcome": "expired", "close_price": 0})
                        if bot and chat_id:
                            await _notify(bot, chat_id, sig, "expired", 0)
                        continue
                except Exception:
                    pass

            price = await _get_price(session, asset)
            if price is None:
                continue

            entry = ((sig.get("entry_low") or 0) + (sig.get("entry_high") or 0)) / 2 or price
            outcome = None
            pnl = 0.0

            if dir_ == "LONG":
                if price <= sl:
                    outcome = "sl"
                    pnl = (price - entry) / entry * 100
                elif tp2 and price >= tp2:
                    outcome = "tp2"
                    pnl = (price - entry) / entry * 100
                elif price >= tp1:
                    outcome = "tp1"
                    pnl = (price - entry) / entry * 100
            else:  # SHORT
                if price >= sl:
                    outcome = "sl"
                    pnl = (entry - price) / entry * 100
                elif tp2 and price <= tp2:
                    outcome = "tp2"
                    pnl = (entry - price) / entry * 100
                elif price <= tp1:
                    outcome = "tp1"
                    pnl = (entry - price) / entry * 100

            if outcome:
                await close_signal(sig["id"], outcome, price, pnl)
                resolved.append({**sig, "outcome": outcome, "close_price": price, "pnl_pct": pnl})
                if bot and chat_id:
                    await _notify(bot, chat_id, sig, outcome, price, pnl)

    return resolved


async def _notify(bot, chat_id: str, sig: dict, outcome: str, price: float, pnl: float = 0):
    icons = {"tp1": "🎯", "tp2": "✅", "sl": "❌", "expired": "💨"}
    labels = {"tp1": "TP1 HIT", "tp2": "TP2 HIT ✨", "sl": "STOP LOSS HIT", "expired": "SIGNAL EXPIRED"}
    icon  = icons.get(outcome, "⏳")
    label = labels.get(outcome, outcome.upper())
    asset = sig["asset"]
    dir_  = sig.get("direction", "LONG")

    text_parts = [
        f"{icon} *{label}*",
        f"*{asset}* {dir_}  @  {fp(price)}",
    ]
    if outcome != "expired":
        text_parts.append(f"PnL: `{pnl:+.2f}%`")
    text = "\n".join(text_parts)
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    except Exception as e:
        log.warning(f"Failed to send signal notification: {e}")


def format_open_signals(signals: list) -> str:
    if not signals:
        return "📭 *No Open Signals*\n\n_Run a scan to generate new signals._"
    lines = ["🎯 *Open Signals*", "━━━━━━━━━━━━━━━━━━", ""]
    for sig in signals[:8]:
        asset = sig["asset"]
        dir_  = sig.get("direction", "LONG")
        entry_low  = sig.get("entry_low")
        entry_high = sig.get("entry_high")
        sl  = sig.get("stop_loss")
        tp1 = sig.get("tp1")
        tp2 = sig.get("tp2")
        icon = "🟢" if dir_ == "LONG" else "🔴"
        entry_str = f"{fp(entry_low)}–{fp(entry_high)}" if entry_low and entry_high else fp(entry_low or 0)
        lines.append(f"{icon} *{asset}* `{dir_}`")
        if entry_low:
            lines.append(f"  Entry  `{entry_str}`")
        if tp1:
            lines.append(f"  TP1    `{fp(tp1)}`  TP2 `{fp(tp2) if tp2 else '–'}`")
        if sl:
            lines.append(f"  SL     `{fp(sl)}`")
        lines.append("")
    lines.append("──────────────────")
    lines.append("_Auto-tracked every 10 min_")
    return "\n".join(lines)
