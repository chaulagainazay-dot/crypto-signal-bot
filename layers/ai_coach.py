"""AI Coach — uses CoinGecko data to answer coin/market questions (no API key needed)."""
import logging
import re

log = logging.getLogger(__name__)


async def ask_coach(user_message: str, history: list[dict] = None) -> str:
    """Analyse the user's question and return CoinGecko-powered insights."""
    from layers.coingecko_api import (
        get_coin_id, fetch_coin_detail, format_coin_detail,
        fetch_global_data, format_global_data,
        format_gainers, format_losers, format_trending,
        search_coins,
    )

    msg = user_message.strip().lower()

    # Global market questions
    if any(k in msg for k in ("market", "global", "total cap", "dominance", "btc dom")):
        try:
            gd = await fetch_global_data()
            text = format_global_data(gd)
            text += (
                "\n\n📐 <b>Coach tip:</b> BTC dominance rising = capital rotating into BTC (risk-off). "
                "Dominance falling = altseason potential.\n\n"
                "<i>Always set a stop loss. DYOR before any trade.</i>"
            )
            return text
        except Exception as e:
            log.error("coach global: %s", e)

    # Top gainers
    if any(k in msg for k in ("gainer", "pump", "moon", "top gain", "best perform")):
        try:
            return await format_gainers(10)
        except Exception as e:
            log.error("coach gainers: %s", e)

    # Top losers
    if any(k in msg for k in ("loser", "dump", "worst", "top los", "drop")):
        try:
            return await format_losers(10)
        except Exception as e:
            log.error("coach losers: %s", e)

    # Trending
    if any(k in msg for k in ("trend", "hot", "viral", "popular")):
        try:
            return await format_trending()
        except Exception as e:
            log.error("coach trending: %s", e)

    # Try to extract a coin ticker/name (e.g. "analyse BTC", "what about ETH", "price of solana")
    words = re.findall(r"\b[a-zA-Z]{2,10}\b", user_message)
    stop = {"what", "about", "tell", "me", "the", "price", "of", "is", "are", "how", "buy",
            "sell", "should", "can", "will", "a", "an", "and", "or", "for", "to", "in",
            "it", "good", "bad", "now", "get", "do", "that", "this", "my", "your", "trading"}
    candidates = [w for w in words if w.lower() not in stop]

    for word in candidates:
        coin_id = get_coin_id(word.upper())
        if not coin_id:
            # Try search
            try:
                results = await search_coins(word)
                if results:
                    coin_id = results[0].get("id") or results[0].get("api_symbol") or word.lower()
            except Exception:
                pass
        if coin_id:
            try:
                d = await fetch_coin_detail(coin_id)
                text = format_coin_detail(d)
                text += (
                    "\n\n📐 <b>Coach tip:</b> Check support/resistance before entry. "
                    "ATH distance shows how far from peak euphoria.\n\n"
                    "⚠️ <i>Not financial advice. Always manage your risk. DYOR.</i>"
                )
                return text
            except Exception as e:
                log.error("coach coin detail %s: %s", coin_id, e)

    # Fallback: show global market overview
    try:
        gd = await fetch_global_data()
        return (
            format_global_data(gd) +
            "\n\n💡 <b>Tip:</b> Type a coin name like <code>BTC</code>, <code>ETH</code>, or "
            "<code>SOL</code> and I'll pull live data for you.\n\n"
            "<i>Use /price &lt;coin&gt; for a quick price check anytime.</i>"
        )
    except Exception as e:
        return (
            "🤖 <b>AI Coach</b>\n\n"
            "Type a coin symbol (e.g. <code>BTC</code>, <code>SOL</code>) or ask about "
            "market trends, gainers, losers, or trending coins.\n\n"
            "<i>Live data powered by CoinGecko.</i>"
        )
