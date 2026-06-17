"""
L3 — Signal Engine
Fuses TA, news, and sentiment scores.
Issues structured signal dicts when composite score exceeds threshold.
Uses Claude for final reasoning paragraph.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import aiohttp
import anthropic

import config
from layers.l2_technical import TAResult
from layers.l1_data import get_news_score, get_sentiment_score


def _fuse_scores(ta_score: float, news_score: float, sentiment_score: float) -> float:
    """Weighted fusion per framework §4.2."""
    composite = (
        config.W_TA * ta_score
        + config.W_NEWS * news_score
        + config.W_SENTIMENT * sentiment_score
    )
    return round(max(-1.0, min(1.0, composite)), 4)


async def _generate_reasoning(
    ta: TAResult,
    news_score: float,
    sentiment_score: float,
    composite: float,
    client: anthropic.AsyncAnthropic,
) -> str:
    if not config.ANTHROPIC_API_KEY:
        return _fallback_reasoning(ta, composite)

    direction = ta.direction_bias.upper()
    prompt = f"""You are a disciplined crypto signal analyst. Write a concise (3–4 sentences) signal reasoning paragraph for a human trader. Be factual, specific, and highlight the key confluence factors. Do NOT give financial advice or express certainty about outcome.

Asset: {ta.asset}
Direction: {direction}
Price: ${ta.price:,.4f}
Regime: {ta.regime}
EMA21: {ta.ema21:.4f} | EMA50: {ta.ema50:.4f} | EMA200: {ta.ema200:.4f}
RSI(14): {ta.rsi:.1f}
MACD Hist: {ta.macd_hist:.6f}
ATR(14): {ta.atr:.4f}
VWAP: {ta.vwap:.4f}
ADX: {ta.adx:.1f}
TA Score: {ta.ta_score:.2f} | News Score: {news_score:.2f} | Sentiment Score: {sentiment_score:.2f}
Composite Score: {composite:.2f}

Write the reasoning paragraph now:"""

    try:
        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        return _fallback_reasoning(ta, composite)


def _fallback_reasoning(ta: TAResult, composite: float) -> str:
    dir_word = "bullish" if composite > 0 else "bearish"
    return (
        f"Price is {'above' if ta.price > ta.ema200 else 'below'} EMA200 at ${ta.ema200:,.2f}, "
        f"establishing a {dir_word} trend context. RSI({ta.rsi:.0f}) is in "
        f"{'healthy momentum range' if 40 < ta.rsi < 70 else 'extreme zone — caution'}. "
        f"MACD histogram is {'positive' if ta.macd_hist > 0 else 'negative'}, "
        f"{'confirming' if (composite > 0 and ta.macd_hist > 0) or (composite < 0 and ta.macd_hist < 0) else 'diverging from'} "
        f"the directional bias. Composite score: {composite:.2f}."
    )


async def evaluate_asset(
    ta: TAResult,
    session: aiohttp.ClientSession,
    anthropic_client: Optional[anthropic.AsyncAnthropic],
) -> Optional[dict]:
    """
    Returns a signal dict if score exceeds threshold, else None.
    """
    # Stand down on chaotic regime
    if ta.regime == "chaotic":
        return None

    # Fetch news and sentiment in parallel
    news_score, news_conf = await get_news_score(ta.asset, session)
    sentiment_score, sent_conf = await get_sentiment_score(ta.asset, session)

    composite = _fuse_scores(ta.ta_score, news_score, sentiment_score)
    abs_comp = abs(composite)

    # Threshold check: composite ≥ 0.70 AND TA alone ≥ 0.50
    if abs_comp < config.COMPOSITE_THRESHOLD:
        return None
    if abs(ta.ta_score) < config.TA_MIN_THRESHOLD:
        return None

    # Direction must be clear
    direction = "long" if composite > 0 else "short"
    if ta.direction_bias != direction and ta.direction_bias != "neutral":
        # TA and composite disagree — skip
        return None

    # Generate reasoning
    reasoning = ""
    if anthropic_client:
        reasoning = await _generate_reasoning(ta, news_score, sentiment_score, composite, anthropic_client)
    else:
        reasoning = _fallback_reasoning(ta, composite)

    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=config.SIGNAL_EXPIRY_MINUTES)).isoformat()

    stop_loss = ta.stop_loss_long if direction == "long" else ta.stop_loss_short
    tp1 = ta.tp1_long if direction == "long" else ta.tp1_short
    tp2 = ta.tp2_long if direction == "long" else ta.tp2_short

    return {
        "asset": ta.asset,
        "direction": direction,
        "price": ta.price,
        "entry_low": ta.entry_low,
        "entry_high": ta.entry_high,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "composite_score": composite,
        "ta_score": ta.ta_score,
        "news_score": news_score,
        "sentiment_score": sentiment_score,
        "regime": ta.regime,
        "rsi": ta.rsi,
        "reasoning": reasoning,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
