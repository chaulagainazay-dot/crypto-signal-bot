"""
NEPSE Signal Bot — Telegram bot for Nepal Stock Exchange.
Bot: @nepse_signal_bot (or whatever username you set)
"""
import asyncio
import logging
import sys
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

sys.path.insert(0, os.path.dirname(__file__))
from config import BOT_TOKEN, CHAT_ID
from utils.db import init_db

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _uid(update: Update) -> str:
    return str(update.effective_user.id)

def _is_group(update: Update) -> bool:
    return update.effective_chat.type in ("group", "supergroup", "channel")

def _esc(t) -> str:
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

async def _edit(query, text: str, kb=None):
    await query.edit_message_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(kb) if kb else None,
    )

async def _reply_html(update: Update, text: str, kb=None):
    await update.message.reply_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(kb) if kb else None,
    )

async def _redirect_dm(update: Update, ctx: ContextTypes.DEFAULT_TYPE, feature: str):
    """Send a DM to the user from a group, redirecting private features."""
    bot_me = await ctx.bot.get_me()
    link = f"https://t.me/{bot_me.username}"
    try:
        await ctx.bot.send_message(
            chat_id=_uid(update),
            text=(
                f"🔒 <b>{_esc(feature)}</b> is private.\n"
                f"Open here: {link}"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ── Private-only actions (route to DM in groups) ──────────────────────────────

_PRIVATE_ACTIONS = {
    "portfolio", "portfolio_analyse", "portfolio_list",
    "portfolio_add_help", "portfolio_remove_help", "portfolio_clear_confirm",
    "alerts", "alerts_help", "dca", "dca_help",
}


# ── Main keyboard ─────────────────────────────────────────────────────────────

def _main_keyboard() -> list:
    return [
        [InlineKeyboardButton("🏛️ Market Overview", callback_data="market")],
        [
            InlineKeyboardButton("🚀 Top Gainers",  callback_data="gainers"),
            InlineKeyboardButton("📉 Top Losers",   callback_data="losers"),
        ],
        [InlineKeyboardButton("🗂️ Sector Analysis", callback_data="sectors")],
        [InlineKeyboardButton("📅 IPO / FPO Calendar", callback_data="ipo")],
        [
            InlineKeyboardButton("📊 My Portfolio",  callback_data="portfolio"),
            InlineKeyboardButton("👁️ Watchlist",     callback_data="watchlist"),
        ],
        [
            InlineKeyboardButton("🔔 My Alerts",   callback_data="alerts"),
            InlineKeyboardButton("📆 DCA Planner", callback_data="dca"),
        ],
        [InlineKeyboardButton("📋 Weekly Report",  callback_data="weekly")],
        [InlineKeyboardButton("❓ Help",            callback_data="help")],
    ]


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🏛️ <b>NEPSE Signal Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Your Nepal Stock Exchange companion.\n\n"
        "• Real-time market data from merolagani.com\n"
        "• Stock deep dive with TA signals\n"
        "• Portfolio tracker (private per user)\n"
        "• Price alerts · DCA reminders · IPO calendar\n\n"
        "<i>Market hours: Sun–Thu  11:00 AM – 3:00 PM NPT</i>"
    )
    await _reply_html(update, text, _main_keyboard())


# ── /help ─────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "❓ <b>NEPSE Bot — Help</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Market Commands</b>\n"
        "/market — full market overview\n"
        "/gainers — top 15 gainers today\n"
        "/losers  — top 15 losers today\n"
        "/stock NABIL — deep dive on any stock\n\n"
        "<b>Portfolio (private)</b>\n"
        "/addstock NABIL 10 1200 — add holding\n"
        "/removestock &lt;id&gt; — remove holding\n"
        "/clearportfolio — clear all holdings\n\n"
        "<b>Alerts</b>\n"
        "/alert NABIL above 1500\n"
        "/alert NICA below 700\n"
        "/delalert &lt;id&gt; — remove alert\n\n"
        "<b>DCA Planner</b>\n"
        "/dca NABIL 5000 weekly\n"
        "/canceldca &lt;id&gt; — cancel plan\n\n"
        "<b>Watchlist</b>\n"
        "/watch SYMBOL — add to watchlist\n"
        "/unwatch SYMBOL — remove from watchlist\n\n"
        "<b>Other</b>\n"
        "/ipo — IPO/FPO calendar\n"
        "/weekly — weekly report\n"
        "/start — main menu"
    )
    await _reply_html(update, text)


# ── Button handler ────────────────────────────────────────────────────────────

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action  = query.data
    user_id = str(query.from_user.id)
    chat_id = str(query.message.chat.id)

    # Private actions in group → DM user
    if action in _PRIVATE_ACTIONS and chat_id != user_id:
        await ctx.bot.send_message(
            chat_id=user_id,
            text=f"🔒 This feature is private. Open in our direct chat: /start",
            parse_mode=ParseMode.HTML,
        )
        await query.answer("Sent to your private chat.")
        return

    if action == "market":
        from layers.market_summary import build_market_overview
        text = await build_market_overview()
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "gainers":
        from layers.market_summary import build_gainers_losers
        text = await build_gainers_losers("gainers")
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "losers":
        from layers.market_summary import build_gainers_losers
        text = await build_gainers_losers("losers")
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "sectors":
        from layers.market_summary import build_market_overview
        text = await build_market_overview()
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "ipo":
        from layers.ipo_calendar import build_ipo_calendar
        text = await build_ipo_calendar()
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "portfolio":
        from layers.portfolio import build_portfolio_analysis
        text = await build_portfolio_analysis(user_id)
        kb = [
            [
                InlineKeyboardButton("📋 Holdings List",  callback_data="portfolio_list"),
                InlineKeyboardButton("➕ Add Help",       callback_data="portfolio_add_help"),
            ],
            [
                InlineKeyboardButton("🗑️ Clear All",     callback_data="portfolio_clear_confirm"),
                InlineKeyboardButton("🔙 Back",           callback_data="back_main"),
            ],
        ]
        await _edit(query, text, kb)

    elif action == "portfolio_list":
        from utils.db import get_holdings
        from layers.portfolio import format_holdings_list
        holdings = await get_holdings(user_id)
        text = format_holdings_list(holdings)
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="portfolio")]])

    elif action == "portfolio_add_help":
        text = (
            "➕ <b>Add a Stock</b>\n\n"
            "<code>/addstock NABIL 10 1200</code>\n"
            "<code>/addstock NICA 25 800</code>\n"
            "<code>/addstock NLIC 5 3500 long-term</code>\n\n"
            "<i>Format: /addstock SYMBOL SHARES BUY_PRICE_NPR [note]</i>"
        )
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="portfolio")]])

    elif action == "portfolio_clear_confirm":
        await _edit(
            query,
            "⚠️ <b>Clear Portfolio?</b>\n\nThis will delete ALL holdings. Are you sure?",
            [
                [
                    InlineKeyboardButton("✅ Yes, Clear", callback_data="portfolio_clear_yes"),
                    InlineKeyboardButton("❌ Cancel",     callback_data="portfolio"),
                ]
            ],
        )

    elif action == "portfolio_clear_yes":
        from utils.db import clear_portfolio
        await clear_portfolio(user_id)
        await _edit(query, "✅ Portfolio cleared.", [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "watchlist":
        from layers.watchlist import build_watchlist_view
        text = await build_watchlist_view(user_id)
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "alerts":
        from utils.db import get_active_alerts
        from layers.alerts import format_alerts_list
        alerts = await get_active_alerts(user_id)
        text = format_alerts_list(alerts)
        kb = [
            [InlineKeyboardButton("ℹ️ How to set alert", callback_data="alerts_help")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
        ]
        await _edit(query, text, kb)

    elif action == "alerts_help":
        text = (
            "🔔 <b>Set a Price Alert</b>\n\n"
            "<code>/alert NABIL above 1500</code>\n"
            "<code>/alert NICA below 700</code>\n\n"
            "<i>Format: /alert SYMBOL above|below PRICE</i>\n"
            "<i>Remove: /delalert &lt;id&gt;</i>"
        )
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="alerts")]])

    elif action == "dca":
        from utils.db import get_dca_plans
        from layers.dca import format_dca_plans
        plans = await get_dca_plans(user_id)
        text = format_dca_plans(plans)
        kb = [
            [InlineKeyboardButton("ℹ️ How to create plan", callback_data="dca_help")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
        ]
        await _edit(query, text, kb)

    elif action == "dca_help":
        text = (
            "📆 <b>Create a DCA Plan</b>\n\n"
            "<code>/dca NABIL 5000 weekly</code>\n"
            "<code>/dca NICA 10000 monthly</code>\n"
            "<code>/dca KBL 2000 daily</code>\n\n"
            "<i>Format: /dca SYMBOL AMOUNT_NPR FREQUENCY</i>\n"
            "<i>Frequencies: daily · weekly · monthly</i>\n"
            "<i>Cancel: /canceldca &lt;id&gt;</i>"
        )
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="dca")]])

    elif action == "weekly":
        from layers.weekly_report import build_weekly_report
        text = await build_weekly_report()
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "help":
        text = (
            "❓ <b>NEPSE Bot — Help</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "/market — full market overview\n"
            "/gainers · /losers — movers\n"
            "/stock NABIL — stock deep dive\n"
            "/addstock SYMBOL SHARES PRICE\n"
            "/alert SYMBOL above|below PRICE\n"
            "/dca SYMBOL AMOUNT FREQ\n"
            "/watch SYMBOL — watchlist\n"
            "/ipo — IPO calendar\n"
            "/weekly — weekly report"
        )
        await _edit(query, text, [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]])

    elif action == "back_main":
        text = (
            "🏛️ <b>NEPSE Signal Bot</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Choose an option below:"
        )
        await _edit(query, text, _main_keyboard())


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_market(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from layers.market_summary import build_market_overview
    text = await build_market_overview()
    await _reply_html(update, text)

async def cmd_gainers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from layers.market_summary import build_gainers_losers
    text = await build_gainers_losers("gainers")
    await _reply_html(update, text)

async def cmd_losers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from layers.market_summary import build_gainers_losers
    text = await build_gainers_losers("losers")
    await _reply_html(update, text)

async def cmd_stock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await _reply_html(update, "Usage: <code>/stock NABIL</code>")
        return
    from layers.stock_lookup import build_stock_deep_dive
    text = await build_stock_deep_dive(args[0])
    await _reply_html(update, text)

async def cmd_ipo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from layers.ipo_calendar import build_ipo_calendar
    text = await build_ipo_calendar()
    await _reply_html(update, text)

async def cmd_weekly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from layers.weekly_report import build_weekly_report
    text = await build_weekly_report()
    await _reply_html(update, text)

# ── Portfolio commands ────────────────────────────────────────────────────────

async def cmd_addstock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "Portfolio")
        return
    user_id = _uid(update)
    from layers.portfolio import parse_addstock
    parsed = parse_addstock(update.message.text or "")
    if not parsed:
        await _reply_html(update,
            "Usage: <code>/addstock NABIL 10 1200</code>\n"
            "<i>Format: /addstock SYMBOL SHARES BUY_PRICE [note]</i>"
        )
        return
    from utils.db import add_holding
    hid = await add_holding(user_id, parsed["symbol"], parsed["shares"], parsed["buy_price"], parsed.get("note",""))
    await _reply_html(update,
        f"✅ Added <b>{_esc(parsed['symbol'])}</b> — "
        f"<code>{parsed['shares']:,g}</code> shares @ <code>रु {parsed['buy_price']:,.2f}</code>  "
        f"(ID <code>#{hid}</code>)\n\n"
        f"<i>Use /portfolio to view your holdings.</i>"
    )

async def cmd_removestock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "Portfolio")
        return
    user_id = _uid(update)
    if not ctx.args:
        await _reply_html(update, "Usage: <code>/removestock &lt;id&gt;</code>")
        return
    try:
        hid = int(ctx.args[0].lstrip("#"))
    except ValueError:
        await _reply_html(update, "Invalid ID. Usage: <code>/removestock 3</code>")
        return
    from utils.db import remove_holding
    await remove_holding(hid, user_id)
    await _reply_html(update, f"🗑️ Holding <code>#{hid}</code> removed.")

async def cmd_clearportfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "Portfolio")
        return
    user_id = _uid(update)
    from utils.db import clear_portfolio
    await clear_portfolio(user_id)
    await _reply_html(update, "🗑️ Portfolio cleared.")

async def cmd_portfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "Portfolio")
        return
    user_id = _uid(update)
    from layers.portfolio import build_portfolio_analysis
    text = await build_portfolio_analysis(user_id)
    await _reply_html(update, text)

# ── Alert commands ────────────────────────────────────────────────────────────

async def cmd_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "Price Alerts")
        return
    user_id = _uid(update)
    from layers.alerts import parse_alert_command
    parsed = parse_alert_command(update.message.text or "")
    if not parsed:
        await _reply_html(update,
            "Usage: <code>/alert NABIL above 1500</code>\n"
            "<i>Conditions: above · below</i>"
        )
        return
    from utils.db import add_alert
    aid = await add_alert(user_id, parsed["symbol"], parsed["condition"], parsed["target_price"])
    cond = "▲ above" if parsed["condition"] == "above" else "▼ below"
    await _reply_html(update,
        f"🔔 Alert set!  <b>{_esc(parsed['symbol'])}</b>  {cond}  "
        f"<code>रु {parsed['target_price']:,.2f}</code>  (ID <code>#{aid}</code>)\n\n"
        f"<i>View alerts: /alerts · Remove: /delalert {aid}</i>"
    )

async def cmd_delalert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "Alerts")
        return
    if not ctx.args:
        await _reply_html(update, "Usage: <code>/delalert &lt;id&gt;</code>")
        return
    try:
        aid = int(ctx.args[0].lstrip("#"))
    except ValueError:
        await _reply_html(update, "Invalid ID.")
        return
    from utils.db import delete_alert
    await delete_alert(aid)
    await _reply_html(update, f"🗑️ Alert <code>#{aid}</code> removed.")

async def cmd_alerts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "Alerts")
        return
    user_id = _uid(update)
    from utils.db import get_active_alerts
    from layers.alerts import format_alerts_list
    alerts = await get_active_alerts(user_id)
    await _reply_html(update, format_alerts_list(alerts))

# ── DCA commands ──────────────────────────────────────────────────────────────

async def cmd_dca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "DCA Planner")
        return
    user_id = _uid(update)
    from layers.dca import parse_dca_command
    parsed = parse_dca_command(update.message.text or "")
    if not parsed:
        await _reply_html(update,
            "Usage: <code>/dca NABIL 5000 weekly</code>\n"
            "<i>Frequencies: daily · weekly · monthly</i>"
        )
        return
    from utils.db import add_dca_plan
    pid = await add_dca_plan(user_id, parsed["symbol"], parsed["amount_npr"], parsed["frequency"], parsed["next_trigger_utc"])
    await _reply_html(update,
        f"📆 DCA plan created!  <b>{_esc(parsed['symbol'])}</b>  "
        f"<code>रु {parsed['amount_npr']:,.0f}</code>  per <b>{parsed['frequency']}</b>  "
        f"(ID <code>#{pid}</code>)\n\n"
        f"<i>Cancel: /canceldca {pid}</i>"
    )

async def cmd_canceldca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_dm(update, ctx, "DCA Planner")
        return
    if not ctx.args:
        await _reply_html(update, "Usage: <code>/canceldca &lt;id&gt;</code>")
        return
    try:
        pid = int(ctx.args[0].lstrip("#"))
    except ValueError:
        await _reply_html(update, "Invalid ID.")
        return
    from utils.db import delete_dca_plan
    await delete_dca_plan(pid)
    await _reply_html(update, f"🗑️ DCA plan <code>#{pid}</code> cancelled.")

# ── Watchlist commands ────────────────────────────────────────────────────────

async def cmd_watch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = _uid(update)
    if not ctx.args:
        await _reply_html(update, "Usage: <code>/watch NABIL</code>")
        return
    sym = ctx.args[0].upper()
    from utils.db import add_watchlist
    await add_watchlist(user_id, sym)
    await _reply_html(update, f"👁️ <b>{_esc(sym)}</b> added to watchlist.\n\n<i>View: /watchlist</i>")

async def cmd_unwatch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = _uid(update)
    if not ctx.args:
        await _reply_html(update, "Usage: <code>/unwatch NABIL</code>")
        return
    sym = ctx.args[0].upper()
    from utils.db import remove_watchlist
    await remove_watchlist(user_id, sym)
    await _reply_html(update, f"👁️ <b>{_esc(sym)}</b> removed from watchlist.")

async def cmd_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = _uid(update)
    from layers.watchlist import build_watchlist_view
    text = await build_watchlist_view(user_id)
    await _reply_html(update, text)

# ── Text fallback (e.g. user types stock name) ────────────────────────────────

async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().upper()
    # If it looks like a stock symbol (2-10 uppercase letters) try a lookup
    if text.isalpha() and 2 <= len(text) <= 10:
        from layers.stock_lookup import build_stock_deep_dive
        result = await build_stock_deep_dive(text)
        await _reply_html(update, result)
    # Otherwise ignore


# ── Scheduler jobs ────────────────────────────────────────────────────────────

async def _job_alert_check(bot):
    from utils.db import get_active_alerts
    from layers.alerts import check_alerts
    alerts = await get_active_alerts()
    await check_alerts(bot, alerts)

async def _job_dca_check(bot):
    from layers.dca import check_due_dca
    await check_due_dca(bot)

async def _job_morning_report(bot):
    if not CHAT_ID:
        return
    from layers.market_summary import build_market_overview
    text = await build_market_overview()
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=ParseMode.HTML)
    except Exception as e:
        log.warning("Morning report error: %s", e)

async def _job_weekly(bot):
    if not CHAT_ID:
        return
    from layers.weekly_report import build_weekly_report
    text = await build_weekly_report()
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=ParseMode.HTML)
    except Exception as e:
        log.warning("Weekly report error: %s", e)


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    await init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    bot = app.bot

    # Commands
    app.add_handler(CommandHandler("start",          cmd_start))
    app.add_handler(CommandHandler("help",           cmd_help))
    app.add_handler(CommandHandler("market",         cmd_market))
    app.add_handler(CommandHandler("gainers",        cmd_gainers))
    app.add_handler(CommandHandler("losers",         cmd_losers))
    app.add_handler(CommandHandler("stock",          cmd_stock))
    app.add_handler(CommandHandler("ipo",            cmd_ipo))
    app.add_handler(CommandHandler("weekly",         cmd_weekly))
    app.add_handler(CommandHandler("portfolio",      cmd_portfolio))
    app.add_handler(CommandHandler("addstock",       cmd_addstock))
    app.add_handler(CommandHandler("removestock",    cmd_removestock))
    app.add_handler(CommandHandler("clearportfolio", cmd_clearportfolio))
    app.add_handler(CommandHandler("alert",          cmd_alert))
    app.add_handler(CommandHandler("alerts",         cmd_alerts))
    app.add_handler(CommandHandler("delalert",       cmd_delalert))
    app.add_handler(CommandHandler("dca",            cmd_dca))
    app.add_handler(CommandHandler("canceldca",      cmd_canceldca))
    app.add_handler(CommandHandler("watch",          cmd_watch))
    app.add_handler(CommandHandler("unwatch",        cmd_unwatch))
    app.add_handler(CommandHandler("watchlist",      cmd_watchlist))

    # Buttons
    app.add_handler(CallbackQueryHandler(on_button))

    # Text fallback (stock symbol lookup)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # Scheduler
    scheduler = AsyncIOScheduler()
    # Alert check every 5 min during market hours (runs always for simplicity)
    scheduler.add_job(lambda: asyncio.create_task(_job_alert_check(bot)), "interval", minutes=5, id="alerts")
    # DCA check every hour
    scheduler.add_job(lambda: asyncio.create_task(_job_dca_check(bot)), "interval", hours=1, id="dca")
    # Morning market report at 11:05 AM NPT (05:20 UTC) Sun–Thu
    scheduler.add_job(
        lambda: asyncio.create_task(_job_morning_report(bot)),
        "cron", hour=5, minute=20, day_of_week="sun,mon,tue,wed,thu", id="morning"
    )
    # Weekly report Saturday 10 AM NPT (04:15 UTC)
    scheduler.add_job(
        lambda: asyncio.create_task(_job_weekly(bot)),
        "cron", hour=4, minute=15, day_of_week="sat", id="weekly"
    )
    scheduler.start()

    log.info("NEPSE Signal Bot starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    log.info("Bot is running. Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
