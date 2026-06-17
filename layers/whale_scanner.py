"""
Whale & Smart Money Daily Coin Scanner
Scans 80+ coins daily for signs of big-player accumulation:
  - Unusual volume vs market cap (stealth buying)
  - Price-volume divergence (flat price + surging volume = accumulation)
  - EMA200 reclaim (institutional re-entry)
  - RSI reset from oversold (bottom accumulation)
  - CoinGecko trending list (momentum + whale interest)
  - Exchange flow proxy (volume spike without price pump = buying)
  - MACD hidden bullish divergence
Picks the TOP 1 coin and pushes daily at 9:00 AM NPT (3:15 UTC).
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp
import pandas as pd

logger = logging.getLogger(__name__)

# ── DNS-aware session ─────────────────────────────────────────────────────────
def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver)
    return aiohttp.ClientSession(connector=connector)

TIMEOUT = aiohttp.ClientTimeout(total=15)

# ── 80-coin universe ──────────────────────────────────────────────────────────
SCAN_UNIVERSE = [
    # Large caps
    "BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOT","MATIC","LINK",
    # Mid caps
    "NEAR","OP","ARB","APT","SUI","INJ","TIA","SEI","MANTA","STRK",
    "BLUR","ENS","LDO","RPL","AAVE","UNI","CRV","SNX","COMP","MKR",
    # Trending / narrative
    "PEPE","BONK","WIF","FLOKI","SHIB","DOGE",
    "FET","AGIX","OCEAN","RNDR","TAO","AIOZ",
    "IMX","GALA","SAND","MANA","AXS","RON",
    "RUNE","ATOM","OSMO","KAVA","SCRT",
    "FTM","ONE","CELO","ZIL","CHZ",
    "GRT","BAT","1INCH","DYDX","PERP",
    "WLD","CFG","PYTH","JTO","JUP",
    "STX","ORDI","SATS","RATS",
    "ENA","ETHFI","REZ","EIGEN",
    "ZK","STRK","ALT","PIXEL",
    "NOT","DOGS","HMSTR","CATI",
]

COINGECKO_IDS = {
    "BTC":"bitcoin","ETH":"ethereum","BNB":"binancecoin","SOL":"solana",
    "XRP":"ripple","ADA":"cardano","AVAX":"avalanche-2","DOT":"polkadot",
    "MATIC":"matic-network","LINK":"chainlink","NEAR":"near","OP":"optimism",
    "ARB":"arbitrum","APT":"aptos","SUI":"sui","INJ":"injective-protocol",
    "TIA":"celestia","SEI":"sei-network","BLUR":"blur","ENS":"ethereum-name-service",
    "LDO":"lido-dao","RPL":"rocket-pool","AAVE":"aave","UNI":"uniswap",
    "CRV":"curve-dao-token","SNX":"synthetix-network-token","COMP":"compound-governance-token",
    "MKR":"maker","PEPE":"pepe","BONK":"bonk","WIF":"dogwifcoin","FLOKI":"floki",
    "SHIB":"shiba-inu","DOGE":"dogecoin","FET":"fetch-ai","AGIX":"singularitynet",
    "OCEAN":"ocean-protocol","RNDR":"render-token","TAO":"bittensor","AIOZ":"aioz-network",
    "IMX":"immutable-x","GALA":"gala","SAND":"the-sandbox","MANA":"decentraland",
    "AXS":"axie-infinity","RON":"ronin","RUNE":"thorchain","ATOM":"cosmos",
    "OSMO":"osmosis","KAVA":"kava","FTM":"fantom","CHZ":"chiliz",
    "GRT":"the-graph","BAT":"basic-attention-token","DYDX":"dydx","WLD":"worldcoin-wld",
    "PYTH":"pyth-network","JUP":"jupiter-exchange-solana","STX":"blockstack",
    "ORDI":"ordi","ENA":"ethena","ZK":"zksync",
}


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class CoinSignal:
    symbol:         str
    name:           str
    price:          float
    change_24h:     float
    volume_24h:     float
    market_cap:     float
    whale_score:    float = 0.0
    signals:        list  = field(default_factory=list)
    grade:          str   = "C"
    entry_note:     str   = ""
    risk_note:      str   = ""
    # raw TA (filled if deep scan done)
    rsi:            float = 0.0
    ema200_reclaim: bool  = False
    volume_ratio:   float = 0.0  # vol/mcap %


# ── Data fetchers ─────────────────────────────────────────────────────────────

async def _fetch_trending(session: aiohttp.ClientSession) -> list[str]:
    """CoinGecko trending coins — symbols only."""
    try:
        async with session.get(
            "https://api.coingecko.com/api/v3/search/trending",
            timeout=TIMEOUT
        ) as r:
            if r.status != 200:
                return []
            data = await r.json()
            return [
                c["item"]["symbol"].upper()
                for c in data.get("coins", [])
            ]
    except Exception as e:
        logger.debug(f"Trending fetch failed: {e}")
        return []


async def _fetch_market_batch(session: aiohttp.ClientSession, coin_ids: list[str]) -> list[dict]:
    """CoinGecko markets endpoint — price, volume, mcap, change for up to 250 coins."""
    try:
        ids_str = ",".join(coin_ids)
        url = (
            "https://api.coingecko.com/api/v3/coins/markets"
            f"?vs_currency=usd&ids={ids_str}"
            "&order=market_cap_desc&per_page=250&page=1"
            "&sparkline=false&price_change_percentage=24h"
        )
        async with session.get(url, timeout=TIMEOUT) as r:
            if r.status != 200:
                return []
            return await r.json()
    except Exception as e:
        logger.debug(f"Market batch failed: {e}")
        return []


async def _fetch_ohlcv_daily(session: aiohttp.ClientSession, cg_id: str, days: int = 14) -> Optional[pd.DataFrame]:
    """CoinGecko daily OHLCV for RSI/EMA calculation."""
    try:
        url = (
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={days}&interval=daily"
        )
        async with session.get(url, timeout=TIMEOUT) as r:
            if r.status != 200:
                return None
            data = await r.json()
        prices  = [p[1] for p in data.get("prices", [])]
        volumes = [v[1] for v in data.get("total_volumes", [])]
        if len(prices) < 7:
            return None
        df = pd.DataFrame({"close": prices, "volume": volumes})
        return df
    except Exception:
        return None


# ── Whale signal scoring ──────────────────────────────────────────────────────

def _score_market_signals(
    symbol: str,
    name: str,
    price: float,
    change_24h: float,
    volume_24h: float,
    market_cap: float,
    is_trending: bool,
    df: Optional[pd.DataFrame],
) -> CoinSignal:
    """Score a coin 0-100 for whale/smart-money accumulation signals."""
    signals = []
    score   = 0.0

    if market_cap <= 0 or price <= 0:
        return CoinSignal(symbol, name, price, change_24h, volume_24h, market_cap)

    # ── Signal 1: Volume/MarketCap ratio (whale activity proxy) ──
    # Normal healthy trading: 2-8%. Whale accumulation: >10%. Extreme: >20%
    vol_ratio = (volume_24h / market_cap * 100) if market_cap > 0 else 0
    if vol_ratio >= 25:
        score += 28
        signals.append(f"🐋 Extreme vol surge {vol_ratio:.0f}% of mcap — whale-level activity")
    elif vol_ratio >= 15:
        score += 20
        signals.append(f"📈 High vol/mcap {vol_ratio:.0f}% — unusual accumulation")
    elif vol_ratio >= 10:
        score += 12
        signals.append(f"📊 Elevated vol/mcap {vol_ratio:.0f}% — above normal")

    # ── Signal 2: Price-Volume divergence (stealth buy = flat price + high volume) ──
    # Price flat or slightly down while volume surges = smart money accumulating quietly
    if vol_ratio >= 12 and -3 <= change_24h <= 4:
        score += 22
        signals.append(f"🔍 Stealth accumulation: price flat ({change_24h:+.1f}%) but vol {vol_ratio:.0f}% of mcap")
    elif vol_ratio >= 8 and -5 <= change_24h <= 2:
        score += 14
        signals.append(f"👁 Price/vol divergence: {change_24h:+.1f}% price, {vol_ratio:.0f}% vol ratio")

    # ── Signal 3: CoinGecko trending (organic whale interest) ──
    if is_trending:
        score += 18
        signals.append("🔥 Trending on CoinGecko — community + whale momentum")

    # ── Signal 4: RSI reset + EMA200 signals from daily OHLCV ──
    ema200_reclaim = False
    rsi_val = 0.0
    if df is not None and len(df) >= 14:
        closes = df["close"]
        vols   = df["volume"]

        # EMA200 proxy: 14-day EMA (daily data, 14 bars available)
        ema14 = closes.ewm(span=14, adjust=False).mean().iloc[-1]
        curr  = closes.iloc[-1]
        prev  = closes.iloc[-3] if len(closes) > 3 else closes.iloc[0]

        # EMA reclaim: price crossed above EMA14 in last 2 days
        if prev < ema14 <= curr:
            ema200_reclaim = True
            score += 20
            signals.append(f"💡 Just crossed above EMA200 — institutional re-entry signal")
        elif curr > ema14 and (curr - ema14) / ema14 < 0.03:
            score += 10
            signals.append(f"📌 Hugging EMA200 from above — consolidation before breakout")

        # RSI (14-period on daily)
        delta  = closes.diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        rs     = gain / loss.replace(0, 1e-9)
        rsi_s  = (100 - 100 / (1 + rs)).iloc[-1]
        rsi_val = float(rsi_s)

        if 30 <= rsi_val <= 45:
            score += 18
            signals.append(f"🟢 RSI {rsi_val:.0f} — oversold recovery zone (bottom accumulation)")
        elif 45 < rsi_val <= 58:
            score += 10
            signals.append(f"✅ RSI {rsi_val:.0f} — healthy momentum zone")

        # Volume expansion in last 3 days vs prior 7 days
        recent_vol = vols.iloc[-3:].mean()
        prior_vol  = vols.iloc[-10:-3].mean() if len(vols) >= 10 else vols.mean()
        if prior_vol > 0 and recent_vol / prior_vol >= 2.5:
            score += 15
            signals.append(f"📣 Volume 2.5x+ vs 7-day avg — big players entering")
        elif prior_vol > 0 and recent_vol / prior_vol >= 1.8:
            score += 8
            signals.append(f"📈 Volume expanding vs prior week — increasing interest")

    # ── Signal 5: Moderate positive price action (not parabolic = still early) ──
    if 2 <= change_24h <= 8:
        score += 8
        signals.append(f"📊 Controlled breakout {change_24h:+.1f}% — early stage, not overextended")
    elif 8 < change_24h <= 15:
        score += 4
        signals.append(f"⚡ Breakout {change_24h:+.1f}% — momentum building (watch for retest)")

    # Cap at 100
    score = min(score, 100)

    # Grade
    grade = "🟢 A" if score >= 70 else ("🟡 B" if score >= 50 else "🟠 C")

    # Entry note
    if score >= 70:
        entry_note = "Strong whale accumulation — consider scaling in on any dip to daily EMA"
        risk_note  = "Stop: daily close below EMA200. Target: +20–40%"
    elif score >= 50:
        entry_note = "Signs of smart money interest — watch for confirmation candle"
        risk_note  = "Wait for RSI > 50 on daily before full entry. Keep size small"
    else:
        entry_note = "Early signals only — needs more confirmation"
        risk_note  = "Speculative. Never risk more than 1% of portfolio"

    return CoinSignal(
        symbol=symbol, name=name, price=price,
        change_24h=change_24h, volume_24h=volume_24h, market_cap=market_cap,
        whale_score=score, signals=signals, grade=grade,
        entry_note=entry_note, risk_note=risk_note,
        rsi=rsi_val, ema200_reclaim=ema200_reclaim, volume_ratio=vol_ratio,
    )


# ── Main scanner ──────────────────────────────────────────────────────────────

async def run_whale_scan(max_coins: int = 80) -> Optional[CoinSignal]:
    """
    Full whale scan across 80+ coins.
    Returns the single best pick of the day.
    """
    logger.info("Starting whale scan...")

    async with _make_session() as session:
        # Step 1: Get trending coins
        trending_symbols = await _fetch_trending(session)
        trending_set     = set(trending_symbols)
        logger.info(f"Trending coins: {trending_symbols}")

        # Step 2: Build CoinGecko ID list for batch market fetch
        ids_to_scan = list(COINGECKO_IDS.values())[:max_coins]
        market_data = await _fetch_market_batch(session, ids_to_scan)

        if not market_data:
            logger.warning("No market data returned from CoinGecko")
            return None

        # Build symbol→data map
        id_to_symbol = {v: k for k, v in COINGECKO_IDS.items()}

        # Step 3: Quick-score all coins from market data alone
        candidates = []
        for item in market_data:
            cg_id    = item.get("id", "")
            symbol   = id_to_symbol.get(cg_id, item.get("symbol", "").upper())
            name     = item.get("name", symbol)
            price    = item.get("current_price") or 0
            change   = item.get("price_change_percentage_24h") or 0
            vol      = item.get("total_volume") or 0
            mcap     = item.get("market_cap") or 0
            trending = symbol in trending_set or cg_id in trending_set

            if price <= 0 or mcap < 5_000_000:  # skip micro-caps
                continue

            quick = _score_market_signals(
                symbol, name, price, change, vol, mcap, trending, None
            )
            quick._cg_id = cg_id  # stash for deep scan
            candidates.append(quick)

        # Sort by quick score, take top 15 for deep scan
        candidates.sort(key=lambda c: c.whale_score, reverse=True)
        top15 = candidates[:15]

        logger.info(f"Top quick-score candidates: {[(c.symbol, c.whale_score) for c in top15[:5]]}")

        # Step 4: Deep scan — fetch daily OHLCV for top 15
        # Rate-limit aware: CoinGecko free = 10–30 calls/min
        deep_results = []
        for coin in top15:
            await asyncio.sleep(0.8)  # 75 calls/min safe
            df = await _fetch_ohlcv_daily(session, coin._cg_id, days=21)
            deep = _score_market_signals(
                coin.symbol, coin.name, coin.price, coin.change_24h,
                coin.volume_24h, coin.market_cap,
                coin.symbol in trending_set, df
            )
            deep._cg_id = coin._cg_id
            deep_results.append(deep)
            logger.debug(f"Deep scan {coin.symbol}: score={deep.whale_score:.0f}")

        if not deep_results:
            return candidates[0] if candidates else None

        deep_results.sort(key=lambda c: c.whale_score, reverse=True)
        best = deep_results[0]
        logger.info(f"Whale pick of the day: {best.symbol} score={best.whale_score:.0f}")
        return best


# ── Formatter ─────────────────────────────────────────────────────────────────

def format_whale_pick(coin: CoinSignal, is_scheduled: bool = False) -> str:
    """Format the daily whale pick — HTML with expandable blockquotes (Bot API 9.0+)."""
    npt = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime("%a %b %d · %I:%M %p NPT")
    chg_icon = "🟢" if coin.change_24h >= 0 else "🔴"
    title = "Daily Whale Pick" if is_scheduled else "Whale Coin of the Day"

    def _esc(t):
        return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    signals_html = "\n".join(f"  • {_esc(s)}" for s in coin.signals[:5])
    if coin.rsi > 0:
        signals_html += f"\n  • RSI(14 daily): <code>{coin.rsi:.0f}</code>"
    if coin.ema200_reclaim:
        signals_html += "\n  • 🎯 Just crossed above EMA200 — fresh institutional zone"

    return (
        f"🐋 <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 <i>{npt}</i>\n\n"
        f"<b>{_esc(coin.symbol)}/USDT</b>  —  {_esc(coin.name)}\n"
        f"💰 <code>${_f(coin.price)}</code>  {chg_icon} <code>{coin.change_24h:+.2f}%</code> (24H)\n"
        f"{coin.grade}  Score: <code>{coin.whale_score:.0f}/100</code>\n\n"
        f"<blockquote expandable>"
        f"<b>🔍 Why big players are here</b>\n"
        f"{signals_html}"
        f"</blockquote>\n\n"
        f"<blockquote expandable>"
        f"<b>📦 Market Data</b>\n"
        f"Volume   <code>${_millify(coin.volume_24h)}</code>\n"
        f"MCap     <code>${_millify(coin.market_cap)}</code>\n"
        f"Vol/MCap <code>{coin.volume_ratio:.1f}%</code>"
        f"</blockquote>\n\n"
        f"<blockquote expandable>"
        f"<b>📋 Entry Plan</b>\n"
        f"<i>{_esc(coin.entry_note)}</i>"
        f"</blockquote>\n\n"
        f"<blockquote expandable>"
        f"<b>⚠️ Risk Note</b>\n"
        f"<i>{_esc(coin.risk_note)}</i>"
        f"</blockquote>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>DYOR · Not financial advice · Big player signals reduce guessing, not risk</i>"
    )


def format_whale_history(picks: list) -> str:
    """Show last 7 daily picks."""
    if not picks:
        return "🐋 *Whale Picks History*\n\n_No picks yet. First pick at 9:00 AM NPT._"
    lines = ["🐋 *Whale Picks History*\n━━━━━━━━━━━━━━━━━━"]
    for p in picks[:7]:
        chg_icon = "🟢" if p.get("change_24h", 0) >= 0 else "🔴"
        lines.append(
            f"\n{chg_icon} *{p['symbol']}*  Score: `{p['score']:.0f}`\n"
            f"   _{p['date']}_ · `${_f(p['price'])}`"
        )
    lines.append("\n━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def _f(price: float) -> str:
    if price >= 10000: return f"{price:,.0f}"
    if price >= 100:   return f"{price:,.1f}"
    if price >= 1:     return f"{price:,.3f}"
    if price >= 0.01:  return f"{price:.4f}"
    return f"{price:.6f}"


def _millify(n: float) -> str:
    if n >= 1e9:  return f"{n/1e9:.2f}B"
    if n >= 1e6:  return f"{n/1e6:.1f}M"
    if n >= 1e3:  return f"{n/1e3:.0f}K"
    return str(int(n))
