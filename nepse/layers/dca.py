"""DCA (Dollar-Cost Averaging) planner for NEPSE stocks."""
from datetime import datetime, timezone, timedelta
from utils.fmt import esc, fp, SEP

FREQUENCIES = {
    "daily":   timedelta(days=1),
    "weekly":  timedelta(days=7),
    "monthly": timedelta(days=30),
}


def parse_dca_command(text: str) -> dict:
    """Parse /dca NABIL 5000 weekly"""
    parts = text.strip().split()
    if len(parts) < 4:
        return None
    try:
        symbol    = parts[1].upper()
        amount    = float(parts[2].replace(",", ""))
        frequency = parts[3].lower()
        if frequency not in FREQUENCIES:
            return None
        next_t = (datetime.now(timezone.utc) + FREQUENCIES[frequency]).isoformat()
        return {"symbol": symbol, "amount_npr": amount, "frequency": frequency, "next_trigger_utc": next_t}
    except (ValueError, IndexError):
        return None


def format_dca_plans(plans: list) -> str:
    if not plans:
        return (
            "📆 <b>My DCA Plans</b>\n"
            f"{SEP}\n\n"
            "No active DCA plans.\n\n"
            "<b>Create a plan:</b>\n"
            "<code>/dca NABIL 5000 weekly</code>\n"
            "<code>/dca NICA 10000 monthly</code>\n\n"
            "<i>Format: /dca SYMBOL AMOUNT_NPR FREQUENCY</i>\n"
            "<i>Frequencies: daily · weekly · monthly</i>"
        )
    lines = ["📆 <b>My DCA Plans</b>", SEP, ""]
    for p in plans:
        next_dt = p["next_trigger_utc"][:10]
        lines.append(
            f"<code>#{p['id']}</code>  <b>{esc(p['symbol'])}</b>\n"
            f"  Amount     <code>रु {fp(p['amount_npr'])}</code>  per <b>{p['frequency']}</b>\n"
            f"  Next       <code>{next_dt}</code>\n"
            f"  Executions <code>{p['executions']}</code>"
        )
    lines += ["", f"<i>Cancel: /canceldca &lt;id&gt;</i>"]
    return "\n".join(lines)


async def check_due_dca(bot):
    """Fire DCA reminders for due plans."""
    from utils.db import get_due_dca_plans, update_dca_next
    import logging
    log = logging.getLogger(__name__)

    plans = await get_due_dca_plans()
    for plan in plans:
        freq  = plan["frequency"]
        delta = FREQUENCIES.get(freq, timedelta(days=7))
        next_t = (datetime.now(timezone.utc) + delta).isoformat()
        await update_dca_next(plan["id"], next_t)

        msg = (
            f"📆 <b>DCA Reminder</b>\n"
            f"Time to invest <code>रु {fp(plan['amount_npr'])}</code> in <b>{esc(plan['symbol'])}</b>\n"
            f"Frequency: <i>{plan['frequency']}</i>  ·  Plan <code>#{plan['id']}</code>\n\n"
            f"<i>Use /stock {esc(plan['symbol'])} to check current price before investing.</i>"
        )
        try:
            await bot.send_message(chat_id=plan["user_id"], text=msg, parse_mode="HTML")
        except Exception as e:
            log.warning("DCA send error: %s", e)
