"""
L1 — Data Integration
News sentiment, social sentiment, macro calendar.
Each function returns a score [-1, +1] and confidence [0, 1].
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
import feedparser
import aiohttp

import config

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver)
    return aiohttp.ClientSession(connector=connector)


CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"

# RSS fallback when CryptoPanic key is missing
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]

# Major macro event keywords that trigger lockout
MACRO_KEYWORDS = [
    "CPI", "FOMC", "fed rate", "nonfarm payroll", "NFP",
    "interest rate decision", "inflation data", "gdp"
]


async def get_news_score(asset_symbol: str, session: aiohttp.ClientSession) -> tuple[float, float]:
    """Returns (score, confidence). score in [-1,+1], confidence in [0,1]."""
    symbol = asset_symbol.split("/")[0].upper()  # BTC/USDT -> BTC

    if config.CRYPTOPANIC_API_KEY:
        return await _cryptopanic_score(symbol, session)
    else:
        return await _rss_score(symbol)


async def _cryptopanic_score(symbol: str, session: aiohttp.ClientSession) -> tuple[float, float]:
    try:
        params = {
            "auth_token": config.CRYPTOPANIC_API_KEY,
            "currencies": symbol,
            "filter": "hot",
            "public": "true",
        }
        async with session.get(CRYPTOPANIC_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return 0.0, 0.0
            data = await resp.json()

        results = data.get("results", [])
        if not results:
            return 0.0, 0.3

        now = datetime.now(timezone.utc)
        scores = []
        for item in results[:20]:
            # Parse age
            published = item.get("published_at", "")
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                age_min = (now - pub_dt).total_seconds() / 60
            except Exception:
                age_min = 999

            # Stale news is context only, not a trigger
            if age_min > 30:
                continue

            votes = item.get("votes", {})
            positive = votes.get("positive", 0) + votes.get("liked", 0)
            negative = votes.get("negative", 0) + votes.get("disliked", 0)
            total = positive + negative
            if total == 0:
                continue

            raw_score = (positive - negative) / total
            # Weight newer news higher
            recency_weight = max(0.1, 1.0 - age_min / 30)
            scores.append(raw_score * recency_weight)

        if not scores:
            return 0.0, 0.1
        avg = sum(scores) / len(scores)
        confidence = min(1.0, len(scores) / 5)
        return float(avg), float(confidence)

    except Exception:
        return 0.0, 0.0


async def _rss_score(symbol: str) -> tuple[float, float]:
    """Simple keyword RSS fallback — limited accuracy, low confidence."""
    positive_words = {"surge", "rally", "bullish", "gains", "breakout", "adoption", "etf approval", "buy"}
    negative_words = {"crash", "plunge", "bearish", "hack", "ban", "sell-off", "decline", "regulation"}

    scores = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            now = datetime.now(timezone.utc)
            for entry in feed.entries[:15]:
                title = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
                if symbol.lower() not in title and symbol.lower()[:3] not in title:
                    continue
                # Age check
                published = entry.get("published_parsed")
                if published:
                    import time
                    pub_ts = time.mktime(published)
                    age_min = (now.timestamp() - pub_ts) / 60
                    if age_min > 30:
                        continue
                pos = sum(1 for w in positive_words if w in title)
                neg = sum(1 for w in negative_words if w in title)
                if pos + neg > 0:
                    scores.append((pos - neg) / (pos + neg))
        except Exception:
            continue

    if not scores:
        return 0.0, 0.0
    return float(sum(scores) / len(scores)), 0.2


async def get_fear_greed_score(session: aiohttp.ClientSession) -> tuple[float, float]:
    """
    Fear & Greed index as contrarian sentiment signal.
    Extreme greed (>80) → fade indicator (bearish signal weight)
    Extreme fear (<20)  → fade indicator (bullish signal weight)
    Returns (score, confidence).
    """
    try:
        async with session.get(FEAR_GREED_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status != 200:
                return 0.0, 0.0
            data = await resp.json()
        index = int(data["data"][0]["value"])
        # Contrarian mapping
        if index >= 80:
            score = -0.6   # extreme greed → bearish fade
        elif index >= 65:
            score = -0.3
        elif index <= 20:
            score = 0.6    # extreme fear → bullish fade
        elif index <= 35:
            score = 0.3
        else:
            score = 0.0    # neutral zone
        return float(score), 0.5
    except Exception:
        return 0.0, 0.0


async def get_sentiment_score(asset_symbol: str, session: aiohttp.ClientSession) -> tuple[float, float]:
    """
    Blends fear/greed index (market-wide) with asset-specific news sentiment.
    Returns combined sentiment score and confidence.
    """
    fg_score, fg_conf = await get_fear_greed_score(session)
    # Weight fear/greed lower — it's market-wide, not asset-specific
    return fg_score * 0.5, fg_conf * 0.5


async def check_macro_lockout(session: aiohttp.ClientSession) -> bool:
    """
    Returns True if we're within a macro event lockout window.
    Uses a lightweight economic calendar check.
    """
    # Simplified: check if current UTC time is near a known pattern
    # In production this would call Trading Economics or Investing.com calendar
    now = datetime.now(timezone.utc)
    # Common major release times (UTC): 13:30 (US data), 18:00 (FOMC)
    high_vol_minutes = [(13, 30), (18, 0), (14, 0)]
    for h, m in high_vol_minutes:
        event_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta = abs((now - event_time).total_seconds() / 60)
        if delta < config.MACRO_LOCKOUT_BEFORE or delta < config.MACRO_LOCKOUT_AFTER:
            # Only trigger on Tuesdays (CPI) / Wednesdays (FOMC) — rough approximation
            if now.weekday() in (1, 2, 4):  # Tue, Wed, Fri
                return True
    return False


async def fetch_latest_news(limit: int = 8) -> list[dict]:
    """
    Returns a list of recent news items: {title, source, url, age_min, sentiment}.
    Tries CryptoPanic first, falls back to RSS feeds.
    """
    items = []

    if config.CRYPTOPANIC_API_KEY:
        try:
            async with _make_session() as session:
                params = {
                    "auth_token": config.CRYPTOPANIC_API_KEY,
                    "filter": "hot",
                    "public": "true",
                    "kind": "news",
                }
                async with session.get(
                    CRYPTOPANIC_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        now = datetime.now(timezone.utc)
                        for item in data.get("results", [])[:limit]:
                            published = item.get("published_at", "")
                            try:
                                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                                age_min = int((now - pub_dt).total_seconds() / 60)
                            except Exception:
                                age_min = 0
                            votes = item.get("votes", {})
                            pos = votes.get("positive", 0)
                            neg = votes.get("negative", 0)
                            if pos > neg:
                                sentiment = "🟢"
                            elif neg > pos:
                                sentiment = "🔴"
                            else:
                                sentiment = "⚪"
                            items.append({
                                "title": item.get("title", ""),
                                "source": item.get("source", {}).get("title", ""),
                                "url": item.get("url", ""),
                                "age_min": age_min,
                                "sentiment": sentiment,
                            })
        except Exception:
            pass

    if not items:
        # RSS fallback
        now = datetime.now(timezone.utc)
        import time
        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                source = feed.feed.get("title", feed_url.split("/")[2])
                for entry in feed.entries[:5]:
                    published = entry.get("published_parsed")
                    if published:
                        age_min = int((now.timestamp() - time.mktime(published)) / 60)
                    else:
                        age_min = 0
                    items.append({
                        "title": entry.get("title", ""),
                        "source": source,
                        "url": entry.get("link", ""),
                        "age_min": age_min,
                        "sentiment": "⚪",
                    })
                if len(items) >= limit:
                    break
            except Exception:
                continue

    # Sort by freshness
    items.sort(key=lambda x: x["age_min"])
    return items[:limit]


async def fetch_fear_greed() -> dict:
    """Returns current Fear & Greed index value and label."""
    try:
        async with _make_session() as session:
            async with session.get(FEAR_GREED_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return {"value": 50, "label": "Neutral", "emoji": "😐"}
                data = await resp.json()
        value = int(data["data"][0]["value"])
        classification = data["data"][0]["value_classification"]
        if value <= 25:
            emoji = "😱"
        elif value <= 45:
            emoji = "😟"
        elif value <= 55:
            emoji = "😐"
        elif value <= 75:
            emoji = "😄"
        else:
            emoji = "🤑"
        return {"value": value, "label": classification, "emoji": emoji}
    except Exception:
        return {"value": 50, "label": "Neutral", "emoji": "😐"}
