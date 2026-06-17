"""
Token Deep Dive — comprehensive single-coin analysis.
Fetches: CoinGecko market data + ATH/ATL + social links +
         live TA (RSI/EMA/MACD) + risk scoring.
Output uses HTML + <blockquote expandable> (Bot API 9.0+).
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False)
    return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=15))

def _esc(text: str) -> str:
    """Escape HTML special chars."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── CoinGecko search + data ───────────────────────────────────────────────────

async def _search_coin(session, query: str) -> dict:
    """Find coin id by symbol or name."""
    query = query.lower().strip()
    try:
        async with session.get(
            "https://api.coingecko.com/api/v3/search",
            params={"query": query}
        ) as r:
            data = await r.json()
        coins = data.get("coins", [])
        # Prefer exact symbol match, then name match
        for coin in coins:
            if coin.get("symbol", "").lower() == query:
                return {"id": coin["id"], "symbol": coin["symbol"].upper(), "name": coin["name"]}
        for coin in coins:
            if query in coin.get("name", "").lower():
                return {"id": coin["id"], "symbol": coin["symbol"].upper(), "name": coin["name"]}
        if coins:
            return {"id": coins[0]["id"], "symbol": coins[0]["symbol"].upper(), "name": coins[0]["name"]}
    except Exception as e:
        log.warning(f"CoinGecko search failed: {e}")
    return None


async def _fetch_coin_data(session, coin_id: str) -> dict:
    """Full CoinGecko coin data including ATH, ATL, supply, links."""
    try:
        async with session.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "false",
                "sparkline": "false",
            }
        ) as r:
            return await r.json()
    except Exception as e:
        log.warning(f"CoinGecko coin data failed: {e}")
        return None


async def _fetch_ohlcv(session, coin_id: str, days: int = 30) -> list:
    """Fetch daily OHLCV for TA calculations."""
    try:
        async with session.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": str(days)}
        ) as r:
            data = await r.json()
            return data if isinstance(data, list) else []
    except Exception:
        return []


# ── Technical Analysis (without ccxt) ────────────────────────────────────────

def _calc_rsi(closes: list, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _calc_ema(closes: list, period: int) -> float:
    if len(closes) < period:
        return closes[-1] if closes else 0
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 8)


def _calc_volatility(closes: list, period: int = 14) -> float:
    """Daily % volatility (std of returns)."""
    if len(closes) < 2:
        return 0.0
    returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes))]
    recent = returns[-period:]
    mean = sum(recent) / len(recent)
    variance = sum((r - mean)**2 for r in recent) / len(recent)
    return round(variance ** 0.5, 2)


# ── Risk Scoring ─────────────────────────────────────────────────────────────

def _risk_score(data: dict, closes: list) -> dict:
    """Score 0-100 (0=safe, 100=extreme risk). Returns sub-scores + flags."""
    d = data.get("market_data", {})
    market_cap = d.get("market_cap", {}).get("usd", 0) or 0
    volume_24h  = d.get("total_volume", {}).get("usd", 0) or 0
    price       = d.get("current_price", {}).get("usd", 0) or 0
    ath         = d.get("ath", {}).get("usd", 0) or 0
    rank        = data.get("market_cap_rank") or 9999
    chg_7d      = d.get("price_change_percentage_7d_in_currency", {}).get("usd", 0) or 0
    chg_30d     = d.get("price_change_percentage_30d_in_currency", {}).get("usd", 0) or 0

    scores = {}
    flags  = []

    # Market cap risk: < $100M is high risk
    if market_cap < 50_000_000:
        scores["market_cap"] = 40
        flags.append("⚠️ Micro-cap — extreme liquidity risk")
    elif market_cap < 500_000_000:
        scores["market_cap"] = 25
        flags.append("⚠️ Small-cap — higher volatility")
    elif market_cap < 5_000_000_000:
        scores["market_cap"] = 10
    else:
        scores["market_cap"] = 0

    # Liquidity: volume/mcap ratio
    liq_ratio = volume_24h / market_cap if market_cap else 0
    if liq_ratio < 0.01:
        scores["liquidity"] = 30
        flags.append("⚠️ Low volume — hard to exit large positions")
    elif liq_ratio < 0.05:
        scores["liquidity"] = 15
    else:
        scores["liquidity"] = 0

    # ATH drawdown
    ath_drawdown = ((ath - price) / ath * 100) if ath > 0 else 0
    if ath_drawdown > 90:
        scores["ath_drawdown"] = 20
        flags.append("⚠️ >90% below ATH — potential dead project or deep accumulation")
    elif ath_drawdown > 70:
        scores["ath_drawdown"] = 10
    else:
        scores["ath_drawdown"] = 0

    # Volatility
    vol = _calc_volatility(closes, 14) if closes else 0
    if vol > 8:
        scores["volatility"] = 20
        flags.append(f"⚠️ High daily volatility ({vol:.1f}%)")
    elif vol > 4:
        scores["volatility"] = 10
    else:
        scores["volatility"] = 0

    # 30d trend
    if chg_30d < -40:
        scores["trend"] = 10
        flags.append("⚠️ Strong downtrend last 30 days")
    elif chg_30d > 100:
        scores["trend"] = 10
        flags.append("⚠️ Parabolic move — overbought risk")
    else:
        scores["trend"] = 0

    total = sum(scores.values())
    level = (
        ("🟢", "LOW", "Well-established asset, manageable risk")
        if total <= 15 else
        ("🟡", "MEDIUM", "Some caution needed, watch position size")
        if total <= 35 else
        ("🟠", "HIGH", "Significant risks — small allocation only")
        if total <= 55 else
        ("🔴", "VERY HIGH", "Speculative — only trade what you can afford to lose")
    )
    return {"total": total, "level": level, "flags": flags, "sub": scores, "volatility": vol}


# ── Opportunity Score ─────────────────────────────────────────────────────────

def _opportunity_score(data: dict, closes: list, rsi: float) -> dict:
    d = data.get("market_data", {})
    chg_7d  = d.get("price_change_percentage_7d_in_currency",  {}).get("usd", 0) or 0
    chg_30d = d.get("price_change_percentage_30d_in_currency", {}).get("usd", 0) or 0
    volume  = d.get("total_volume", {}).get("usd", 0) or 0
    mcap    = d.get("market_cap",   {}).get("usd", 0) or 0
    price   = d.get("current_price", {}).get("usd", 0) or 0
    ath     = d.get("ath", {}).get("usd", 0) or 0

    score  = 0
    notes  = []

    # RSI oversold → opportunity
    if rsi < 35:
        score += 25
        notes.append(f"✅ RSI oversold ({rsi:.0f}) — potential bounce zone")
    elif rsi < 45:
        score += 15
        notes.append(f"✅ RSI below midpoint ({rsi:.0f}) — watch for reversal")
    elif rsi > 70:
        score -= 15
        notes.append(f"⚠️ RSI overbought ({rsi:.0f}) — reduce entries")

    # Recovering from selloff
    if -30 < chg_30d < -10 and chg_7d > 3:
        score += 20
        notes.append("✅ Bouncing from 30d drawdown — possible recovery")

    # Strong 7d momentum
    if 10 < chg_7d < 40:
        score += 15
        notes.append(f"✅ Strong 7d momentum (+{chg_7d:.1f}%)")

    # Far from ATH = room to grow
    ath_dist = ((ath - price) / ath * 100) if ath > 0 else 0
    if 40 < ath_dist < 80:
        score += 15
        notes.append(f"✅ {ath_dist:.0f}% below ATH — significant recovery potential")
    elif ath_dist > 80:
        score += 5
        notes.append(f"⚡ {ath_dist:.0f}% below ATH — high risk/reward")

    # High volume relative to mcap
    if mcap and volume / mcap > 0.08:
        score += 10
        notes.append("✅ High volume-to-mcap ratio — active interest")

    score = max(0, min(100, score))
    grade = (
        "🟢 Strong Buy Zone"  if score >= 60 else
        "🟡 Watch Closely"    if score >= 40 else
        "⚪ Neutral"          if score >= 20 else
        "🔴 Avoid for Now"
    )
    return {"score": score, "grade": grade, "notes": notes}


# ── Price formatter ───────────────────────────────────────────────────────────

def _fp(p: float) -> str:
    if p is None or p == 0: return "$0"
    if p >= 10000: return f"${p:,.0f}"
    if p >= 100:   return f"${p:,.2f}"
    if p >= 1:     return f"${p:,.4f}"
    if p >= 0.01:  return f"${p:.6f}"
    return f"${p:.8f}"

def _mill(n: float) -> str:
    if n is None or n == 0: return "$0"
    if n >= 1e12: return f"${n/1e12:.2f}T"
    if n >= 1e9:  return f"${n/1e9:.2f}B"
    if n >= 1e6:  return f"${n/1e6:.1f}M"
    if n >= 1e3:  return f"${n/1e3:.0f}K"
    return f"${n:.0f}"


# ── Format HTML message ───────────────────────────────────────────────────────

def format_deep_dive_html(data: dict, search_info: dict, closes: list) -> str:
    """Returns full HTML message using Bot API 9.0+ formatting."""
    d = data.get("market_data", {})
    name   = _esc(data.get("name", "Unknown"))
    symbol = _esc(data.get("symbol", "?").upper())
    rank   = data.get("market_cap_rank", "?")

    price   = d.get("current_price", {}).get("usd") or 0
    mcap    = d.get("market_cap",   {}).get("usd") or 0
    vol_24h = d.get("total_volume", {}).get("usd") or 0
    fdv     = d.get("fully_diluted_valuation", {}).get("usd") or 0
    supply_circ = d.get("circulating_supply") or 0
    supply_max  = d.get("max_supply") or 0
    supply_tot  = d.get("total_supply") or 0

    chg_1h  = d.get("price_change_percentage_1h_in_currency", {}).get("usd") or 0
    chg_24h = d.get("price_change_percentage_24h_in_currency", {}).get("usd") or 0
    chg_7d  = d.get("price_change_percentage_7d_in_currency",  {}).get("usd") or 0
    chg_30d = d.get("price_change_percentage_30d_in_currency", {}).get("usd") or 0
    chg_1y  = d.get("price_change_percentage_1y_in_currency",  {}).get("usd") or 0

    ath     = d.get("ath", {}).get("usd") or 0
    ath_dt  = (d.get("ath_date", {}).get("usd") or "")[:10]
    atl     = d.get("atl", {}).get("usd") or 0
    atl_dt  = (d.get("atl_date", {}).get("usd") or "")[:10]
    ath_chg = d.get("ath_change_percentage", {}).get("usd") or 0
    atl_chg = d.get("atl_change_percentage", {}).get("usd") or 0

    h24_high = d.get("high_24h", {}).get("usd") or 0
    h24_low  = d.get("low_24h",  {}).get("usd") or 0

    # Compute TA
    closes_list = [c[4] for c in closes if len(c) >= 5] if closes else []
    rsi   = _calc_rsi(closes_list) if len(closes_list) >= 15 else 50.0
    ema21 = _calc_ema(closes_list, 21) if len(closes_list) >= 21 else price
    ema50 = _calc_ema(closes_list, 50) if len(closes_list) >= 50 else price

    # Trend
    if price > ema21 > ema50:
        trend = "🟢 UPTREND"
    elif price < ema21 < ema50:
        trend = "🔴 DOWNTREND"
    else:
        trend = "🟡 RANGING"

    # Risk & Opportunity
    risk = _risk_score(data, closes_list)
    opp  = _opportunity_score(data, closes_list, rsi)
    risk_icon, risk_label, risk_desc = risk["level"]

    # Change arrow helpers
    def _arrow(v): return "▲" if v >= 0 else "▼"
    def _color_tag(v, t): return f"<b>{'🟢' if v>=0 else '🔴'} {t}</b>"

    # Social links
    links = data.get("links", {})
    homepage   = (links.get("homepage") or [""])[0]
    twitter    = links.get("twitter_screen_name") or ""
    reddit     = links.get("subreddit_url") or ""
    coingecko_url = f"https://www.coingecko.com/en/coins/{data.get('id','')}"

    # Sentiment
    sent_up   = data.get("sentiment_votes_up_percentage") or 0
    sent_down = data.get("sentiment_votes_down_percentage") or 0

    lines = []

    # ── Header ─────────────────────────────────────────────────────────────
    chg_icon = "🟢" if chg_24h >= 0 else "🔴"
    lines.append(
        f"🔎 <b>{name} ({symbol})</b>  #{rank}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Price</b>  <code>{_fp(price)}</code>  {chg_icon} <code>{chg_24h:+.2f}% (24h)</code>\n"
        f"<b>24H</b>  <code>{_fp(h24_low)} – {_fp(h24_high)}</code>"
    )

    # ── Performance ────────────────────────────────────────────────────────
    lines.append(
        f"\n<blockquote expandable>"
        f"<b>📈 Price Performance</b>\n"
        f"1 Hour   <code>{_arrow(chg_1h)} {chg_1h:+.2f}%</code>\n"
        f"24 Hours <code>{_arrow(chg_24h)} {chg_24h:+.2f}%</code>\n"
        f"7 Days   <code>{_arrow(chg_7d)} {chg_7d:+.2f}%</code>\n"
        f"30 Days  <code>{_arrow(chg_30d)} {chg_30d:+.2f}%</code>\n"
        f"1 Year   <code>{_arrow(chg_1y)} {chg_1y:+.2f}%</code>"
        f"</blockquote>"
    )

    # ── ATH / ATL ──────────────────────────────────────────────────────────
    lines.append(
        f"\n<blockquote expandable>"
        f"<b>🏔 All-Time High &amp; Low</b>\n"
        f"ATH  <code>{_fp(ath)}</code>  <i>{ath_dt}</i>  (<code>{ath_chg:+.1f}%</code> from now)\n"
        f"ATL  <code>{_fp(atl)}</code>  <i>{atl_dt}</i>  (<code>{atl_chg:+.1f}%</code> from now)"
        f"</blockquote>"
    )

    # ── Market Data ────────────────────────────────────────────────────────
    supply_pct = f"{supply_circ/supply_max*100:.1f}%" if supply_max else "∞"
    lines.append(
        f"\n<blockquote expandable>"
        f"<b>🏦 Market Data</b>\n"
        f"Market Cap      <code>{_mill(mcap)}</code>\n"
        f"24H Volume      <code>{_mill(vol_24h)}</code>\n"
        f"FDV             <code>{_mill(fdv)}</code>\n"
        f"Circulating     <code>{supply_circ:,.0f} {symbol}</code>  ({supply_pct} of max)\n"
        f"Max Supply      <code>{'∞' if not supply_max else f'{supply_max:,.0f}'}</code>\n"
        f"Vol/MCap        <code>{vol_24h/mcap*100:.1f}%</code>"
        f"</blockquote>"
    )

    # ── Technical Analysis ─────────────────────────────────────────────────
    rsi_note = "Overbought ⚠️" if rsi > 70 else ("Oversold 🎯" if rsi < 30 else "Neutral ✅")
    lines.append(
        f"\n<blockquote expandable>"
        f"<b>📊 Technical Analysis (30-day Daily)</b>\n"
        f"Trend   <b>{trend}</b>\n"
        f"RSI(14) <code>{rsi:.0f}</code>  <i>{rsi_note}</i>\n"
        f"EMA21   <code>{_fp(ema21)}</code>  {'🟢 above' if price > ema21 else '🔴 below'}\n"
        f"EMA50   <code>{_fp(ema50)}</code>  {'🟢 above' if price > ema50 else '🔴 below'}\n"
        f"Volatility <code>{risk['volatility']:.1f}%</code> / day"
        f"</blockquote>"
    )

    # ── Risk Analysis ──────────────────────────────────────────────────────
    risk_flags_str = "\n".join(risk["flags"]) if risk["flags"] else "✅ No major red flags"
    lines.append(
        f"\n<blockquote expandable>"
        f"<b>⚠️ Risk Analysis</b>\n"
        f"Overall  {risk_icon} <b>{risk_label}</b> (score {risk['total']}/100)\n"
        f"<i>{_esc(risk_desc)}</i>\n\n"
        f"{risk_flags_str}"
        f"</blockquote>"
    )

    # ── Opportunity Score ──────────────────────────────────────────────────
    opp_notes_str = "\n".join(opp["notes"]) if opp["notes"] else "⚪ No strong signals"
    lines.append(
        f"\n<blockquote expandable>"
        f"<b>🎯 Opportunity Score</b>\n"
        f"Score  <code>{opp['score']}/100</code>  {opp['grade']}\n\n"
        f"{opp_notes_str}"
        f"</blockquote>"
    )

    # ── Community Sentiment ────────────────────────────────────────────────
    if sent_up or sent_down:
        bar_up   = "▓" * int(sent_up / 10)
        bar_down = "░" * int(sent_down / 10)
        lines.append(
            f"\n<blockquote expandable>"
            f"<b>💬 Community Sentiment</b>\n"
            f"🟢 Bullish  <code>{sent_up:.1f}%</code>  {bar_up}\n"
            f"🔴 Bearish  <code>{sent_down:.1f}%</code>  {bar_down}"
            f"</blockquote>"
        )

    # ── Links ──────────────────────────────────────────────────────────────
    link_parts = [f'<a href="{coingecko_url}">CoinGecko</a>']
    if homepage:
        link_parts.append(f'<a href="{_esc(homepage)}">Website</a>')
    if twitter:
        link_parts.append(f'<a href="https://twitter.com/{twitter}">Twitter</a>')
    if reddit:
        link_parts.append(f'<a href="{_esc(reddit)}">Reddit</a>')
    lines.append(f"\n🔗  {'  ·  '.join(link_parts)}")

    # ── Footer ─────────────────────────────────────────────────────────────
    lines.append(
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"<i>DYOR · Not financial advice · Paper trade first</i>"
    )

    return "".join(lines)


# ── Main entry ────────────────────────────────────────────────────────────────

async def run_token_deep_dive(query: str) -> tuple:
    """
    Returns (html_text, found_name) or raises on not found.
    html_text uses Bot API 9.0 HTML formatting.
    """
    async with _make_session() as session:
        search = await _search_coin(session, query)
        if not search:
            return None, None

        coin_id = search["id"]
        # Fetch market data + OHLCV in parallel
        data, closes = await asyncio.gather(
            _fetch_coin_data(session, coin_id),
            _fetch_ohlcv(session, coin_id, days=90),
        )
        if not data:
            return None, None

    text = format_deep_dive_html(data, search, closes)
    return text, search["name"]
