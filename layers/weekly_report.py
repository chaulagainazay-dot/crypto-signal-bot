"""Weekly performance report — HTML with expandable blockquotes (Bot API 9.0+)."""
from utils.db import get_weekly_stats, get_whale_picks_history
from datetime import datetime, timezone, timedelta


def _npt() -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)
    return dt.strftime("%a %b %d, %Y  ·  %I:%M %p NPT")


def _fp(p: float) -> str:
    if not p: return "$0"
    if p >= 10000: return f"${p:,.0f}"
    if p >= 100:   return f"${p:,.2f}"
    if p >= 1:     return f"${p:,.4f}"
    return f"${p:.6f}"


async def build_weekly_report() -> str:
    stats  = await get_weekly_stats()
    whales = await get_whale_picks_history(limit=7)
    return format_weekly_report(stats, whales)


def format_weekly_report(stats: dict, whale_picks: list) -> str:
    total    = stats["total"]
    wins     = stats["wins"]
    losses   = stats["losses"]
    pending  = stats["pending"]
    expired  = stats["expired"]
    win_rate = stats["win_rate"]
    best     = stats["best"]
    worst    = stats["worst"]

    # Win rate grade
    if win_rate >= 70: grade = "🟢 Excellent"
    elif win_rate >= 55: grade = "🟡 Good"
    elif win_rate >= 40: grade = "🟠 Average"
    else: grade = "🔴 Below average"

    # Signal rows
    outcome_icons = {"pending": "⏳", "tp1": "🎯", "tp2": "✅", "sl": "❌", "expired": "💨"}
    signal_rows = ""
    for sig in stats["signals"][:10]:
        icon  = outcome_icons.get(sig["outcome"], "⏳")
        asset = sig["asset"]
        dir_  = sig.get("direction", "?")
        pnl_v = sig.get("pnl_pct") or 0
        pnl_s = f"<code>{pnl_v:+.2f}%</code>" if sig["outcome"] not in ("pending","expired") else "<code>—</code>"
        signal_rows += f"  {icon} <b>{asset}</b> {dir_}  {pnl_s}\n"

    # Commentary
    if total == 0:
        commentary = "No signals this week. Run a scan to get started."
    elif win_rate >= 70:
        commentary = "Excellent week! Strategies working well. Stay disciplined and protect profits."
    elif win_rate >= 50:
        commentary = "Decent performance. Review losses for sizing or entry improvements."
    else:
        commentary = "Tough week. Consider reducing position size until confluence improves."

    # Whale picks block
    whale_rows = ""
    for wp in whale_picks:
        whale_rows += f"  • <b>{wp['symbol']}</b>  {_fp(wp['price_at_pick'] or 0)}  Score <code>{wp['score']:.0f}</code>  <i>{wp['date']}</i>\n"

    lines = [
        f"📊 <b>Weekly Performance Report</b>",
        f"━━━━━━━━━━━━━━━━━━",
        f"<i>{_npt()}</i>",
        "",
        f"<b>Signals</b>  <code>{total}</code>   "
        f"✅ <code>{wins}</code>  ❌ <code>{losses}</code>  ⏳ <code>{pending}</code>  💨 <code>{expired}</code>",
        f"<b>Win Rate</b>  <code>{win_rate:.1f}%</code>  {grade}",
        "",
    ]

    # Best/worst
    if best and best.get("pnl_pct"):
        lines.append(f"🏆 Best   <b>{best['asset']}</b> <code>{best['pnl_pct']:+.2f}%</code>")
    if worst and worst.get("pnl_pct") and worst["pnl_pct"] < 0:
        lines.append(f"💀 Worst  <b>{worst['asset']}</b> <code>{worst['pnl_pct']:+.2f}%</code>")
    if best or worst:
        lines.append("")

    # Signals detail block
    if signal_rows:
        lines.append(
            f"<blockquote expandable>"
            f"<b>All Signals This Week</b>\n"
            f"{signal_rows.rstrip()}"
            f"</blockquote>\n"
        )

    # Whale picks block
    if whale_rows:
        lines.append(
            f"<blockquote expandable>"
            f"<b>🐋 Whale Picks (7 days)</b>\n"
            f"{whale_rows.rstrip()}"
            f"</blockquote>\n"
        )

    lines += [
        f"💬 <i>{commentary}</i>",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "<i>Past performance does not guarantee future results · DYOR</i>",
    ]
    return "\n".join(lines)
