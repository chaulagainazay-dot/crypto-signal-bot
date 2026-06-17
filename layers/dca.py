"""DCA planner — set recurring buy reminders (daily/weekly/monthly)."""
from datetime import datetime, timezone, timedelta
from utils.db import add_dca_plan, get_dca_plans, delete_dca_plan, get_due_dca_plans, update_dca_next
from utils.fmt import fp, mill, header, SEP, footer

FREQUENCIES = {
    "daily":   timedelta(days=1),
    "weekly":  timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


def _next_trigger(frequency: str) -> str:
    delta = FREQUENCIES.get(frequency, timedelta(days=1))
    return (datetime.now(timezone.utc) + delta).isoformat()


def parse_dca_command(text: str) -> dict:
    """Parse '/dca BTC 100 weekly'"""
    parts = text.strip().split()
    if len(parts) < 4:
        return None
    _, symbol, amount_str, frequency = parts[0], parts[1], parts[2], parts[3].lower()
    if frequency not in FREQUENCIES:
        return None
    try:
        amount = float(amount_str.replace(",", "").replace("$", ""))
    except ValueError:
        return None
    return {"symbol": symbol.upper(), "amount_usd": amount, "frequency": frequency}


async def create_dca(chat_id: str, symbol: str, amount_usd: float, frequency: str) -> int:
    next_t = _next_trigger(frequency)
    return await add_dca_plan(chat_id, symbol, amount_usd, frequency, next_t)


async def format_dca_plans(chat_id: str) -> str:
    plans = await get_dca_plans(chat_id)
    if not plans:
        return (
            f"{header('📅', 'DCA Planner')}\n\n"
            "_No active DCA plans._\n\n"
            "Create one:\n"
            "`/dca BTC 100 weekly`\n"
            "`/dca ETH 50 daily`\n"
            "`/dca SOL 200 monthly`\n\n"
            f"{footer()}"
        )
    lines = [header("📅", "Active DCA Plans"), ""]
    for p in plans:
        freq_icon = {"daily": "📆", "weekly": "🗓", "monthly": "🗃"}.get(p["frequency"], "📅")
        next_dt = datetime.fromisoformat(p["next_trigger_utc"])
        days_left = max(0, (next_dt - datetime.now(timezone.utc)).days)
        lines.append(
            f"{freq_icon} *{p['symbol']}* — `${p['amount_usd']:.0f}` / {p['frequency']}"
        )
        lines.append(f"  Next: `{next_dt.strftime('%b %d')}` ({days_left}d)  Runs: `{p['executions']}`  `#{p['id']}`")
        lines.append("")
    lines.append("_Cancel: `/canceldca <id>`_")
    lines.append(f"\n{footer()}")
    return "\n".join(lines)


async def check_due_dca(bot=None) -> list:
    """Called by scheduler. Sends reminders for due DCA plans."""
    due = await get_due_dca_plans()
    notified = []
    for plan in due:
        next_t = _next_trigger(plan["frequency"])
        await update_dca_next(plan["id"], next_t)
        notified.append(plan)
        if bot:
            await _send_dca_reminder(bot, plan)
    return notified


async def _send_dca_reminder(bot, plan: dict):
    freq_icon = {"daily": "📆", "weekly": "🗓", "monthly": "🗃"}.get(plan["frequency"], "📅")
    text = (
        f"{freq_icon} *DCA Reminder*\n\n"
        f"Time to buy *{plan['symbol']}*!\n\n"
        f"Target: `${plan['amount_usd']:.0f} USDT`\n"
        f"Frequency: `{plan['frequency'].capitalize()}`\n\n"
        f"_This is a reminder only — execute manually on your exchange._"
    )
    try:
        await bot.send_message(chat_id=plan["chat_id"], text=text, parse_mode="Markdown")
    except Exception:
        pass
