"""
Crypto Signal Agent — @hcglivesignalbot
Scheduled: 6 AM NPT news, 8 AM NPT analytics, 9 AM NPT whale pick,
           10 AM NPT Sunday weekly report.
On-demand: everything else on button tap.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

import config
from layers.l1_data import fetch_latest_news, fetch_fear_greed
from layers.l2_technical import analyze, fetch_ticker, close_exchange, test_all_sources
from layers.l_opportunities import scan_opportunities, format_opportunities
from layers.chart import generate_chart
from layers.strategies import (
    STRATEGIES, format_strategy_list, format_strategy_detail,
    run_strategy_scan, format_live_scan_results,
)
from layers.whale_scanner import run_whale_scan, format_whale_pick
from layers.token_deep_dive import run_token_deep_dive
from layers.portfolio import (
    build_portfolio_analysis, format_holdings_list_html,
    format_empty_portfolio_html, _parse_command as _parse_holding,
)
from layers.funding_oi import fetch_funding_oi, format_funding_oi, format_oi_spikes
from layers.dominance import fetch_dominance, format_dominance
from layers.signal_tracker import check_signals, format_open_signals
from layers.weekly_report import build_weekly_report
from layers.dca import parse_dca_command, create_dca, format_dca_plans, check_due_dca, delete_dca_plan
from utils.alerts import parse_alert_command, check_alerts, format_alerts_list
from utils.db import (
    init_db, get_recent_signals, log_scan, log_whale_pick,
    add_alert, get_active_alerts, delete_alert,
    add_dca_plan, get_dca_plans,
    add_holding, get_holdings, remove_holding, clear_portfolio,
)
from layers.l5_delivery import (
    format_recent_signals_box, format_morning_news,
    format_signal, push,
)
from scanner import run_morning_news, run_morning_analytics, run_manual_scan
from utils.fmt import npt_now, fp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")
_last_action: dict[str, str] = {}


# ── Keyboards ──────────────────────────────────────────────────────────────────

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📰 Morning News",     callback_data="news"),
            InlineKeyboardButton("📊 Market Scan",      callback_data="scan"),
        ],
        [
            InlineKeyboardButton("🔍 Opportunities",    callback_data="opportunities"),
            InlineKeyboardButton("📉 Chart",            callback_data="chart_menu"),
        ],
        [
            InlineKeyboardButton("💲 Prices",           callback_data="prices"),
            InlineKeyboardButton("🌡 Fear & Greed",     callback_data="feargreed"),
        ],
        [
            InlineKeyboardButton("📈 Signals",          callback_data="signals"),
            InlineKeyboardButton("⚙️ Status",           callback_data="status"),
        ],
        [
            InlineKeyboardButton("🎯 Pro Strategies",   callback_data="strategies"),
            InlineKeyboardButton("🐋 Whale Pick",       callback_data="whalepick"),
        ],
        [
            InlineKeyboardButton("📊 Funding & OI",    callback_data="funding_oi"),
            InlineKeyboardButton("🌐 Dominance",        callback_data="dominance"),
        ],
        [
            InlineKeyboardButton("🔔 My Alerts",        callback_data="alerts"),
            InlineKeyboardButton("📅 DCA Planner",      callback_data="dca"),
        ],
        [
            InlineKeyboardButton("💼 My Portfolio",     callback_data="portfolio"),
            InlineKeyboardButton("🔎 Token Lookup",     callback_data="token_lookup"),
        ],
        [
            InlineKeyboardButton("📋 Weekly Report",    callback_data="weekly_report"),
            InlineKeyboardButton("🔌 Test Connection",  callback_data="conntest"),
        ],
    ])


def back_keyboard(refresh_action: str = None) -> InlineKeyboardMarkup:
    rows = []
    if refresh_action:
        rows.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{refresh_action}")])
    rows.append([InlineKeyboardButton("🏠 Menu", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def chart_keyboard() -> InlineKeyboardMarkup:
    buttons, row = [], []
    for asset in config.WATCHLIST:
        sym = asset.split("/")[0]
        row.append(InlineKeyboardButton(f"📉 {sym}", callback_data=f"chart_{asset}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🏠 Menu", callback_data="menu")])
    return InlineKeyboardMarkup(buttons)


def strategies_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🔍 Live Scan — Find Active Setups", callback_data="strategy_scan")],
        [InlineKeyboardButton("📖 Strategy Guide", callback_data="strategy_list")],
    ]
    strat_row = []
    for s in STRATEGIES:
        label = s["name"][:22]
        strat_row.append(InlineKeyboardButton(label, callback_data=f"strategy_{s['id']}"))
        if len(strat_row) == 2:
            rows.append(strat_row); strat_row = []
    if strat_row:
        rows.append(strat_row)
    rows.append([InlineKeyboardButton("🏠 Menu", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def prices_keyboard() -> InlineKeyboardMarkup:
    buttons, row = [], []
    for asset in config.WATCHLIST:
        sym = asset.split("/")[0]
        row.append(InlineKeyboardButton(f"💲 {sym}", callback_data=f"price_{asset}"))
        if len(row) == 3:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🏠 Menu", callback_data="menu")])
    return InlineKeyboardMarkup(buttons)


def funding_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Full Rates",    callback_data="funding_full"),
            InlineKeyboardButton("📈 OI Spikes",     callback_data="oi_spikes"),
        ],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
    ])


def alerts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Set Alert (type /alert)", callback_data="alerts_help")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_alerts")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
    ])


def portfolio_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Analyse Portfolio",  callback_data="portfolio_analyse"),
            InlineKeyboardButton("📋 View Holdings",      callback_data="portfolio_list"),
        ],
        [
            InlineKeyboardButton("➕ Add Holding",         callback_data="portfolio_add_help"),
            InlineKeyboardButton("🗑 Remove Holding",      callback_data="portfolio_remove_help"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh",            callback_data="portfolio_analyse"),
            InlineKeyboardButton("🏠 Menu",               callback_data="menu"),
        ],
    ])


def dca_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ New Plan (type /dca)", callback_data="dca_help")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_dca")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
    ])


# ── Home panel ─────────────────────────────────────────────────────────────────

def home_text() -> str:
    watch = "  ".join(a.split("/")[0] for a in config.WATCHLIST)
    return (
        "🤖 *Crypto Signal Agent*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {npt_now()}\n"
        f"👁 `{watch}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📅 *Scheduled pushes:*\n"
        "  • 6:00 AM NPT — Morning news brief\n"
        "  • 8:00 AM NPT — Analytics + signals\n"
        "  • 9:00 AM NPT — 🐋 Daily whale coin pick\n"
        "  • 10:00 AM NPT (Sun) — 📊 Weekly report\n\n"
        "_Tap a button for live data._"
    )


# ── /start ─────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if not config.TELEGRAM_CHAT_ID:
        os.environ["TELEGRAM_CHAT_ID"] = chat_id
        config.TELEGRAM_CHAT_ID = chat_id
    await update.message.reply_text(
        home_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard()
    )


# ── Privacy helpers ────────────────────────────────────────────────────────────

def _user_id(update: Update) -> str:
    """Always returns the individual Telegram user ID (never the group chat ID)."""
    return str(update.effective_user.id)


def _is_group(update: Update) -> bool:
    return update.effective_chat.type in ("group", "supergroup", "channel")


async def _redirect_to_dm(update: Update, ctx: ContextTypes.DEFAULT_TYPE, feature: str):
    """Tell a group user to use private DM for personal features."""
    bot_info = await ctx.bot.get_me()
    await update.message.reply_text(
        f"🔒 <b>Private feature</b>\n\n"
        f"<b>{feature}</b> is personal data — I'll send it to your private chat only.\n\n"
        f"<a href=\"https://t.me/{bot_info.username}\">👉 Open private chat with me</a> and run the command there.",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── /alert command ─────────────────────────────────────────────────────────────

async def cmd_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /alert BTC above 70000  or  /alert ETH below 2500"""
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Price Alerts 🔔")
        return
    user_id = _user_id(update)
    parsed  = parse_alert_command(update.message.text)
    if not parsed:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n<code>/alert BTC above 70000</code>\n<code>/alert ETH below 2500</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    alert_id = await add_alert(user_id, parsed["symbol"], parsed["condition"], parsed["target_price"])
    cond_icon = "🔼" if parsed["condition"] == "above" else "🔽"
    await update.message.reply_text(
        f"🔔 <b>Alert Set!</b>\n\n"
        f"{cond_icon} <b>{parsed['symbol']}</b> — notify when <code>{parsed['condition']} {fp(parsed['target_price'])}</code>\n"
        f"ID: <code>#{alert_id}</code>\n\n"
        f"<i>Cancel with /delalert {alert_id}</i>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_delalert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /delalert 5"""
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Price Alerts 🔔")
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await update.message.reply_text("Usage: <code>/delalert &lt;id&gt;</code>", parse_mode=ParseMode.HTML)
        return
    await delete_alert(int(parts[1]))
    await update.message.reply_text(f"🗑 Alert <code>#{parts[1]}</code> removed.", parse_mode=ParseMode.HTML)


# ── /dca command ───────────────────────────────────────────────────────────────

async def cmd_dca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /dca BTC 100 weekly"""
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "DCA Planner 📅")
        return
    user_id = _user_id(update)
    parsed  = parse_dca_command(update.message.text)
    if not parsed:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n<code>/dca BTC 100 weekly</code>\n<code>/dca ETH 50 daily</code>\n<code>/dca SOL 200 monthly</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    plan_id = await create_dca(user_id, parsed["symbol"], parsed["amount_usd"], parsed["frequency"])
    freq_icon = {"daily": "📆", "weekly": "🗓", "monthly": "🗃"}.get(parsed["frequency"], "📅")
    await update.message.reply_text(
        f"✅ <b>DCA Plan Created!</b>\n\n"
        f"{freq_icon} <b>{parsed['symbol']}</b> — <code>${parsed['amount_usd']:.0f}</code> every <code>{parsed['frequency']}</code>\n"
        f"Plan ID: <code>#{plan_id}</code>\n\n"
        f"<i>Cancel with /canceldca {plan_id}</i>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_canceldca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /canceldca 3"""
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "DCA Planner 📅")
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await update.message.reply_text("Usage: <code>/canceldca &lt;id&gt;</code>", parse_mode=ParseMode.HTML)
        return
    await delete_dca_plan(int(parts[1]))
    await update.message.reply_text(f"🗑 DCA plan <code>#{parts[1]}</code> cancelled.", parse_mode=ParseMode.HTML)


# ── /watchlist command ─────────────────────────────────────────────────────────

async def cmd_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /token BTC  or  /token solana  or  /token pepe"""
    parts = update.message.text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await update.message.reply_text(
            "🔎 <b>Token Deep Dive</b>\n\n"
            "Usage: <code>/token BTC</code> or <code>/token solana</code> or <code>/token pepe</code>\n\n"
            "I'll fetch full market data, ATH/ATL, TA, risk score and opportunity score.",
            parse_mode=ParseMode.HTML,
        )
        return
    query = parts[1].strip()
    msg = await update.message.reply_text(
        f"🔍 Looking up <b>{query.upper()}</b>…",
        parse_mode=ParseMode.HTML,
    )
    try:
        text, found_name = await run_token_deep_dive(query)
        if not text:
            await msg.edit_text(
                f"❌ <b>Token not found:</b> <code>{query}</code>\n\n"
                "Try the full name (e.g. <code>/token solana</code>) or the symbol (<code>/token SOL</code>).",
                parse_mode=ParseMode.HTML,
            )
            return
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        await msg.edit_text(f"❌ Error: <code>{e}</code>", parse_mode=ParseMode.HTML)


async def cmd_addholding(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /addholding BTC 0.5 45000 [note]"""
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Portfolio 💼")
        return
    user_id = _user_id(update)
    parsed  = _parse_holding(update.message.text)
    if not parsed:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "<code>/addholding BTC 0.5 45000</code>\n"
            "<code>/addholding ETH 2 2800 spot bag</code>\n\n"
            "<i>Format: SYMBOL AMOUNT BUY_PRICE [optional note]</i>",
            parse_mode=ParseMode.HTML,
        )
        return
    holding_id = await add_holding(
        user_id,
        parsed["symbol"],
        parsed["amount"],
        parsed["buy_price"],
        parsed.get("note", ""),
    )
    await update.message.reply_text(
        f"✅ <b>Holding added!</b>\n\n"
        f"<b>{parsed['symbol']}</b>  —  <code>{parsed['amount']:,g}</code> coins\n"
        f"Buy price: <code>${parsed['buy_price']:,}</code>\n"
        f"ID: <code>#{holding_id}</code>\n\n"
        f"<i>Only visible to you — completely private.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💼 View Portfolio", callback_data="portfolio_analyse")
        ]])
    )


async def cmd_removeholding(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /removeholding 5"""
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Portfolio 💼")
        return
    user_id = _user_id(update)
    parts   = update.message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await update.message.reply_text("Usage: <code>/removeholding &lt;id&gt;</code>", parse_mode=ParseMode.HTML)
        return
    holding_id = int(parts[1])
    await remove_holding(holding_id, user_id)
    await update.message.reply_text(
        f"🗑 Holding <code>#{holding_id}</code> removed.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💼 View Portfolio", callback_data="portfolio_analyse")
        ]])
    )


async def cmd_clearportfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Clears all holdings — asks for confirmation."""
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Portfolio 💼")
        return
    await update.message.reply_text(
        "⚠️ <b>Clear all holdings?</b>\n\nThis will delete your entire portfolio. Are you sure?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, clear all", callback_data="portfolio_clear_confirm"),
                InlineKeyboardButton("❌ Cancel",          callback_data="portfolio"),
            ]
        ])
    )


async def cmd_watchlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /watchlist add LINK  or  /watchlist remove LINK  or  /watchlist"""
    parts = update.message.text.strip().split()
    if len(parts) == 1:
        watch = "\n".join(f"  • `{a}`" for a in config.WATCHLIST)
        await update.message.reply_text(
            f"👁 *Current Watchlist*\n\n{watch}\n\n"
            "_Add: `/watchlist add LINK`\nRemove: `/watchlist remove BTC`_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    if len(parts) < 3:
        await update.message.reply_text(
            "Usage: `/watchlist add LINK` or `/watchlist remove BTC`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    action, symbol = parts[1].lower(), parts[2].upper()
    pair = f"{symbol}/USDT"
    if action == "add":
        if pair not in config.WATCHLIST:
            config.WATCHLIST.append(pair)
            await update.message.reply_text(
                f"✅ Added `{pair}` to watchlist.\nWatchlist: `{len(config.WATCHLIST)}` coins",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text(f"`{pair}` is already in watchlist.")
    elif action == "remove":
        if pair in config.WATCHLIST:
            config.WATCHLIST.remove(pair)
            await update.message.reply_text(
                f"🗑 Removed `{pair}` from watchlist.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text(f"`{pair}` not in watchlist.")
    else:
        await update.message.reply_text("Use `add` or `remove`.", parse_mode=ParseMode.MARKDOWN)


# ── Callback router ────────────────────────────────────────────────────────────

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    action  = query.data
    chat_id = str(query.message.chat_id)      # group or DM chat — for editing the message
    user_id = str(query.from_user.id)          # always the individual user — for private data

    if action.startswith("refresh_"):
        action = action[8:]

    _last_action[chat_id] = action

    # Private-only actions: redirect to DM if triggered from a group
    _PRIVATE_ACTIONS = {
        "portfolio", "portfolio_analyse", "portfolio_list",
        "portfolio_add_help", "portfolio_remove_help", "portfolio_clear_confirm",
        "alerts", "alerts_help",
        "dca", "dca_help",
    }
    if action in _PRIVATE_ACTIONS and chat_id != user_id:
        await query.answer(
            "🔒 Opening your private data in DM…",
            show_alert=False,
        )
        try:
            bot_info = await ctx.bot.get_me()
            bot_username = bot_info.username
            await ctx.bot.send_message(
                chat_id=user_id,
                text=(
                    f"🔒 <b>Private Session</b>\n\n"
                    f"Your personal data is only visible to you here.\n"
                    f"Tap the button below to continue."
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("▶️ Open " + (
                        "Portfolio" if "portfolio" in action else
                        "Alerts"    if "alert" in action else
                        "DCA Planner"
                    ), callback_data=action)
                ]])
            )
        except Exception:
            # If bot can't DM the user (never started DM), show a popup
            await query.answer(
                "🔒 Please start a private chat with me first, then tap this button there.",
                show_alert=True,
            )
        return

    # ── Menu ──
    if action == "menu":
        await _edit(query, home_text(), main_keyboard())

    # ── News ──
    elif action == "news":
        await _edit(query, "⏳ Fetching latest news…", None)
        text = await _build_news_box()
        await _edit(query, text, back_keyboard("news"))

    # ── Market scan ──
    elif action == "scan":
        await _edit(query, "🔍 Scanning markets… (~30 sec)", None)
        try:
            scanned, issued = await run_manual_scan(ctx.bot, notify_chat_id=chat_id)
            result = (
                f"✅ *Scan done* — {scanned} assets\n"
                f"{'Signals sent above 👆' if issued else 'No setups met threshold right now.'}"
            )
        except Exception as e:
            result = f"❌ Scan error: `{e}`"
        await _edit(query, result, back_keyboard())

    # ── Opportunities ──
    elif action == "opportunities":
        await _edit(query, "🔍 Scanning 20 coins for setups… (~45 sec)", None)
        opps = await scan_opportunities(top_n=5)
        text = format_opportunities(opps)
        await _edit(query, text, back_keyboard("opportunities"))

    # ── Chart menu ──
    elif action == "chart_menu":
        await _edit(query, "📉 *Pick a coin:*", chart_keyboard())

    elif action.startswith("chart_"):
        asset = action[6:]
        await _edit(query, f"📉 Generating `{asset}` chart…", None)
        try:
            recent = await get_recent_signals(20)
            live   = next((s for s in recent if s["asset"] == asset and s.get("outcome") == "pending"), None)
            img    = await generate_chart(asset, signal=live, timeframe="1h", candles=80)
            sym    = asset.replace("/", "")
            caption = (
                f"📉 *{sym}* — 1H\n"
                f"🟢▲ Buy signal  •  🔴▼ Sell signal\n"
                f"EMA21 (yellow) / EMA50 (orange) / EMA200 (purple) / VWAP (blue)\n"
            )
            if live:
                caption += f"\n📌 _Live {live['direction'].upper()} signal: entry / SL / TP overlaid_"
            caption += "\n⚠️ _Paper trade only._"
            await query.message.reply_photo(photo=img, caption=caption, parse_mode=ParseMode.MARKDOWN)
            await _edit(query, "📉 *Pick another coin or go back:*", chart_keyboard())
        except Exception as e:
            await _edit(query, f"❌ Chart error: `{e}`", back_keyboard())

    # ── Prices ──
    elif action == "prices":
        await _edit(query, "💲 *Pick a coin:*", prices_keyboard())

    elif action.startswith("price_"):
        asset = action[6:]
        await _edit(query, f"⏳ Fetching `{asset}`…", None)
        text = await _build_price(asset)
        await _edit(query, text, prices_keyboard())

    # ── Fear & Greed ──
    elif action == "feargreed":
        await _edit(query, "⏳ Fetching index…", None)
        text = await _build_fear_greed()
        await _edit(query, text, back_keyboard("feargreed"))

    # ── Signals ──
    elif action == "signals":
        sigs = await get_recent_signals(5)
        text = format_recent_signals_box(sigs)
        await _edit(query, text, back_keyboard())

    # ── Open Signals ──
    elif action == "open_signals":
        from utils.db import get_pending_signals
        sigs = await get_pending_signals()
        text = format_open_signals(sigs)
        await _edit(query, text, back_keyboard("open_signals"))

    # ── Status ──
    elif action == "status":
        text = _build_status()
        await _edit(query, text, back_keyboard())

    # ── Pro Strategies ──
    elif action == "strategies":
        await _edit(query, "🎯 *Pro Strategies*\n\nChoose an option below:", strategies_keyboard())

    elif action == "strategy_list":
        text = format_strategy_list()
        await _edit(query, text, strategies_keyboard())

    elif action == "strategy_scan":
        await _edit(query, "🔍 Running live strategy scan across all assets… (~45 sec)", None)
        try:
            results = await run_strategy_scan(config.WATCHLIST)
            text = format_live_scan_results(results)
        except Exception as e:
            text = f"❌ Scan error: `{e}`"
        await _edit(query, text, strategies_keyboard())

    elif action.startswith("strategy_") and not action.startswith("strategy_scan"):
        sid  = action[9:]
        text = format_strategy_detail(sid)
        await _edit(query, text, strategies_keyboard())

    # ── Whale Pick ──
    elif action == "whalepick":
        await _edit(query, "🐋 Scanning 80+ coins for whale activity… (~60 sec)", None)
        try:
            coin = await run_whale_scan()
            if coin:
                await log_whale_pick(coin.symbol, coin.price, coin.whale_score, coin.signals[:3])
                text = format_whale_pick(coin)
                await _edit_html(query, text, back_keyboard("whalepick"))
                return
            else:
                text = "🐋 <b>Whale Scan</b>\n\n<i>No strong whale signals detected right now.\nTry again later or check 9:00 AM NPT push.</i>"
        except Exception as e:
            text = f"❌ Whale scan error: <code>{e}</code>"
        await _edit_html(query, text, back_keyboard("whalepick"))

    # ── Funding & OI ──
    elif action == "funding_oi":
        await _edit(query, "📊 *Funding Rates & Open Interest*\n\nChoose view:", funding_keyboard())

    elif action == "funding_full":
        await _edit(query, "⏳ Fetching funding rates…", None)
        data = await fetch_funding_oi()
        text = format_funding_oi(data)
        await _edit(query, text, funding_keyboard())

    elif action == "oi_spikes":
        await _edit(query, "⏳ Scanning OI spikes…", None)
        data = await fetch_funding_oi()
        text = format_oi_spikes(data)
        await _edit(query, text, funding_keyboard())

    # ── BTC Dominance ──
    elif action == "dominance":
        await _edit(query, "⏳ Fetching market dominance…", None)
        data = await fetch_dominance()
        text = format_dominance(data)
        await _edit(query, text, back_keyboard("dominance"))

    # ── Alerts  (keyed by user_id — private per person) ──
    elif action == "alerts":
        alerts = await get_active_alerts(chat_id=user_id)
        text   = format_alerts_list(alerts)
        await _edit_html(query, text, alerts_keyboard())

    elif action == "alerts_help":
        await _edit_html(query,
            "🔔 <b>Set a Price Alert</b>\n\n"
            "Send me one of these commands:\n\n"
            "<code>/alert BTC above 70000</code>\n"
            "<code>/alert ETH below 2500</code>\n"
            "<code>/alert SOL above 200</code>\n\n"
            "<i>I'll notify you privately the moment the price crosses your target.</i>",
            back_keyboard("alerts")
        )

    # ── DCA  (keyed by user_id — private per person) ──
    elif action == "dca":
        text = await format_dca_plans(user_id)
        await _edit_html(query, text, dca_keyboard())

    elif action == "dca_help":
        await _edit_html(query,
            "📅 <b>Create DCA Plan</b>\n\n"
            "Send me one of these commands:\n\n"
            "<code>/dca BTC 100 weekly</code>\n"
            "<code>/dca ETH 50 daily</code>\n"
            "<code>/dca SOL 200 monthly</code>\n\n"
            "<i>Frequencies: daily / weekly / monthly\nReminders go to your private chat.</i>",
            back_keyboard("dca")
        )

    # ── Portfolio  (keyed by user_id — completely private per person) ──
    elif action == "portfolio":
        await _edit_html(query,
            "💼 <b>My Portfolio</b>  🔒\n\n"
            "Your holdings are private — only visible to you.\n\n"
            "<b>Quick add:</b>  <code>/addholding BTC 0.5 45000</code>\n"
            "<i>Format: symbol · amount · your buy price</i>",
            portfolio_keyboard()
        )

    elif action == "portfolio_analyse":
        await _edit_html(query, "⏳ Fetching live prices…", None)
        try:
            text = await build_portfolio_analysis(user_id)
        except Exception as e:
            text = f"❌ Portfolio error: <code>{_esc_html(str(e))}</code>"
        await _edit_html(query, text, portfolio_keyboard())

    elif action == "portfolio_list":
        holdings = await get_holdings(user_id)
        text = format_holdings_list_html(holdings)
        await _edit_html(query, text, portfolio_keyboard())

    elif action == "portfolio_add_help":
        await _edit_html(query,
            "➕ <b>Add a Holding</b>\n\n"
            "Send any of these commands:\n\n"
            "<code>/addholding BTC 0.5 45000</code>\n"
            "<code>/addholding ETH 2 2800</code>\n"
            "<code>/addholding SOL 10 120 long-term hold</code>\n"
            "<code>/addholding PEPE 1000000 0.0000025</code>\n\n"
            "<i>Format: /addholding SYMBOL AMOUNT BUY_PRICE [optional note]</i>",
            portfolio_keyboard()
        )

    elif action == "portfolio_clear_confirm":
        await clear_portfolio(user_id)
        await _edit_html(query,
            "🗑 <b>Portfolio cleared.</b>\n\nAll holdings removed.\n\n"
            "Start fresh with <code>/addholding BTC 0.5 45000</code>",
            portfolio_keyboard()
        )

    elif action == "portfolio_remove_help":
        holdings = await get_holdings(user_id)
        if not holdings:
            text = "💼 <b>Portfolio is empty.</b>\n\nAdd holdings first with <code>/addholding</code>."
        else:
            text = (
                "🗑 <b>Remove a Holding</b>\n\n"
                "Use the ID number:\n"
                "<code>/removeholding &lt;id&gt;</code>\n\n"
                "<b>Your holdings:</b>\n"
            )
            for h in holdings:
                text += f"  <code>#{h['id']}</code>  <b>{h['symbol']}</b>  {h['amount']:,g} @ ${h['buy_price']}\n"
        await _edit_html(query, text, portfolio_keyboard())

    # ── Token Lookup ──
    elif action == "token_lookup":
        await _edit_html(query,
            "🔎 <b>Token Deep Dive</b>\n\n"
            "Send me any token name or symbol:\n\n"
            "<code>/token BTC</code> — Bitcoin full analysis\n"
            "<code>/token ETH</code> — Ethereum\n"
            "<code>/token SOL</code> — Solana\n"
            "<code>/token pepe</code> — search by name\n\n"
            "<i>Includes: price, ATH/ATL, market data, TA, risk score, opportunity score, links.</i>",
            back_keyboard()
        )

    # ── Weekly Report ──
    elif action == "weekly_report":
        await _edit(query, "📊 Building weekly report…", None)
        text = await build_weekly_report()
        await _edit_html(query, text, back_keyboard("weekly_report"))

    # ── Connection test ──
    elif action == "conntest":
        await _edit(query, "🔌 Testing data sources…", None)
        text = await _build_conntest()
        await _edit(query, text, back_keyboard())


async def _edit(query, text: str, keyboard):
    try:
        await query.edit_message_text(
            text=text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard, disable_web_page_preview=True,
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"edit error: {e}")


async def _edit_html(query, text: str, keyboard):
    """Edit message with HTML parse mode (Bot API 9.0+ formatting)."""
    try:
        await query.edit_message_text(
            text=text, parse_mode=ParseMode.HTML,
            reply_markup=keyboard, disable_web_page_preview=True,
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"edit_html error: {e}")


# ── Content builders ───────────────────────────────────────────────────────────

async def _build_news_box() -> str:
    items = await fetch_latest_news(limit=8)
    fg    = await fetch_fear_greed()
    if not items:
        return "📰 *Latest News*\n\n_No news fetched — add CRYPTOPANIC\\_API\\_KEY for better results._"
    lines = [
        f"📰 *Latest Crypto News* — {npt_now()}\n"
        f"🌡 F&G: *{fg['label']}* `{fg['value']}/100`\n"
        "━━━━━━━━━━━━━━━━━━"
    ]
    for item in items:
        title = item["title"][:70] + ("…" if len(item["title"]) > 70 else "")
        title = title.replace("*","").replace("_","")
        age   = f"{item['age_min']}m" if item["age_min"] < 60 else f"{item['age_min']//60}h"
        lines.append(f"\n{item['sentiment']} *{title}*\n   _{item['source']} · {age} ago_")
    lines += ["\n━━━━━━━━━━━━━━━━━━", "_🟢 bullish  🔴 bearish  ⚪ neutral_"]
    return "\n".join(lines)


def _fmt(p: float) -> str:
    if p >= 10000: return f"${p:,.0f}"
    if p >= 100:   return f"${p:,.1f}"
    if p >= 1:     return f"${p:,.3f}"
    return f"${p:.5f}"


async def _build_price(asset: str) -> str:
    try:
        ta     = await analyze(asset)
        ticker = await fetch_ticker(asset)
        price  = ticker["price"] or ta.price
        chg    = ticker["change_pct"]
        h24    = ticker["high_24h"]
        l24    = ticker["low_24h"]
        chg_icon = "🟢" if chg >= 0 else "🔴"
        rsi_note = "Overbought ⚠️" if ta.rsi > 70 else ("Oversold ⚠️" if ta.rsi < 30 else "Normal ✅")
        return (
            f"💲 *{asset}*  {chg_icon} `{chg:+.2f}%`\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"Price: `{_fmt(price)}`\n"
            f"24H High: `{_fmt(h24)}`  Low: `{_fmt(l24)}`\n\n"
            f"RSI(14): `{ta.rsi:.0f}` — {rsi_note}\n"
            f"EMA21 / 50 / 200:\n"
            f"  `{_fmt(ta.ema21)}` / `{_fmt(ta.ema50)}` / `{_fmt(ta.ema200)}`\n"
            f"VWAP: `{_fmt(ta.vwap)}`  ATR: `{_fmt(ta.atr)}`\n"
            f"MACD hist: `{ta.macd_hist:+.4f}`\n"
            f"Regime: `{ta.regime}`  TA Score: `{ta.ta_score:+.2f}`\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"_Updated {npt_now()}_"
        )
    except Exception as e:
        return f"❌ Error fetching `{asset}`:\n`{e}`"


async def _build_fear_greed() -> str:
    fg   = await fetch_fear_greed()
    val  = fg["value"]
    bar  = "█" * (val // 10) + "░" * (10 - val // 10)
    interp = (
        "Extreme fear — contrarian buying zone, market over-correcting."
        if val <= 25 else
        "Fear — cautious but setups starting to form on strong assets."
        if val <= 45 else
        "Neutral — no strong sentiment bias, follow price action."
        if val <= 55 else
        "Greed — rising optimism, watch for overextension."
        if val <= 75 else
        "Extreme greed — historically a contrarian sell zone. Tighten risk."
    )
    return (
        f"{fg['emoji']} *Fear & Greed Index*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"*{val} / 100 — {fg['label']}*\n"
        f"`[{bar}]`\n\n"
        f"📌 _{interp}_\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "_Extreme readings used as contrarian signals (not follow signals)._"
    )


async def _build_conntest() -> str:
    results = await test_all_sources()
    lines   = ["🔌 *Data Source Test*\n━━━━━━━━━━━━━━━━━━"]
    working = []
    for name, ok, detail in results:
        if ok:
            lines.append(f"✅ *{name}* — `{detail}`")
            working.append(name)
        else:
            lines.append(f"❌ {name} — `{detail[:55]}`")
    lines.append("\n━━━━━━━━━━━━━━━━━━")
    if working:
        lines.append(f"Using: *{working[0]}* (first working source)")
    else:
        lines.append("⚠️ _No sources reachable — check internet connection._")
    return "\n".join(lines)


def _build_status() -> str:
    news_job = scheduler.get_job("morning_news")
    scan_job = scheduler.get_job("morning_scan")

    def _next(job):
        if job and job.next_run_time:
            dt = job.next_run_time + timedelta(hours=5, minutes=45)
            return dt.strftime("%I:%M %p NPT")
        return "N/A"

    return (
        f"⚙️ *System Status*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕐 {npt_now()}\n"
        f"Exchange: `{config.EXCHANGE}`\n"
        f"Watchlist: `{len(config.WATCHLIST)}` assets\n\n"
        f"📅 *Next scheduled:*\n"
        f"  News brief:    `{_next(news_job)}`\n"
        f"  Analytics:     `{_next(scan_job)}`\n\n"
        "🔇 _Auto-scan is OFF — signals only fire at 8 AM NPT or on manual tap._\n"
        "━━━━━━━━━━━━━━━━━━"
    )


def _esc_html(t: str) -> str:
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


async def _push_html(bot: Bot, text: str):
    """Send HTML-formatted push message to the configured chat."""
    if not config.TELEGRAM_CHAT_ID:
        return
    try:
        await bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"HTML push failed: {e}")


# ── Fallback text handler (commands) ──────────────────────────────────────────

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands*\n\n"
        "`/start` — Open main panel\n"
        "`/addholding BTC 0.5 45000` — Add portfolio holding\n"
        "`/removeholding &lt;id&gt;` — Remove holding\n"
        "`/clearportfolio` — Clear all holdings\n"
        "`/token BTC` or `/coin SOL` — Full token deep dive\n"
        "`/alert BTC above 70000` — Set price alert\n"
        "`/delalert <id>` — Remove alert\n"
        "`/dca BTC 100 weekly` — DCA reminder\n"
        "`/canceldca <id>` — Cancel DCA plan\n"
        "`/watchlist` — View watchlist\n"
        "`/watchlist add LINK` — Add coin\n"
        "`/watchlist remove BTC` — Remove coin\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(),
    )


async def cmd_unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Use /start to open the panel or /help for commands.",
        reply_markup=main_keyboard(),
    )


# ── Scheduled jobs ─────────────────────────────────────────────────────────────

async def _job_morning_news(bot: Bot):
    try:
        await run_morning_news(bot)
    except Exception as e:
        logger.error(f"Morning news job failed: {e}", exc_info=True)


async def _job_morning_scan(bot: Bot):
    try:
        await run_morning_analytics(bot)
    except Exception as e:
        logger.error(f"Morning analytics job failed: {e}", exc_info=True)


async def _job_whale_pick(bot: Bot):
    """9:00 AM NPT (3:15 UTC) — push daily whale coin pick."""
    logger.info("Running daily whale pick job (9 AM NPT)")
    try:
        coin = await run_whale_scan()
        if coin:
            await log_whale_pick(coin.symbol, coin.price, coin.whale_score, coin.signals[:3])
            text = format_whale_pick(coin, is_scheduled=True)
            await _push_html(bot, text)
        else:
            await _push_html(bot, "🐋 <b>Daily Whale Pick</b>\n\n<i>No strong whale accumulation detected today. Markets may be ranging — wait for clearer setups.</i>")
    except Exception as e:
        logger.error(f"Whale pick job failed: {e}", exc_info=True)


async def _job_weekly_report(bot: Bot):
    """10:00 AM NPT Sunday (04:15 UTC Sun) — push weekly performance report."""
    logger.info("Running weekly performance report (10 AM NPT Sunday)")
    try:
        text = await build_weekly_report()
        await _push_html(bot, text)
    except Exception as e:
        logger.error(f"Weekly report job failed: {e}", exc_info=True)


async def _job_check_signals(bot: Bot):
    """Every 10 min — check open signals vs live price, notify on TP/SL hit."""
    try:
        resolved = await check_signals(bot=bot, chat_id=config.TELEGRAM_CHAT_ID)
        if resolved:
            logger.info(f"Signal tracker: resolved {len(resolved)} signals")
    except Exception as e:
        logger.error(f"Signal tracker job failed: {e}", exc_info=True)


async def _job_check_alerts(bot: Bot):
    """Every 5 min — check custom price alerts."""
    try:
        triggered = await check_alerts(bot=bot)
        if triggered:
            logger.info(f"Alert checker: triggered {len(triggered)} alerts")
    except Exception as e:
        logger.error(f"Alert checker job failed: {e}", exc_info=True)


async def _job_check_dca(bot: Bot):
    """Every hour — check due DCA plans and send reminders."""
    try:
        notified = await check_due_dca(bot=bot)
        if notified:
            logger.info(f"DCA checker: sent {len(notified)} reminders")
    except Exception as e:
        logger.error(f"DCA checker job failed: {e}", exc_info=True)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
    asyncio.run(_run())


async def _run():
    await init_db()

    import ssl
    import certifi
    from telegram.request import HTTPXRequest
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    request = HTTPXRequest(connection_pool_size=8)
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).request(request).build()

    # Commands
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("alert",       cmd_alert))
    app.add_handler(CommandHandler("delalert",    cmd_delalert))
    app.add_handler(CommandHandler("dca",         cmd_dca))
    app.add_handler(CommandHandler("canceldca",   cmd_canceldca))
    app.add_handler(CommandHandler("addholding",   cmd_addholding))
    app.add_handler(CommandHandler("removeholding",cmd_removeholding))
    app.add_handler(CommandHandler("clearportfolio",cmd_clearportfolio))
    app.add_handler(CommandHandler("token",       cmd_token))
    app.add_handler(CommandHandler("coin",        cmd_token))
    app.add_handler(CommandHandler("watchlist",   cmd_watchlist))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    # Scheduled jobs
    # 6:00 AM NPT = 00:15 UTC
    scheduler.add_job(
        _job_morning_news, "cron",
        hour=config.MORNING_NEWS_UTC_H, minute=config.MORNING_NEWS_UTC_M,
        id="morning_news", kwargs={"bot": app.bot},
    )
    # 8:00 AM NPT = 02:15 UTC
    scheduler.add_job(
        _job_morning_scan, "cron",
        hour=config.MORNING_SCAN_UTC_H, minute=config.MORNING_SCAN_UTC_M,
        id="morning_scan", kwargs={"bot": app.bot},
    )
    # 9:00 AM NPT = 03:15 UTC daily
    scheduler.add_job(
        _job_whale_pick, "cron",
        hour=3, minute=15,
        id="whale_pick", kwargs={"bot": app.bot},
    )
    # 10:00 AM NPT Sunday = 04:15 UTC Sunday
    scheduler.add_job(
        _job_weekly_report, "cron",
        day_of_week="sun", hour=4, minute=15,
        id="weekly_report", kwargs={"bot": app.bot},
    )
    # TP/SL tracker — every 10 minutes
    scheduler.add_job(
        _job_check_signals, "interval",
        minutes=10,
        id="signal_tracker", kwargs={"bot": app.bot},
    )
    # Price alerts — every 5 minutes
    scheduler.add_job(
        _job_check_alerts, "interval",
        minutes=5,
        id="alert_checker", kwargs={"bot": app.bot},
    )
    # DCA reminders — every hour
    scheduler.add_job(
        _job_check_dca, "interval",
        hours=1,
        id="dca_checker", kwargs={"bot": app.bot},
    )

    scheduler.start()
    logger.info(
        "Scheduled: news@00:15 UTC · scan@02:15 UTC · whale@03:15 UTC · "
        "weekly(sun)@04:15 UTC · signals every 10min · alerts every 5min · DCA every 1h"
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=False)

    logger.info("Bot running. Press Ctrl+C to stop.")
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()
        await close_exchange()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    main()
