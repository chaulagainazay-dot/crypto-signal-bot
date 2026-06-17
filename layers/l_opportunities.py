"""
Buying Opportunities Scanner
Scans an extended coin list beyond the watchlist, scores each for entry quality,
and returns a ranked list of the best setups right now.

Opportunity score criteria (all from the framework):
  - Price above EMA200 on 1h (trend filter — long only)
  - RSI between 30–55 (not overextended, potential momentum resumption)
  - MACD histogram turning from negative to positive (momentum shift)
  - Price within 1% of EMA21 or VWAP (low-risk entry zone)
  - Regime = trending or ranging (never chaotic)
  - Volume above 20-period average (confirmation)
  - ATR/price ratio reasonable (not insanely volatile)
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice

from layers.l2_technical import fetch_ohlcv, _compute_indicators, _classify_regime

# Extended scan list — liquid majors + high-cap alts
OPPORTUNITY_LIST = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT", "MATIC/USDT",
    "TON/USDT", "DOGE/USDT", "SHIB/USDT", "LTC/USDT", "UNI/USDT",
    "ATOM/USDT", "NEAR/USDT", "FTM/USDT", "OP/USDT", "ARB/USDT",
]


@dataclass
class Opportunity:
    asset: str
    price: float
    score: float          # 0–100
    grade: str            # A / B / C
    rsi: float
    dist_ema21_pct: float
    regime: str
    reason: str           # human-readable bullet list of why
    entry_zone: str
    stop_loss: float
    tp1: float
    tp2: float
    atr: float


def _opportunity_score(ind: dict, price: float, df: pd.DataFrame) -> tuple[float, list[str]]:
    """Returns (score 0-100, list of reason strings)."""
    score = 0.0
    reasons = []

    # 1. Trend filter — price above EMA200 (+25 pts)
    if price > ind["ema200"]:
        score += 25
        reasons.append("Price above EMA200 (uptrend confirmed)")
    else:
        reasons.append("⚠️ Below EMA200 (counter-trend — risky)")

    # 2. RSI sweet spot 30–55 (+20 pts for 35–52, +10 for 30–35 or 52–60)
    rsi = ind["rsi"]
    if 35 <= rsi <= 52:
        score += 20
        reasons.append(f"RSI {rsi:.0f} — ideal accumulation zone (35–52)")
    elif 28 <= rsi < 35:
        score += 12
        reasons.append(f"RSI {rsi:.0f} — oversold bounce candidate")
    elif 52 < rsi <= 62:
        score += 8
        reasons.append(f"RSI {rsi:.0f} — momentum building, not overextended")
    elif rsi > 70:
        score -= 10
        reasons.append(f"RSI {rsi:.0f} — overbought, wait for pullback")
    else:
        reasons.append(f"RSI {rsi:.0f} — neutral")

    # 3. MACD histogram turning positive (+20 pts)
    hist_now = ind["macd_hist"]
    hist_prev = float(
        MACD(df["close"], window_fast=12, window_slow=26, window_sign=9)
        .macd_diff().iloc[-2]
    )
    if hist_now > 0 and hist_prev <= 0:
        score += 20
        reasons.append("MACD histogram just turned positive (momentum shift)")
    elif hist_now > hist_prev > 0:
        score += 12
        reasons.append("MACD histogram rising (momentum building)")
    elif hist_now > 0:
        score += 6
        reasons.append("MACD positive but flat")
    else:
        reasons.append("MACD negative (no momentum yet)")

    # 4. Proximity to EMA21 or VWAP (+20 pts)
    dist_ema21 = abs(price - ind["ema21"]) / ind["ema21"] * 100
    dist_vwap = abs(price - ind["vwap"]) / ind["vwap"] * 100
    if dist_ema21 < 0.5 or dist_vwap < 0.3:
        score += 20
        reasons.append(f"Price at EMA21/VWAP support ({dist_ema21:.1f}% away) — low-risk entry")
    elif dist_ema21 < 1.5:
        score += 10
        reasons.append(f"Price near EMA21 ({dist_ema21:.1f}% away)")
    else:
        reasons.append(f"Price {dist_ema21:.1f}% from EMA21 — wait for pullback")

    # 5. Volume confirmation (+10 pts)
    recent_vol = df["volume"].iloc[-1]
    avg_vol = df["volume"].iloc[-20:].mean()
    if recent_vol > avg_vol * 1.3:
        score += 10
        reasons.append("Volume spike (+30% above 20-period avg) — buyers active")
    elif recent_vol > avg_vol:
        score += 5
        reasons.append("Volume above average")
    else:
        reasons.append("Below-average volume — weak conviction")

    # 6. ADX trending (+5 pts bonus)
    if ind["adx"] > 25:
        score += 5
        reasons.append(f"ADX {ind['adx']:.0f} — strong trend structure")

    return min(100.0, score), reasons


def _grade(score: float) -> str:
    if score >= 75:
        return "A"
    elif score >= 55:
        return "B"
    elif score >= 35:
        return "C"
    return "D"


async def _scan_asset(asset: str) -> Optional[Opportunity]:
    try:
        df = await fetch_ohlcv(asset, "1h", limit=250)
        price = float(df["close"].iloc[-1])
        ind = _compute_indicators(df)
        regime = _classify_regime(ind["adx"], ind["atr"], df)

        if regime == "chaotic":
            return None

        score, reasons = _opportunity_score(ind, price, df)

        # Only return C grade or better (score >= 35)
        if score < 35:
            return None

        grade = _grade(score)
        stop_dist = 1.5 * ind["atr"]
        sl = price - stop_dist
        tp1 = price + 1.5 * stop_dist
        tp2 = price + 2.5 * stop_dist
        dist_ema21 = abs(price - ind["ema21"]) / ind["ema21"] * 100

        fmt_p = f"${price:,.2f}" if price >= 1 else f"${price:.6f}"
        entry_zone = f"${price * 0.998:,.4f} – {fmt_p}"

        return Opportunity(
            asset=asset,
            price=price,
            score=score,
            grade=grade,
            rsi=ind["rsi"],
            dist_ema21_pct=dist_ema21,
            regime=regime,
            reason="\n".join(f"  • {r}" for r in reasons),
            entry_zone=entry_zone,
            stop_loss=sl,
            tp1=tp1,
            tp2=tp2,
            atr=ind["atr"],
        )
    except Exception:
        return None


async def scan_opportunities(top_n: int = 5) -> list[Opportunity]:
    """Scans the full opportunity list and returns top_n ranked setups."""
    tasks = [_scan_asset(asset) for asset in OPPORTUNITY_LIST]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    opps = [r for r in results if isinstance(r, Opportunity)]
    opps.sort(key=lambda x: x.score, reverse=True)
    return opps[:top_n]


def format_opportunities(opps: list[Opportunity]) -> str:
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    if not opps:
        return (
            "🔍 *Buying Opportunities*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "_No setups meet the minimum criteria right now._\n"
            "_Market may be overextended or in chaotic regime._"
        )

    grade_emoji = {"A": "🥇", "B": "🥈", "C": "🥉", "D": "❌"}
    lines = [f"🔍 *Buying Opportunities* — {now}\n━━━━━━━━━━━━━━━━━━━━━━"]

    for i, opp in enumerate(opps, 1):
        p = opp.price
        fmt_p = f"${p:,.2f}" if p >= 1 else f"${p:.6f}"
        sl_fmt = f"${opp.stop_loss:,.4f}" if opp.stop_loss < 10 else f"${opp.stop_loss:,.2f}"
        tp1_fmt = f"${opp.tp1:,.4f}" if opp.tp1 < 10 else f"${opp.tp1:,.2f}"
        ge = grade_emoji.get(opp.grade, "")
        score_bar = "█" * int(opp.score / 10) + "░" * (10 - int(opp.score / 10))

        lines.append(
            f"\n{ge} *#{i} {opp.asset}* — Grade {opp.grade}  `{opp.score:.0f}/100`\n"
            f"`[{score_bar}]`\n"
            f"💲 Price: `{fmt_p}`  |  RSI: `{opp.rsi:.0f}`  |  Regime: `{opp.regime}`\n"
            f"📍 Entry: `{opp.entry_zone}`\n"
            f"🛑 SL: `{sl_fmt}`  🎯 TP1: `{tp1_fmt}`\n"
            f"*Why this setup:*\n{opp.reason}"
        )
        if i < len(opps):
            lines.append("\n─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─")

    lines.append(
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ _Paper-trade only. Scores are educational, not guaranteed._"
    )
    return "\n".join(lines)
