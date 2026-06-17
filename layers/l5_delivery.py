"""
L5 — Delivery
Compact, actionable Telegram message templates.
Design principle: user reads once → immediately knows what, why, and what to do.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode

import config
from utils.db import log_signal, get_recent_signals


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(price: float) -> str:
    if price >= 10000:  return f"${price:,.0f}"
    if price >= 100:    return f"${price:,.1f}"
    if price >= 1:      return f"${price:,.3f}"
    return f"${price:.5f}"

def _pct(v: float) -> str:
    return f"{v:+.2f}%"

def _npt_now() -> str:
    npt = datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)
    return npt.strftime("%I:%M %p NPT")

def _expires_npt(minutes: int = None) -> str:
    m = minutes or config.SIGNAL_EXPIRY_MINUTES
    npt = datetime.now(timezone.utc) + timedelta(hours=5, minutes=45+m)
    return npt.strftime("%I:%M %p NPT")


# ── Signal message (new signal) ───────────────────────────────────────────────

def format_signal(signal: dict) -> str:
    d         = signal["direction"]
    asset     = signal["asset"].replace("/USDT", "")
    arrow     = "▲ LONG" if d == "long" else "▼ SHORT"
    bias_icon = "🟢" if d == "long" else "🔴"
    score     = signal.get("composite_score", 0)
    confidence = "High" if abs(score) >= 0.80 else ("Medium" if abs(score) >= 0.65 else "Low")

    entry_low  = signal["entry_low"]
    entry_high = signal["entry_high"]
    sl         = signal["stop_loss"]
    tp1        = signal["tp1"]
    tp2        = signal["tp2"]

    rsi        = signal.get("rsi", 0)
    regime     = signal.get("regime", "")
    reasoning  = signal.get("reasoning", "")

    # Build compact bullet reasons (max 3 lines)
    if reasoning:
        raw = [l.strip().lstrip("•-").strip() for l in reasoning.split("\n") if l.strip()]
        bullets = "\n".join(f"• {l}" for l in raw[:3] if l)
    else:
        bullets = (
            f"• RSI {rsi:.0f} — {'oversold bounce' if rsi < 40 else 'momentum zone'}\n"
            f"• Price {'above' if d == 'long' else 'below'} EMA200 (trend confirmed)\n"
            f"• MACD histogram {'positive' if d == 'long' else 'negative'}"
        )

    expiry = _expires_npt()

    return (
        f"🚨 *{asset}/USDT · {arrow} · 1H* {bias_icon}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{bullets}\n\n"
        f"*Entry:* {_fmt(entry_low)} – {_fmt(entry_high)}\n"
        f"*Stop:* {_fmt(sl)}\n"
        f"*TP1:* {_fmt(tp1)}  •  *TP2:* {_fmt(tp2)}\n\n"
        f"→ Confirm on 1H close {'above' if d == 'long' else 'below'} {_fmt(entry_high if d == 'long' else entry_low)}\n"
        f"⏱ Expires {expiry}  ·  Score `{score:.2f}`"
    )


def format_signal_invalidated(asset: str, reason: str) -> str:
    return (
        f"⚠️ *Setup Cancelled: {asset.replace('/USDT','')}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{reason}\n\n"
        f"_No trade until a new setup appears._"
    )


def format_tp_update(asset: str, direction: str, tp_hit: int, new_stop: float) -> str:
    arrow = "▲" if direction == "long" else "▼"
    return (
        f"📈 *TP{tp_hit} Hit: {asset.replace('/USDT','')} {arrow}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"• Take partial profit ({50 if tp_hit == 1 else 100}%)\n"
        f"• Move stop → breakeven ({_fmt(new_stop)})\n"
        f"• Let remainder run if trend holds"
    )


# ── Morning news push (6 AM NPT) ──────────────────────────────────────────────

def format_morning_news(
    news_items: list,
    fg: dict,
    btc_change: float,
    eth_change: float,
    regime_label: str,
) -> str:
    from datetime import date
    day = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime("%a %b %d")
    tone_icon = "😱" if fg["value"] <= 25 else ("😟" if fg["value"] <= 45 else ("😐" if fg["value"] <= 55 else "😄"))

    lines = [
        f"🌅 *Morning Brief — {day}*",
        f"━━━━━━━━━━━━━━━━━━",
        f"Market Tone: *{fg['label']}* {tone_icon} `({fg['value']}/100)`",
        f"BTC {_pct(btc_change)}  •  ETH {_pct(eth_change)}",
        f"Regime: *{regime_label}*",
        "",
        "📰 *Top Stories:*",
    ]

    for item in news_items[:6]:
        title = item["title"][:72] + ("…" if len(item["title"]) > 72 else "")
        age   = f"{item['age_min']}m" if item["age_min"] < 60 else f"{item['age_min']//60}h"
        lines.append(f"• {title} _{item['source']} · {age}_")

    lines += [
        "",
        f"_Full analytics at 8:00 AM NPT →_"
    ]
    return "\n".join(lines)


# ── Morning analytics (8 AM NPT) ─────────────────────────────────────────────

def format_morning_analytics(asset_rows: list, top_watch: str, avoid_note: str) -> str:
    """
    asset_rows: list of dicts with asset, price, high_24h, low_24h, change_pct, bias, note
    """
    npt = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime("%I:%M %p NPT")
    lines = [
        f"📊 *Market Analytics — {npt}*",
        f"━━━━━━━━━━━━━━━━━━",
    ]

    for row in asset_rows:
        symbol   = row["asset"].replace("/USDT", "")
        chg_icon = "🟢" if row["change_pct"] >= 0 else "🔴"
        lines.append(
            f"\n*{symbol}/USDT*  {chg_icon} `{_pct(row['change_pct'])}`\n"
            f"24H  H: `{_fmt(row['high_24h'])}`  L: `{_fmt(row['low_24h'])}`\n"
            f"_{row['note']}_\n"
            f"Bias: *{row['bias']}*"
        )

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━",
        f"👁 *Watch:* {top_watch}",
        f"⛔ *Avoid:* {avoid_note}",
        "",
        "_Signals fire automatically when setups confirm._",
    ]
    return "\n".join(lines)


# ── Daily summary ─────────────────────────────────────────────────────────────

def format_daily_summary(tone: str, best: list, watch_notes: str) -> str:
    day = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime("%a %b %d")
    best_str = ", ".join(best) if best else "—"
    return (
        f"🗓 *Daily Brief — {day}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Today's tone: *{tone}*\n"
        f"Best setups: `{best_str}`\n\n"
        f"📌 Plan:\n"
        f"• Wait for confirmation candles\n"
        f"• Prefer liquid pairs (BTC / ETH)\n"
        f"• {watch_notes}\n\n"
        f"_Tap 🔍 Opportunities for live setups._"
    )


# ── Regime alert ──────────────────────────────────────────────────────────────

def format_regime_alert(regime: str, notes: list) -> str:
    icon = "⚠️" if "chaotic" in regime.lower() else "🌍"
    bullet_notes = "\n".join(f"• {n}" for n in notes)
    return (
        f"{icon} *Market Regime Shift*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"New regime: *{regime}*\n\n"
        f"{bullet_notes}\n\n"
        f"_Signal thresholds tightened automatically._"
    )


# ── Delivery helpers ──────────────────────────────────────────────────────────

async def push(bot: Bot, text: str, chat_id: str = None):
    target = chat_id or config.TELEGRAM_CHAT_ID
    if not target:
        return
    await bot.send_message(
        chat_id=target,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


async def deliver_signal(bot: Bot, signal: dict, chat_id: str = None):
    text = format_signal(signal)
    await push(bot, text, chat_id)
    await log_signal(signal)


# ── Recent signals box (for keyboard) ────────────────────────────────────────

def format_recent_signals_box(signals: list) -> str:
    if not signals:
        return (
            "📈 *Recent Signals*\n━━━━━━━━━━━━━━━━━━\n\n"
            "_No signals yet. Run morning scan or tap 📊 Market Scan._"
        )
    lines = ["📈 *Recent Signals*\n━━━━━━━━━━━━━━━━━━"]
    for s in signals[:5]:
        d      = s["direction"]
        arrow  = "▲" if d == "long" else "▼"
        score  = s.get("composite_score", 0)
        status = s.get("outcome", "pending")
        icon   = {"pending": "⏳", "win": "✅", "loss": "❌", "expired": "💨"}.get(status, "⏳")
        asset  = s["asset"].replace("/USDT", "")
        ts     = s["created_at"][:16].replace("T", " ")
        lines.append(f"\n{arrow} *{asset}* {d.upper()}  `{score:.2f}`  {icon}\n   _🕐 {ts} UTC_")
    lines.append("\n━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
