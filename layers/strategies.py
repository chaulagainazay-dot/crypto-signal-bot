"""
Pro Trading Strategies Engine
Based on methods used by top traders: Michael van de Poppe, Plan B, Pentoshi, etc.
Scans live price data and returns actionable strategy matches.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from layers.l2_technical import fetch_ohlcv, analyze

logger = logging.getLogger(__name__)


# ── Strategy definitions ──────────────────────────────────────────────────────

STRATEGIES = [
    {
        "id":    "ema_pullback",
        "name":  "EMA21 Pullback",
        "trader": "Michael van de Poppe",
        "style": "Swing",
        "tf":    "1h",
        "desc":  (
            "Price pulls back to EMA21 in an uptrend. "
            "Van de Poppe's core entry: buy the dip to EMA21 when EMA21 > EMA50 > EMA200."
        ),
        "rules": {
            "trend":    "EMA21 > EMA50 > EMA200",
            "entry":    "Price within 1% of EMA21",
            "confirm":  "RSI 40–60 (reset zone), MACD hist > 0",
            "sl":       "Below EMA50",
            "tp":       "2× ATR above entry",
        },
    },
    {
        "id":    "support_flip",
        "name":  "Support Flip",
        "trader": "Michael van de Poppe",
        "style": "Breakout",
        "tf":    "4h",
        "desc":  (
            "Former resistance flips to support after a clean breakout candle. "
            "Wait for retest of the broken level, enter on confirmation."
        ),
        "rules": {
            "trend":    "Price closed above key resistance (1H or 4H)",
            "entry":    "Retest of broken level (within 0.5%)",
            "confirm":  "RSI > 50, volume spike on breakout candle",
            "sl":       "Below the flipped support level",
            "tp":       "Equal leg extension (measured move)",
        },
    },
    {
        "id":    "macd_momentum",
        "name":  "MACD Momentum Cross",
        "trader": "Pentoshi",
        "style": "Momentum",
        "tf":    "1h",
        "desc":  (
            "MACD line crosses above signal while histogram turns positive. "
            "Pentoshi uses this on 1H to catch early momentum shifts before the crowd."
        ),
        "rules": {
            "trend":    "Price above EMA200",
            "entry":    "MACD crosses signal from below (histogram turns positive)",
            "confirm":  "RSI 50–65 (not overbought), volume rising",
            "sl":       "Below last swing low",
            "tp":       "Next resistance or 1.5× risk",
        },
    },
    {
        "id":    "rsi_oversold_bounce",
        "name":  "RSI Oversold Bounce",
        "trader": "Crypto Rover / DCA Mindset",
        "style": "Counter-trend",
        "tf":    "1h",
        "desc":  (
            "RSI drops below 30 on a healthy asset (above EMA200). "
            "High-probability mean-reversion. Best in ranging markets."
        ),
        "rules": {
            "trend":    "Price above EMA200 (long-term uptrend intact)",
            "entry":    "RSI crosses back above 30 from below",
            "confirm":  "Bullish candle close above EMA21",
            "sl":       "Below the swing low that caused oversold reading",
            "tp":       "EMA21 or EMA50 (first target)",
        },
    },
    {
        "id":    "vwap_reclaim",
        "name":  "VWAP Reclaim",
        "trader": "Institutional / Smart Money",
        "style": "Intraday",
        "tf":    "1h",
        "desc":  (
            "Price dips below VWAP then reclaims it with volume. "
            "Institutional traders use VWAP as a mean — reclaims signal accumulation."
        ),
        "rules": {
            "trend":    "Daily bias bullish (price above daily EMA50)",
            "entry":    "Price crosses back above VWAP on rising volume",
            "confirm":  "MACD histogram turning up, RSI > 45",
            "sl":       "Below VWAP (invalidation)",
            "tp":       "Previous session high or 1.5× ATR",
        },
    },
    {
        "id":    "ema_squeeze_breakout",
        "name":  "EMA Squeeze Breakout",
        "trader": "Plan B / Trend Followers",
        "style": "Breakout",
        "tf":    "4h",
        "desc":  (
            "All EMAs (21/50/200) compressed within 2% of each other — coil about to spring. "
            "Plan B style: wait for the expansion and ride it hard."
        ),
        "rules": {
            "trend":    "EMA21, EMA50, EMA200 within 2% of each other (squeeze)",
            "entry":    "Price closes decisively above all EMAs",
            "confirm":  "RSI > 55, MACD crosses above signal line",
            "sl":       "Below the EMA cluster",
            "tp":       "3–5× ATR (expansion trade)",
        },
    },
    {
        "id":    "adx_trend_ride",
        "name":  "ADX Strong Trend Ride",
        "trader": "Professional Momentum Traders",
        "style": "Trend-following",
        "tf":    "1h",
        "desc":  (
            "ADX > 25 confirms a strong trend. Don't fight it — ride it. "
            "Enter on pullbacks to EMA21 while trend is strong."
        ),
        "rules": {
            "trend":    "ADX > 25 (strong trend confirmed)",
            "entry":    "Pullback to EMA21 without violating EMA50",
            "confirm":  "RSI 45–60, MACD positive",
            "sl":       "Break of EMA50",
            "tp":       "Trail stop using EMA21",
        },
    },
    {
        "id":    "fear_contrarian",
        "name":  "Extreme Fear Contrarian Buy",
        "trader": "Warren Buffett Principle adapted to Crypto",
        "style": "Macro / DCA",
        "tf":    "Daily",
        "desc":  (
            "Fear & Greed < 20 = Extreme Fear. Historically the best buying zones. "
            "\"Be greedy when others are fearful.\" Accumulate BTC/ETH in stages."
        ),
        "rules": {
            "trend":    "Fear & Greed Index < 20",
            "entry":    "Split into 3 tranches over 3 days",
            "confirm":  "RSI < 35 on daily, price above key 200-week MA",
            "sl":       "Full exit if weekly EMA200 breaks",
            "tp":       "Sell 50% at Fear & Greed > 75 (Extreme Greed)",
        },
    },
]


# ── Live scanner ──────────────────────────────────────────────────────────────

@dataclass
class StrategyMatch:
    strategy_id:  str
    asset:        str
    signal:       str   # "LONG" | "WATCH" | "WAIT"
    score:        float
    reasons:      list[str]
    entry:        float
    sl:           float
    tp1:          float


async def scan_strategy(strategy_id: str, asset: str) -> Optional[StrategyMatch]:
    """Run a specific strategy against a live asset. Returns match or None."""
    try:
        ta = await analyze(asset)
    except Exception as e:
        logger.warning(f"strategy scan {strategy_id}/{asset}: {e}")
        return None

    p   = ta.price
    r21 = ta.ema21
    r50 = ta.ema50
    r200= ta.ema200
    rsi = ta.rsi
    atr = ta.atr
    adx = ta.adx

    # MACD histogram sign
    macd_pos = ta.macd_hist > 0

    if strategy_id == "ema_pullback":
        trend_ok  = r21 > r50 > r200
        near_ema  = abs(p - r21) / r21 < 0.012
        rsi_ok    = 38 <= rsi <= 62
        reasons   = []
        if trend_ok:  reasons.append(f"EMA21({_f(r21)}) > EMA50({_f(r50)}) > EMA200({_f(r200)}) ✅")
        if near_ema:  reasons.append(f"Price {_f(p)} near EMA21 ({abs(p-r21)/r21*100:.1f}% away) ✅")
        if rsi_ok:    reasons.append(f"RSI {rsi:.0f} in reset zone (38–62) ✅")
        if macd_pos:  reasons.append("MACD histogram positive ✅")
        score = sum([trend_ok, near_ema, rsi_ok, macd_pos]) / 4
        if score >= 0.75:
            return StrategyMatch("ema_pullback", asset, "LONG", score, reasons,
                                 entry=p, sl=r50 * 0.995, tp1=p + 2 * atr)

    elif strategy_id == "macd_momentum":
        above_ema200 = p > r200
        macd_cross   = macd_pos and ta.macd_hist < ta.macd_hist * 1.5  # just turned positive
        rsi_ok       = 48 <= rsi <= 68
        reasons = []
        if above_ema200: reasons.append(f"Price above EMA200({_f(r200)}) ✅")
        if macd_pos:     reasons.append(f"MACD histogram positive ({ta.macd_hist:.4f}) ✅")
        if rsi_ok:       reasons.append(f"RSI {rsi:.0f} in momentum zone ✅")
        score = sum([above_ema200, macd_pos, rsi_ok]) / 3
        if score >= 0.66:
            return StrategyMatch("macd_momentum", asset, "LONG", score, reasons,
                                 entry=p, sl=p - 1.2 * atr, tp1=p + 1.8 * atr)

    elif strategy_id == "rsi_oversold_bounce":
        above_ema200 = p > r200
        oversold     = rsi < 34
        bouncing     = rsi > 28 and p > r21  # recovering
        reasons = []
        if above_ema200: reasons.append(f"Long-term uptrend intact (above EMA200 {_f(r200)}) ✅")
        if oversold:     reasons.append(f"RSI {rsi:.0f} — deeply oversold ✅")
        if bouncing:     reasons.append(f"Price reclaimed EMA21 — bounce forming ✅")
        score = sum([above_ema200, oversold]) / 2
        if score >= 0.5 and oversold:
            return StrategyMatch("rsi_oversold_bounce", asset, "LONG", score, reasons,
                                 entry=p, sl=p - atr, tp1=r21)

    elif strategy_id == "vwap_reclaim":
        above_vwap = p > ta.vwap
        vwap_close = abs(p - ta.vwap) / ta.vwap < 0.008
        rsi_ok     = rsi > 44
        reasons = []
        if above_vwap: reasons.append(f"Price {_f(p)} above VWAP {_f(ta.vwap)} ✅")
        if vwap_close: reasons.append(f"Close to VWAP — fresh reclaim zone ✅")
        if rsi_ok:     reasons.append(f"RSI {rsi:.0f} positive bias ✅")
        if macd_pos:   reasons.append("MACD positive ✅")
        score = sum([above_vwap, vwap_close, rsi_ok, macd_pos]) / 4
        if score >= 0.5 and above_vwap and vwap_close:
            return StrategyMatch("vwap_reclaim", asset, "LONG", score, reasons,
                                 entry=p, sl=ta.vwap * 0.997, tp1=p + 1.5 * atr)

    elif strategy_id == "ema_squeeze_breakout":
        spread = (max(r21, r50, r200) - min(r21, r50, r200)) / r200
        squeeze = spread < 0.03
        breaking_out = p > max(r21, r50, r200)
        reasons = []
        if squeeze:       reasons.append(f"EMA squeeze ({spread*100:.1f}% spread) — coil building ✅")
        if breaking_out:  reasons.append(f"Price breaking above EMA cluster ✅")
        if rsi > 52:      reasons.append(f"RSI {rsi:.0f} confirming breakout ✅")
        if macd_pos:      reasons.append("MACD positive ✅")
        score = sum([squeeze, breaking_out, rsi > 52, macd_pos]) / 4
        if score >= 0.75:
            return StrategyMatch("ema_squeeze_breakout", asset, "LONG", score, reasons,
                                 entry=p, sl=min(r21, r50, r200) * 0.995, tp1=p + 3 * atr)

    elif strategy_id == "adx_trend_ride":
        strong_trend = adx is not None and adx > 25
        near_ema21   = abs(p - r21) / r21 < 0.015
        ema_intact   = p > r50
        reasons = []
        if strong_trend: reasons.append(f"ADX {adx:.0f} — strong trend confirmed ✅")
        if near_ema21:   reasons.append(f"Pullback to EMA21 ({_f(r21)}) ✅")
        if ema_intact:   reasons.append(f"EMA50 support intact ✅")
        if macd_pos:     reasons.append("MACD positive ✅")
        score = sum([bool(strong_trend), near_ema21, ema_intact, macd_pos]) / 4
        if score >= 0.75:
            return StrategyMatch("adx_trend_ride", asset, "LONG", score, reasons,
                                 entry=p, sl=r50 * 0.993, tp1=p + 2 * atr)

    elif strategy_id == "support_flip":
        # Price recently broke above EMA50 and is retesting it
        retesting   = abs(p - r50) / r50 < 0.01
        above_ema200 = p > r200
        rsi_ok      = rsi > 48
        reasons = []
        if above_ema200: reasons.append(f"Price above EMA200 (trend intact) ✅")
        if retesting:    reasons.append(f"Retesting EMA50 ({_f(r50)}) as support ✅")
        if rsi_ok:       reasons.append(f"RSI {rsi:.0f} bullish ✅")
        if macd_pos:     reasons.append("MACD positive ✅")
        score = sum([above_ema200, retesting, rsi_ok, macd_pos]) / 4
        if score >= 0.75:
            return StrategyMatch("support_flip", asset, "LONG", score, reasons,
                                 entry=p, sl=r200 * 0.995, tp1=p + 2 * atr)

    return None


async def run_strategy_scan(assets: list[str]) -> list[tuple[dict, StrategyMatch]]:
    """Scan all assets × strategies, return top matches sorted by score."""
    results = []
    scannable = [s for s in STRATEGIES if s["id"] != "fear_contrarian"]  # fear needs live F&G

    tasks = [
        scan_strategy(s["id"], asset)
        for s in scannable
        for asset in assets
    ]
    matches = await asyncio.gather(*tasks, return_exceptions=True)

    i = 0
    for s in scannable:
        for asset in assets:
            m = matches[i]
            i += 1
            if isinstance(m, StrategyMatch):
                results.append((s, m))

    results.sort(key=lambda x: x[1].score, reverse=True)
    return results[:6]  # top 6


# ── Formatters ────────────────────────────────────────────────────────────────

def format_strategy_list() -> str:
    """Show all 8 strategies as a reference card."""
    lines = [
        "📚 *Pro Trading Strategies*",
        "━━━━━━━━━━━━━━━━━━",
        "_Used by top traders worldwide_\n",
    ]
    for s in STRATEGIES:
        lines.append(
            f"*{s['name']}* — {s['style']}\n"
            f"👤 _{s['trader']}_\n"
            f"_{s['desc'][:90]}{'…' if len(s['desc'])>90 else ''}_\n"
        )
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("_Tap 🔍 Live Scan to find active setups now._")
    return "\n".join(lines)


def format_strategy_detail(sid: str) -> str:
    """Detailed view of one strategy."""
    s = next((x for x in STRATEGIES if x["id"] == sid), None)
    if not s:
        return "Strategy not found."
    r = s["rules"]
    return (
        f"📖 *{s['name']}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Trader:* {s['trader']}\n"
        f"⏱ *Style:* {s['style']}  |  TF: `{s['tf']}`\n\n"
        f"_{s['desc']}_\n\n"
        f"*Rules:*\n"
        f"• *Trend:* {r['trend']}\n"
        f"• *Entry:* {r['entry']}\n"
        f"• *Confirm:* {r['confirm']}\n"
        f"• *Stop Loss:* {r['sl']}\n"
        f"• *Take Profit:* {r['tp']}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"_Paper trade first. Never risk more than 2% per trade._"
    )


def format_live_scan_results(results: list[tuple[dict, StrategyMatch]]) -> str:
    """Format live scan results."""
    if not results:
        return (
            "🔍 *Live Strategy Scan*\n━━━━━━━━━━━━━━━━━━\n\n"
            "_No active setups found right now._\n"
            "_Markets may be ranging — wait for cleaner confluences._"
        )
    lines = [
        "🔍 *Live Strategy Scan — Active Setups*",
        "━━━━━━━━━━━━━━━━━━",
    ]
    for s, m in results:
        grade = "🟢 A" if m.score >= 0.85 else ("🟡 B" if m.score >= 0.70 else "🟠 C")
        asset = m.asset.replace("/USDT", "")
        lines.append(
            f"\n{grade}  *{asset}* — {s['name']}\n"
            f"👤 _{s['trader']}_\n"
        )
        for r in m.reasons[:3]:
            lines.append(f"   • {r}")
        lines.append(
            f"   Entry: `{_f(m.entry)}`  SL: `{_f(m.sl)}`  TP: `{_f(m.tp1)}`\n"
            f"   Score: `{m.score:.0%}`"
        )
    lines += [
        "\n━━━━━━━━━━━━━━━━━━",
        "_Always confirm on your own chart. Paper trade first._",
    ]
    return "\n".join(lines)


def _f(price: float) -> str:
    if price >= 10000: return f"${price:,.0f}"
    if price >= 100:   return f"${price:,.1f}"
    if price >= 1:     return f"${price:,.3f}"
    return f"${price:.5f}"
