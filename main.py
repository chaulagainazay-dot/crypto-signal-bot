"""
Trading AI Assistant — @hcglivesignalbot
Complete crypto trading bot: Market, Signals, Learn, Portfolio, Research, Tools, Alerts, AI Coach, Journal, Challenges, Profile.
"""
import asyncio
import logging
import os
import random
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
from utils.keyboards import kb, kb_home
from utils.fmt import npt_now, fp
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
from layers.learn_content import LESSONS, QUIZ_QUESTIONS
from layers.calc_tools import (
    calc_position_size, calc_risk_reward, calc_profit,
    calc_dca, calc_compound, calc_liquidation, calc_funding, calc_fee,
)
from layers.ai_coach import ask_coach
from layers.journal_layer import (
    add_journal_entry, get_journal_entries, get_journal_stats,
    format_journal_stats, format_journal_list,
)
from layers.challenges_layer import (
    CHALLENGES, start_challenge, get_active_challenges,
    get_completed_challenges, format_challenges_menu, check_in_challenge,
)
from utils.alerts import parse_alert_command, check_alerts, format_alerts_list
from utils.db import (
    init_db, get_recent_signals, log_scan, log_whale_pick,
    add_alert, get_active_alerts, delete_alert,
    add_dca_plan, get_dca_plans,
    add_holding, get_holdings, remove_holding, clear_portfolio,
    save_quiz_score, get_quiz_history,
    get_user_settings, upsert_user_settings,
    save_coach_message, get_coach_history,
)
from layers.l5_delivery import (
    format_recent_signals_box, format_morning_news,
    format_signal, push,
)
from scanner import run_morning_news, run_morning_analytics, run_manual_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

# ── State tracking ─────────────────────────────────────────────────────────────
_coach_mode: set[str] = set()
_quiz_state: dict[str, dict] = {}


# ═══════════════════════════════════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════════════

def main_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📈 Market", "market"),          ("🎯 Signals", "signals_menu")],
        [("📚 Learn Trading", "learn"),    ("💼 Portfolio", "portfolio")],
        [("📰 Research", "research"),      ("🧮 Tools", "tools_menu")],
        [("🔔 Alerts", "alerts"),          ("🤖 AI Coach", "coach_menu")],
        [("📊 Journal", "journal"),        ("🏆 Challenges", "challenges")],
        [("👤 Profile", "profile"),        ("⚙️ Settings", "settings")],
        home=False,
    )


def market_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📊 Market Overview", "market_overview"), ("🔴 Live Market", "live_market")],
        [("🔍 Coin Scanner", "coin_scanner"),        ("😱 Fear & Greed", "feargreed")],
        [("🌐 Dominance", "dominance"),              ("📊 Funding & OI", "funding_oi")],
        back="menu",
    )


def market_overview_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("₿ BTC Overview", "market_btc"),   ("Ξ ETH Overview", "market_eth")],
        [("🪙 Altcoins", "market_alts"),      ("😱 Fear & Greed", "feargreed")],
        [("📈 Market Trend", "market_trend"), ("🌐 Dominance", "dominance")],
        [("💰 Volume", "market_volume"),      ("💧 Liquidations", "market_liq")],
        back="market",
    )


def live_market_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("🚀 Top Gainers", "live_gainers"),  ("📉 Top Losers", "live_losers")],
        [("🔥 Trending", "live_trending"),    ("🆕 New Listings", "live_new")],
        [("💰 High Volume", "live_volume"),   ("⚡ Most Volatile", "live_volatile")],
        [("🐋 Whales Buying", "live_whale_buy"), ("🐻 Whales Selling", "live_whale_sell")],
        back="market",
    )


def coin_scanner_keyboard() -> InlineKeyboardMarkup:
    coins = [("BTC", "scan_BTC"), ("ETH", "scan_ETH"), ("SOL", "scan_SOL"),
             ("BNB", "scan_BNB"), ("XRP", "scan_XRP"), ("SUI", "scan_SUI")]
    rows = [coins[i:i+3] for i in range(0, len(coins), 3)]
    buttons = [[(lbl, cb) for lbl, cb in row] for row in rows]
    buttons.append([("🔎 Type coin name", "scanner_help")])
    return kb(*buttons, back="market")


def signals_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("⭐ Best Coin Today", "signal_best"),   ("📊 Market Scan", "scan")],
        [("📈 Swing Trade", "swing_menu"),         ("⚡ Scalping", "scalp_menu")],
        [("🔮 Futures", "futures_menu"),           ("💱 Spot Only", "signal_spot")],
        [("🔺 Breakout Scanner", "breakout_scan"), ("🔻 Reversal Scanner", "reversal_scan")],
        [("🐋 Whale Pick", "whalepick"),           ("📋 Open Signals", "signals_open")],
        back="menu",
    )


def swing_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("1 Day", "swing_1d"), ("3 Days", "swing_3d")],
        [("1 Week", "swing_1w"), ("1 Month", "swing_1m")],
        back="signals_menu",
    )


def scalp_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("1 Min", "scalp_1m"), ("5 Min", "scalp_5m"), ("15 Min", "scalp_15m")],
        back="signals_menu",
    )


def futures_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📈 Long", "futures_long"), ("📉 Short", "futures_short")],
        [("⚡ Leverage Guide", "futures_leverage"), ("💀 Liq Warning", "futures_liq_warn")],
        back="signals_menu",
    )


def learn_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("🌱 Beginner", "learn_beginner"),       ("📊 Intermediate", "learn_intermediate")],
        [("🎓 Advanced", "learn_advanced"),        ("🧠 Psychology", "learn_psychology")],
        [("🛡 Risk Management", "learn_risk"),     ("❓ Daily Quiz", "quiz_start")],
        back="menu",
    )


def learn_beginner_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📖 What is Trading", "lesson_what_is_trading")],
        [("💱 Spot Trading", "lesson_spot_trading")],
        [("📊 Futures Trading", "lesson_futures_trading")],
        [("💸 Margin Trading", "lesson_margin_trading")],
        [("⚡ Leverage", "lesson_leverage_explained")],
        back="learn",
    )


def learn_intermediate_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📐 Support & Resistance", "lesson_support_resistance")],
        [("📈 Trendlines", "lesson_trendlines")],
        [("🏗 Market Structure", "lesson_market_structure")],
        [("📊 Volume Analysis", "lesson_volume_analysis")],
        [("🕯 Candlestick Patterns", "lesson_candlestick_patterns")],
        back="learn",
    )


def learn_advanced_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("💡 Smart Money (SMC)", "lesson_smart_money")],
        [("🎓 ICT Concepts", "lesson_ict_concepts")],
        [("📉 Wyckoff Method", "lesson_wyckoff")],
        [("🌊 Elliott Wave", "lesson_elliott_wave")],
        [("🟦 Order Blocks", "lesson_order_blocks")],
        [("⚡ Fair Value Gap", "lesson_fair_value_gap")],
        [("💧 Liquidity", "lesson_liquidity")],
        [("🏦 Market Maker Model", "lesson_market_maker_model")],
        back="learn",
    )


def learn_psychology_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("😨 Fear", "lesson_fear_psychology"),        ("💰 Greed", "lesson_greed_psychology")],
        [("💢 Revenge Trading", "lesson_revenge_trading"), ("⚔️ Discipline", "lesson_discipline")],
        back="learn",
    )


def learn_risk_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("🛡 Risk Management", "lesson_risk_management")],
        [("📏 Position Sizing", "lesson_position_sizing")],
        back="learn",
    )


def portfolio_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📊 Analyse", "portfolio_analyse"),   ("📋 View Holdings", "portfolio_list")],
        [("➕ Add Holding", "portfolio_add_help"), ("🗑 Remove", "portfolio_remove_help")],
        [("🏥 Health Check", "portfolio_health"), ("⚖️ Rebalance", "portfolio_rebalance")],
        [("📅 Investment Plan", "portfolio_plan"),  ("🔄 Clear All", "portfolio_clear")],
        back="menu",
    )


def research_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📰 Daily Research", "research_daily"),  ("🔍 Coin Research", "research_coin_menu")],
        [("📊 Research Score", "research_score_menu"), ("📅 News Feed", "news")],
        [("📈 Weekly Report", "weekly_report")],
        back="menu",
    )


def research_coin_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("₿ BTC", "research_BTC"), ("Ξ ETH", "research_ETH")],
        [("◎ SOL", "research_SOL"), ("🔗 LINK", "research_LINK")],
        [("🔎 Type coin", "research_coin_help")],
        back="research",
    )


def tools_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📏 Position Size", "tool_possize"),   ("🎯 Risk:Reward", "tool_rr")],
        [("💰 Profit Calc", "tool_profit"),      ("📉 DCA Calc", "tool_dca_calc")],
        [("📈 Compound Calc", "tool_compound"),  ("💀 Liquidation", "tool_liq")],
        [("💸 Funding Fee", "tool_funding"),     ("💳 Trading Fee", "tool_fee")],
        back="menu",
    )


def alerts_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("🔔 My Alerts", "alerts_list"),           ("➕ Price Alert", "alerts_add_help")],
        [("📅 DCA Plans", "dca"),                   ("📊 Signal Alerts", "alerts_signals")],
        back="menu",
    )


def coach_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("💬 Start Chat", "coach_start"),          ("📖 Clear History", "coach_clear")],
        [("❓ Should I buy BTC?", "coach_q_btc"),   ("📊 Rate my portfolio", "coach_q_port")],
        [("📈 Explain RSI", "coach_q_rsi"),         ("🛡 Create trading plan", "coach_q_plan")],
        back="menu",
    )


def journal_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("📊 Analysis", "journal_stats"),    ("📋 Recent Trades", "journal_list")],
        [("➕ Add Trade", "journal_add"),      ("❓ How to use", "journal_help")],
        back="menu",
    )


def challenges_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("🏆 All Challenges", "challenges_all")],
        [("⚔️ 30-Day Discipline", "ch_start_discipline_30")],
        [("🧘 No FOMO", "ch_start_no_fomo")],
        [("🛡 Risk Mgmt", "ch_start_risk_mgmt")],
        [("📚 Learning Streak", "ch_start_learning_streak")],
        [("🏅 My Progress", "challenges_progress")],
        back="menu",
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("👤 My Profile", "profile_view"),   ("⚙️ Settings", "settings")],
        [("📊 Quiz History", "quiz_history"), ("🏆 Achievements", "achievements")],
        back="menu",
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return kb(
        [("💱 Currency", "set_currency"),      ("⏰ Timezone", "set_timezone")],
        [("📊 Risk Profile", "set_risk"),      ("🤖 AI Style", "set_ai_style")],
        [("🔔 Notifications", "set_notifs")],
        back="profile",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _user_id(update: Update) -> str:
    return str(update.effective_user.id)


def _is_group(update: Update) -> bool:
    return update.effective_chat.type in ("group", "supergroup")


async def _edit(query, text: str, keyboard: InlineKeyboardMarkup = None):
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                       reply_markup=keyboard or kb_home())
    except BadRequest:
        pass


async def _redirect_to_dm(update: Update, ctx: ContextTypes.DEFAULT_TYPE, feature: str):
    bot = await ctx.bot.get_me()
    await update.message.reply_text(
        f"🔒 {feature} is private. Please message me directly:\n👉 @{bot.username}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💬 Open DM", url=f"https://t.me/{bot.username}")
        ]])
    )


def home_text() -> str:
    return (
        "🤖 <b>Trading AI Assistant</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Your complete crypto trading companion.\n\n"
        "<b>What I can do:</b>\n"
        "📈 Live market data & analysis\n"
        "🎯 AI-powered trade signals\n"
        "📚 Learn trading from zero\n"
        "💼 Track your portfolio\n"
        "📰 Research any coin\n"
        "🧮 Trading calculators\n"
        "🤖 AI coach for any question\n"
        "📊 Trade journal & analytics\n\n"
        "💬 <i>Type any coin ticker (BTC, ETH, SOL) or ask any question!</i>"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        bot = await ctx.bot.get_me()
        await update.message.reply_text(
            f"Hi! I'm a crypto trading AI. Message me at @{bot.username} for full features.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💬 Open DM", url=f"https://t.me/{bot.username}")
            ]])
        )
        return
    await update.message.reply_text(home_text(), parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(home_text(), parse_mode=ParseMode.HTML, reply_markup=main_keyboard())


async def cmd_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Alerts")
        return
    parts = update.message.text.split()[1:]
    if len(parts) < 3:
        await update.message.reply_text(
            "📌 <b>Alert format:</b>\n\n"
            "<code>/alert BTC above 70000</code>\n"
            "<code>/alert ETH below 3000</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([("🔔 My Alerts", "alerts_list")], back="menu"),
        )
        return
    uid = _user_id(update)
    result, msg = parse_alert_command(uid, parts)
    if result:
        await add_alert(uid, result["symbol"], result["condition"], result["target_price"])
        await update.message.reply_text(f"✅ Alert set!\n{msg}", parse_mode=ParseMode.HTML,
                                        reply_markup=kb([("🔔 My Alerts", "alerts_list")], back="menu"))
    else:
        await update.message.reply_text(f"❌ {msg}", parse_mode=ParseMode.HTML)


async def cmd_delalert(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()[1:]
    if not parts:
        await update.message.reply_text("Usage: /delalert <id>")
        return
    try:
        await delete_alert(int(parts[0]))
        await update.message.reply_text(f"✅ Alert deleted.",
                                        reply_markup=kb([("🔔 Alerts", "alerts_list")], back="menu"))
    except ValueError:
        await update.message.reply_text("❌ Invalid alert ID.")


async def cmd_dca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "DCA Planner")
        return
    parts = update.message.text.split()[1:]
    if len(parts) < 3:
        await update.message.reply_text(
            "📅 <b>DCA format:</b>\n\n"
            "<code>/dca BTC 50 weekly</code>\n<code>/dca ETH 100 monthly</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    uid = _user_id(update)
    result, msg = parse_dca_command(uid, parts)
    if result:
        await create_dca(result)
        await update.message.reply_text(f"✅ DCA plan created!\n{msg}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ {msg}", parse_mode=ParseMode.HTML)


async def cmd_canceldca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()[1:]
    if not parts:
        await update.message.reply_text("Usage: /canceldca <id>")
        return
    try:
        await delete_dca_plan(int(parts[0]))
        await update.message.reply_text("✅ DCA plan cancelled.")
    except Exception:
        await update.message.reply_text("❌ Invalid ID.")


async def cmd_addholding(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Portfolio")
        return
    parts = update.message.text.split()[1:]
    if len(parts) < 3:
        await update.message.reply_text(
            "💼 <b>Add holding:</b>\n\n<code>/add BTC 0.5 45000</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    uid = _user_id(update)
    result, msg = _parse_holding(uid, parts)
    if result:
        await add_holding(uid, result["symbol"], result["amount"], result["buy_price"], result.get("note", ""))
        await update.message.reply_text(f"✅ Added!\n{msg}", parse_mode=ParseMode.HTML,
                                        reply_markup=kb([("💼 Portfolio", "portfolio_analyse")], back="menu"))
    else:
        await update.message.reply_text(f"❌ {msg}", parse_mode=ParseMode.HTML)


async def cmd_removeholding(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()[1:]
    if not parts:
        await update.message.reply_text("Usage: /remove <id>")
        return
    uid = _user_id(update)
    try:
        await remove_holding(int(parts[0]), uid)
        await update.message.reply_text("✅ Holding removed.",
                                        reply_markup=kb([("💼 Portfolio", "portfolio_list")], back="menu"))
    except Exception:
        await update.message.reply_text("❌ Invalid ID.")


async def cmd_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()[1:]
    if not parts:
        await update.message.reply_text("Usage: /token BTC")
        return
    symbol = parts[0].upper()
    msg = await update.message.reply_text(f"🔍 Analysing {symbol}...")
    try:
        result = await run_token_deep_dive(symbol)
        await msg.edit_text(result, parse_mode=ParseMode.HTML,
                            reply_markup=kb([("🔄 Refresh", f"scan_{symbol}")], back="coin_scanner"))
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")


async def cmd_journal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _is_group(update):
        await _redirect_to_dm(update, ctx, "Journal")
        return
    parts = update.message.text.split()[1:]
    if len(parts) < 4:
        await update.message.reply_text(
            "📊 <b>Add trade to journal:</b>\n\n"
            "<code>/journal BTC LONG 60000 65000 1000</code>\n\n"
            "Format: /journal COIN DIRECTION ENTRY EXIT [SIZE_USD]",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([("📊 Open Journal", "journal")], back="menu"),
        )
        return
    uid = _user_id(update)
    try:
        coin = parts[0].upper()
        direction = parts[1].upper()
        entry = float(parts[2])
        exit_p = float(parts[3])
        size = float(parts[4]) if len(parts) > 4 else 0
        entry_id = await add_journal_entry(uid, coin, direction, entry, exit_p, size, "", "", "")
        pnl = (exit_p - entry) / entry * 100 if direction == "LONG" else (entry - exit_p) / entry * 100
        emoji = "✅" if pnl > 0 else "❌"
        await update.message.reply_text(
            f"{emoji} <b>Trade #{entry_id} recorded!</b>\n{coin} {direction}: <code>{pnl:+.2f}%</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([("📊 Journal", "journal_stats")], back="menu"),
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid format. Use: /journal BTC LONG 60000 65000")


async def cmd_calc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()[1:]
    if not parts:
        await update.message.reply_text(
            "🧮 <b>Calculator Commands:</b>\n\n"
            "<code>/calc possize 10000 1 60000 58000</code>\n"
            "<code>/calc rr 60000 58000 65000</code>\n"
            "<code>/calc profit 60000 65000 0.1</code>\n"
            "<code>/calc dca 60000:500 55000:500</code>\n"
            "<code>/calc compound 1000 10 12</code>\n"
            "<code>/calc liq 60000 10 long</code>\n"
            "<code>/calc funding 10000 0.01</code>\n"
            "<code>/calc fee 10000 bybit</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([("🧮 Tools", "tools_menu")], back="menu"),
        )
        return
    calc_type = parts[0].lower()
    try:
        if calc_type == "possize" and len(parts) >= 5:
            result = calc_position_size(float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
        elif calc_type == "rr" and len(parts) >= 4:
            tp2 = float(parts[4]) if len(parts) > 4 else None
            result = calc_risk_reward(float(parts[1]), float(parts[2]), float(parts[3]), tp2)
        elif calc_type == "profit" and len(parts) >= 4:
            lev = float(parts[4]) if len(parts) > 4 else 1.0
            result = calc_profit(float(parts[1]), float(parts[2]), float(parts[3]), lev)
        elif calc_type == "dca" and len(parts) >= 2:
            entries = [(float(p.split(":")[0]), float(p.split(":")[1])) for p in parts[1:]]
            result = calc_dca(entries)
        elif calc_type == "compound" and len(parts) >= 4:
            result = calc_compound(float(parts[1]), float(parts[2]), int(parts[3]))
        elif calc_type == "liq" and len(parts) >= 3:
            direction = parts[3] if len(parts) > 3 else "long"
            result = calc_liquidation(float(parts[1]), float(parts[2]), direction)
        elif calc_type == "funding" and len(parts) >= 3:
            result = calc_funding(float(parts[1]), float(parts[2]))
        elif calc_type == "fee" and len(parts) >= 2:
            exchange = parts[2] if len(parts) > 2 else "bybit"
            result = calc_fee(float(parts[1]), exchange)
        else:
            result = "❌ Invalid format. Type /calc for help."
    except (ValueError, IndexError) as e:
        result = f"❌ Error: {e}. Check your numbers."
    await update.message.reply_text(result, parse_mode=ParseMode.HTML,
                                     reply_markup=kb([("🧮 More Calculators", "tools_menu")], back="menu"))


# ═══════════════════════════════════════════════════════════════════════════════
# BUTTON HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    uid = str(query.from_user.id)

    if action == "menu":
        await _edit(query, home_text(), main_keyboard())
        return

    # ── MARKET ────────────────────────────────────────────────────────────────
    if action == "market":
        await _edit(query, "📈 <b>Market</b>\n━━━━━━━━━━━━━━━━━━\n\nExplore live crypto market data.", market_keyboard())
        return

    if action == "market_overview":
        await _edit(query, "📊 <b>Market Overview</b>\n\nSelect a view:", market_overview_keyboard())
        return

    if action in ("market_btc", "market_eth", "market_alts", "market_trend", "market_volume", "market_liq"):
        coin_map = {"market_btc": "BTC", "market_eth": "ETH", "market_alts": "SOL",
                    "market_trend": "BNB", "market_volume": "XRP", "market_liq": "BTC"}
        symbol = coin_map.get(action, "BTC")
        await query.edit_message_text(f"🔍 Loading {symbol} overview...", parse_mode=ParseMode.HTML)
        try:
            result = await run_token_deep_dive(symbol)
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", action)], back="market_overview"))
        except Exception as e:
            await _edit(query, f"❌ Error: {e}", kb(back="market_overview"))
        return

    if action == "live_market":
        await _edit(query, "🔴 <b>Live Market</b>\n━━━━━━━━━━━━━━━━━━\n\nReal-time market movers:", live_market_keyboard())
        return

    if action in ("live_gainers", "live_losers", "live_trending", "live_new",
                  "live_volume", "live_volatile", "live_whale_buy", "live_whale_sell"):
        await query.edit_message_text("📊 Loading market data...", parse_mode=ParseMode.HTML)
        try:
            result = await _build_live_market(action)
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", action)], back="live_market"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="live_market"))
        return

    if action == "coin_scanner":
        await _edit(query,
            "🔍 <b>Coin Scanner</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "Select a coin or type any ticker for full analysis.",
            coin_scanner_keyboard())
        return

    if action == "scanner_help":
        await _edit(query,
            "🔍 <b>Coin Scanner</b>\n\nJust type any coin ticker (BTC, SOL, DOGE...) as a message!",
            kb(back="coin_scanner"))
        return

    if action.startswith("scan_"):
        symbol = action[5:].upper()
        await query.edit_message_text(f"🔍 Scanning {symbol}...", parse_mode=ParseMode.HTML)
        try:
            result = await run_token_deep_dive(symbol)
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb(
                                               [("🔄 Refresh", action), ("📊 Chart", f"chart_{symbol.lower()}")],
                                               back="coin_scanner"))
        except Exception as e:
            await _edit(query, f"❌ Error scanning {symbol}: {e}", kb(back="coin_scanner"))
        return

    if action == "feargreed":
        await query.edit_message_text("😱 Loading Fear & Greed...", parse_mode=ParseMode.HTML)
        try:
            result = await _build_fear_greed()
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "feargreed")], back="market"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="market"))
        return

    if action == "dominance":
        await query.edit_message_text("🌐 Loading dominance...", parse_mode=ParseMode.HTML)
        try:
            data = await fetch_dominance()
            result = format_dominance(data)
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "dominance")], back="market"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="market"))
        return

    if action == "funding_oi":
        await query.edit_message_text("📊 Loading funding & OI...", parse_mode=ParseMode.HTML)
        try:
            data = await fetch_funding_oi(config.WATCHLIST[:8])
            result = format_funding_oi(data)
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("📈 OI Spikes", "oi_spikes"), ("🔄 Refresh", "funding_oi")], back="market"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="market"))
        return

    if action == "oi_spikes":
        await query.edit_message_text("📈 Loading OI spikes...", parse_mode=ParseMode.HTML)
        try:
            data = await fetch_funding_oi(config.WATCHLIST[:8])
            result = format_oi_spikes(data)
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "oi_spikes")], back="funding_oi"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="market"))
        return

    # ── SIGNALS ───────────────────────────────────────────────────────────────
    if action == "signals_menu":
        await _edit(query, "🎯 <b>AI Trade Signals</b>\n━━━━━━━━━━━━━━━━━━\n\nAI-powered trade opportunities:", signals_keyboard())
        return

    if action in ("signal_best", "scan", "signal_spot", "reversal_scan"):
        label_map = {"signal_best": "⭐ Finding best coin today...", "scan": "📊 Running market scan...",
                     "signal_spot": "💱 Scanning spot opportunities...", "reversal_scan": "🔻 Scanning reversal patterns..."}
        await query.edit_message_text(label_map.get(action, "📊 Scanning..."), parse_mode=ParseMode.HTML)
        try:
            results = await run_manual_scan(config.WATCHLIST)
            text = format_opportunities(results) if results else "⚠️ No strong signals right now. Try again later."
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", action)], back="signals_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="signals_menu"))
        return

    if action == "swing_menu":
        await _edit(query, "📈 <b>Swing Trade Signals</b>\n\nSelect timeframe:", swing_keyboard())
        return

    if action in ("swing_1d", "swing_3d", "swing_1w", "swing_1m"):
        tf_map = {"swing_1d": "1D", "swing_3d": "3D", "swing_1w": "1W", "swing_1m": "1M"}
        tf = tf_map[action]
        await query.edit_message_text(f"📈 Scanning for {tf} swing setups...", parse_mode=ParseMode.HTML)
        try:
            results = await run_manual_scan(config.WATCHLIST)
            text = format_opportunities(results) if results else f"⚠️ No {tf} swing setups found."
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", action)], back="swing_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="swing_menu"))
        return

    if action == "scalp_menu":
        await _edit(query, "⚡ <b>Scalping Signals</b>\n\nSelect timeframe:", scalp_keyboard())
        return

    if action in ("scalp_1m", "scalp_5m", "scalp_15m"):
        tf_map = {"scalp_1m": "1m", "scalp_5m": "5m", "scalp_15m": "15m"}
        tf = tf_map[action]
        await query.edit_message_text(f"⚡ Scanning {tf} scalp setups...", parse_mode=ParseMode.HTML)
        try:
            results = await run_manual_scan(config.WATCHLIST[:5])
            text = format_opportunities(results) if results else f"⚠️ No {tf} scalp setups found."
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", action)], back="scalp_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="scalp_menu"))
        return

    if action == "futures_menu":
        await _edit(query, "🔮 <b>Futures Signals</b>\n━━━━━━━━━━━━━━━━━━\n\nPerpetual futures trade ideas:", futures_keyboard())
        return

    if action in ("futures_long", "futures_short"):
        direction = "LONG" if action == "futures_long" else "SHORT"
        await query.edit_message_text(f"🔮 Scanning for {direction} setups...", parse_mode=ParseMode.HTML)
        try:
            results = await run_manual_scan(config.WATCHLIST)
            text = format_opportunities(results) if results else f"⚠️ No {direction} setups."
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", action)], back="futures_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="futures_menu"))
        return

    if action == "futures_leverage":
        await _edit(query,
            "⚡ <b>Leverage Guide for Futures</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "🟢 <b>Safe (beginner):</b> 2x–5x\n   Liquidation: 20–50% against you\n\n"
            "🟡 <b>Moderate:</b> 5x–10x\n   Liquidation: 10–20% against you\n\n"
            "🔴 <b>Aggressive:</b> 10x–20x\n   Liquidation: 5–10% against you\n\n"
            "💀 <b>Very high risk:</b> 20x–50x\n   Liquidation: 2–5% against you\n\n"
            "⚠️ <b>Never use 50x–100x.</b>\n\n"
            "💡 Use the Liquidation Calculator in 🧮 Tools.",
            kb([("💀 Liq Calculator", "tool_liq")], back="futures_menu"))
        return

    if action == "futures_liq_warn":
        await _edit(query,
            "⚠️ <b>Liquidation Warning</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "You get liquidated when your losses equal your margin.\n\n"
            "<b>What to do when close to liquidation:</b>\n"
            "✅ Add margin to push liq price further\n"
            "✅ Reduce position size\n"
            "✅ Close partially to lock in capital\n"
            "❌ Never average down hoping for recovery\n\n"
            "💡 Always set stop loss at 50% of liq distance.",
            kb([("💀 Liq Calculator", "tool_liq")], back="futures_menu"))
        return

    if action == "breakout_scan":
        await query.edit_message_text("🔺 Scanning for breakout patterns...", parse_mode=ParseMode.HTML)
        try:
            result = await run_strategy_scan(config.WATCHLIST)
            text = format_live_scan_results(result) if result else "⚠️ No breakout patterns found."
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "breakout_scan")], back="signals_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="signals_menu"))
        return

    if action == "whalepick":
        await query.edit_message_text("🐋 Running whale analysis...", parse_mode=ParseMode.HTML)
        try:
            coins = await run_whale_scan(config.WATCHLIST)
            if coins:
                best = coins[0]
                text = format_whale_pick(best)
                await log_whale_pick(best["symbol"], best.get("price", 0), best.get("whale_score", 0), str(best.get("signals", {})))
            else:
                text = "🐋 No strong whale activity detected right now."
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "whalepick")], back="signals_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="signals_menu"))
        return

    if action == "signals_open":
        try:
            signals = await get_recent_signals(10)
            text = format_recent_signals_box(signals) if signals else "📋 No recent signals found."
            await _edit(query, text, kb([("🔄 Refresh", "signals_open")], back="signals_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="signals_menu"))
        return

    # ── LEARN ─────────────────────────────────────────────────────────────────
    if action == "learn":
        await _edit(query, "📚 <b>Learn Trading</b>\n━━━━━━━━━━━━━━━━━━\n\nMaster trading from beginner to advanced.", learn_keyboard())
        return
    if action == "learn_beginner":
        await _edit(query, "🌱 <b>Beginner Lessons</b>\n\nSelect a topic:", learn_beginner_keyboard())
        return
    if action == "learn_intermediate":
        await _edit(query, "📊 <b>Intermediate Lessons</b>\n\nSelect a topic:", learn_intermediate_keyboard())
        return
    if action == "learn_advanced":
        await _edit(query, "🎓 <b>Advanced Lessons</b>\n\nSelect a topic:", learn_advanced_keyboard())
        return
    if action == "learn_psychology":
        await _edit(query, "🧠 <b>Trading Psychology</b>\n\nSelect a topic:", learn_psychology_keyboard())
        return
    if action == "learn_risk":
        await _edit(query, "🛡 <b>Risk Management</b>\n\nSelect a topic:", learn_risk_keyboard())
        return

    if action.startswith("lesson_"):
        lesson_key = action[7:]
        lesson = LESSONS.get(lesson_key)
        if lesson:
            section_map = {
                "what_is_trading": "learn_beginner", "spot_trading": "learn_beginner",
                "futures_trading": "learn_beginner", "margin_trading": "learn_beginner",
                "leverage_explained": "learn_beginner",
                "support_resistance": "learn_intermediate", "trendlines": "learn_intermediate",
                "market_structure": "learn_intermediate", "volume_analysis": "learn_intermediate",
                "candlestick_patterns": "learn_intermediate",
                "smart_money": "learn_advanced", "ict_concepts": "learn_advanced",
                "wyckoff": "learn_advanced", "elliott_wave": "learn_advanced",
                "order_blocks": "learn_advanced", "fair_value_gap": "learn_advanced",
                "liquidity": "learn_advanced", "market_maker_model": "learn_advanced",
                "fear_psychology": "learn_psychology", "greed_psychology": "learn_psychology",
                "revenge_trading": "learn_psychology", "discipline": "learn_psychology",
                "risk_management": "learn_risk", "position_sizing": "learn_risk",
            }
            back_action = section_map.get(lesson_key, "learn")
            await _edit(query, lesson["body"], kb([("❓ Daily Quiz", "quiz_start")], back=back_action))
        else:
            await _edit(query, "❌ Lesson not found.", kb(back="learn"))
        return

    # ── QUIZ ──────────────────────────────────────────────────────────────────
    if action == "quiz_start":
        questions = random.sample(QUIZ_QUESTIONS, min(10, len(QUIZ_QUESTIONS)))
        _quiz_state[uid] = {"questions": questions, "index": 0, "score": 0, "answers": []}
        await _send_quiz_question(query, uid)
        return

    if action.startswith("quiz_ans_"):
        ans_idx = int(action.split("_")[2])
        state = _quiz_state.get(uid)
        if not state:
            await _edit(query, "❌ Quiz expired. Start a new one.", kb([("❓ Start Quiz", "quiz_start")], back="learn"))
            return
        q = state["questions"][state["index"]]
        correct = ans_idx == q["answer"]
        if correct:
            state["score"] += 1
        state["answers"].append({"correct": correct, "explanation": q["explanation"]})
        state["index"] += 1
        result_text = ("✅ Correct!" if correct else "❌ Wrong!") + f"\n\n💡 {q['explanation']}"
        if state["index"] >= len(state["questions"]):
            score = state["score"]
            total = len(state["questions"])
            await save_quiz_score(uid, score, total)
            grade = "🏆 Excellent!" if score >= 9 else "🎯 Good!" if score >= 7 else "📚 Keep studying!"
            final = (
                f"📊 <b>Quiz Complete!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"{result_text}\n\n"
                f"<b>Final Score: {score}/{total}</b>  {grade}\n\n"
                f"{''.join(['✅' if a['correct'] else '❌' for a in state['answers']])}"
            )
            del _quiz_state[uid]
            await _edit(query, final, kb([("🔄 Try Again", "quiz_start"), ("📚 Learn More", "learn")], back="learn"))
        else:
            await _edit(query, result_text, kb([("➡️ Next Question", f"quiz_next_{uid[:8]}")], back="learn"))
        return

    if action.startswith("quiz_next_"):
        state = _quiz_state.get(uid)
        if state:
            await _send_quiz_question(query, uid)
        return

    if action == "quiz_history":
        history = await get_quiz_history(uid)
        if not history:
            await _edit(query, "📊 <b>Quiz History</b>\n\nNo quizzes taken yet.",
                        kb([("❓ Take Quiz", "quiz_start")], back="profile"))
            return
        text = "📊 <b>Quiz History</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for h in history:
            pct = h["score"] / h["total"] * 100
            emoji = "🏆" if pct >= 90 else "🎯" if pct >= 70 else "📚"
            text += f"{emoji} {h['score']}/{h['total']} ({pct:.0f}%)  <i>{h['taken_at'][:10]}</i>\n"
        await _edit(query, text, kb([("❓ Take Quiz", "quiz_start")], back="profile"))
        return

    # ── PORTFOLIO ─────────────────────────────────────────────────────────────
    if action == "portfolio":
        await _edit(query, "💼 <b>Portfolio</b>\n━━━━━━━━━━━━━━━━━━\n\nTrack and analyse your crypto holdings.", portfolio_keyboard())
        return

    if action == "portfolio_analyse":
        await query.edit_message_text("💼 Analysing portfolio...", parse_mode=ParseMode.HTML)
        try:
            holdings = await get_holdings(uid)
            if not holdings:
                await _edit(query, format_empty_portfolio_html(), portfolio_keyboard())
            else:
                text = await build_portfolio_analysis(holdings)
                await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=portfolio_keyboard())
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="portfolio"))
        return

    if action == "portfolio_list":
        try:
            holdings = await get_holdings(uid)
            text = format_holdings_list_html(holdings) if holdings else format_empty_portfolio_html()
            await _edit(query, text, portfolio_keyboard())
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="portfolio"))
        return

    if action == "portfolio_add_help":
        await _edit(query,
            "➕ <b>Add Holding</b>\n\n"
            "Send:\n<code>/add BTC 0.5 45000</code>\n<code>/add ETH 2 3200</code>\n\n"
            "Format: /add COIN AMOUNT BUY_PRICE",
            kb(back="portfolio"))
        return

    if action == "portfolio_remove_help":
        holdings = await get_holdings(uid)
        if not holdings:
            await _edit(query, "💼 Portfolio is empty.", kb(back="portfolio"))
            return
        text = "🗑 <b>Remove Holding</b>\n\n"
        for h in holdings:
            text += f"<b>#{h['id']}</b>  {h['symbol']}  {h['amount']}  @ ${h['buy_price']:,.2f}\n"
        text += "\nSend: <code>/remove ID</code>"
        await _edit(query, text, kb(back="portfolio"))
        return

    if action == "portfolio_health":
        await query.edit_message_text("🏥 Checking portfolio health...", parse_mode=ParseMode.HTML)
        try:
            holdings = await get_holdings(uid)
            if not holdings:
                await _edit(query, "💼 Add some holdings first.", kb(back="portfolio"))
                return
            text = await _build_portfolio_health(holdings)
            await _edit(query, text, kb([("📊 Full Analysis", "portfolio_analyse")], back="portfolio"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="portfolio"))
        return

    if action == "portfolio_rebalance":
        await query.edit_message_text("⚖️ Calculating rebalance suggestions...", parse_mode=ParseMode.HTML)
        try:
            holdings = await get_holdings(uid)
            if not holdings:
                await _edit(query, "💼 Add holdings first.", kb(back="portfolio"))
                return
            text = _build_rebalance_suggestion(holdings)
            await _edit(query, text, kb([("📊 Full Analysis", "portfolio_analyse")], back="portfolio"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="portfolio"))
        return

    if action == "portfolio_plan":
        await _edit(query,
            "📅 <b>Investment Plan</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<b>🟢 Conservative:</b>\n70% BTC + 20% ETH + 10% stable DCA monthly\n\n"
            "<b>🟡 Moderate:</b>\n50% BTC + 30% ETH + 20% top altcoins\n\n"
            "<b>🔴 Aggressive:</b>\n30% BTC + 20% ETH + 50% mid/small cap alts\n\n"
            "💡 Ask the <b>AI Coach</b> to create your personalised plan!",
            kb([("🤖 AI Coach", "coach_start")], back="portfolio"))
        return

    if action == "portfolio_clear":
        await _edit(query, "⚠️ <b>Clear Portfolio</b>\n\nThis will delete ALL holdings. Are you sure?",
                    kb([("✅ Yes, clear", "portfolio_clear_confirm"), ("❌ Cancel", "portfolio")], home=False))
        return

    if action == "portfolio_clear_confirm":
        await clear_portfolio(uid)
        await _edit(query, "✅ Portfolio cleared.", kb(back="portfolio"))
        return

    # ── RESEARCH ──────────────────────────────────────────────────────────────
    if action == "research":
        await _edit(query, "📰 <b>AI Research</b>\n━━━━━━━━━━━━━━━━━━\n\nDeep research on crypto markets and projects.", research_keyboard())
        return

    if action == "research_daily":
        await query.edit_message_text("📰 Fetching daily research...", parse_mode=ParseMode.HTML)
        try:
            news = await fetch_latest_news()
            fg = await fetch_fear_greed()
            text = _build_daily_research(news, fg)
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "research_daily")], back="research"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="research"))
        return

    if action == "research_coin_menu":
        await _edit(query, "🔍 <b>Coin Research</b>\n━━━━━━━━━━━━━━━━━━\n\nDeep dive into any cryptocurrency.", research_coin_keyboard())
        return

    if action == "research_coin_help":
        await _edit(query, "🔍 <b>Coin Research</b>\n\nJust type any coin ticker as a message and I'll research it!", kb(back="research_coin_menu"))
        return

    if action.startswith("research_") and action[9:].upper() in ("BTC", "ETH", "SOL", "LINK"):
        symbol = action[9:].upper()
        await query.edit_message_text(f"🔍 Researching {symbol}...", parse_mode=ParseMode.HTML)
        try:
            result = await run_token_deep_dive(symbol)
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", action)], back="research_coin_menu"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="research"))
        return

    if action in ("research_score_menu",):
        await _edit(query, "📊 <b>Research Score</b>\n\nSelect a coin:", research_coin_keyboard())
        return

    if action == "news":
        await query.edit_message_text("📰 Loading latest news...", parse_mode=ParseMode.HTML)
        try:
            news = await fetch_latest_news()
            text = format_morning_news(news) if news else "⚠️ No news available right now."
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "news")], back="research"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="research"))
        return

    if action == "weekly_report":
        await query.edit_message_text("📋 Building weekly report...", parse_mode=ParseMode.HTML)
        try:
            text = await build_weekly_report()
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                           reply_markup=kb([("🔄 Refresh", "weekly_report")], back="research"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="research"))
        return

    # ── TOOLS ─────────────────────────────────────────────────────────────────
    if action == "tools_menu":
        await _edit(query, "🧮 <b>Trading Tools</b>\n━━━━━━━━━━━━━━━━━━\n\nProfessional calculators for traders:", tools_keyboard())
        return

    TOOL_HELP = {
        "tool_possize": (
            "📏 <b>Position Size Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc possize ACCOUNT RISK% ENTRY STOP</code>\n\n"
            "Example:\n<code>/calc possize 10000 1 60000 58000</code>",
            "calc_possize_example",
        ),
        "tool_rr": (
            "🎯 <b>Risk:Reward Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc rr ENTRY STOP TP1 [TP2]</code>\n\n"
            "Example:\n<code>/calc rr 60000 58000 65000 70000</code>",
            "calc_rr_example",
        ),
        "tool_profit": (
            "💰 <b>Profit Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc profit ENTRY EXIT QTY [LEVERAGE]</code>\n\n"
            "Example:\n<code>/calc profit 60000 65000 0.1 1</code>",
            "calc_profit_example",
        ),
        "tool_dca_calc": (
            "📉 <b>DCA Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc dca PRICE1:AMT1 PRICE2:AMT2</code>\n\n"
            "Example:\n<code>/calc dca 60000:500 55000:500 50000:1000</code>",
            "calc_dca_example",
        ),
        "tool_compound": (
            "📈 <b>Compound Interest Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc compound PRINCIPAL RATE% PERIODS</code>\n\n"
            "Example:\n<code>/calc compound 1000 10 12</code>",
            "calc_compound_example",
        ),
        "tool_liq": (
            "💀 <b>Liquidation Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc liq ENTRY LEVERAGE [long/short]</code>\n\n"
            "Example:\n<code>/calc liq 60000 10 long</code>",
            "calc_liq_example",
        ),
        "tool_funding": (
            "💸 <b>Funding Fee Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc funding POSITION_USD RATE%</code>\n\n"
            "Example:\n<code>/calc funding 10000 0.01</code>",
            "calc_funding_example",
        ),
        "tool_fee": (
            "💳 <b>Trading Fee Calculator</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<code>/calc fee POSITION_USD [exchange]</code>\n\n"
            "Example:\n<code>/calc fee 10000 bybit</code>",
            "calc_fee_example",
        ),
    }
    if action in TOOL_HELP:
        text, example_cb = TOOL_HELP[action]
        await _edit(query, text, kb([(f"📊 Example", example_cb)], back="tools_menu"))
        return

    CALC_EXAMPLES = {
        "calc_possize_example": lambda: calc_position_size(10000, 1.0, 60000, 58000),
        "calc_rr_example": lambda: calc_risk_reward(60000, 58000, 65000, 70000),
        "calc_profit_example": lambda: calc_profit(60000, 65000, 0.1, 1.0),
        "calc_dca_example": lambda: calc_dca([(60000, 500), (55000, 500), (50000, 1000)]),
        "calc_compound_example": lambda: calc_compound(1000, 10, 12),
        "calc_liq_example": lambda: calc_liquidation(60000, 10, "long"),
        "calc_funding_example": lambda: calc_funding(10000, 0.01),
        "calc_fee_example": lambda: calc_fee(10000, "bybit"),
    }
    tool_back = {
        "calc_possize_example": "tool_possize", "calc_rr_example": "tool_rr",
        "calc_profit_example": "tool_profit", "calc_dca_example": "tool_dca_calc",
        "calc_compound_example": "tool_compound", "calc_liq_example": "tool_liq",
        "calc_funding_example": "tool_funding", "calc_fee_example": "tool_fee",
    }
    if action in CALC_EXAMPLES:
        result = CALC_EXAMPLES[action]()
        await _edit(query, result, kb(back=tool_back[action]))
        return

    # ── ALERTS ────────────────────────────────────────────────────────────────
    if action == "alerts":
        await _edit(query, "🔔 <b>Alerts & Plans</b>\n━━━━━━━━━━━━━━━━━━\n\nSet price alerts and DCA plans.", alerts_keyboard())
        return

    if action == "alerts_list":
        try:
            user_alerts = await get_active_alerts(uid)
            text = format_alerts_list(user_alerts) if user_alerts else \
                "🔔 <b>My Alerts</b>\n\nNo active alerts.\n\nUse /alert to create one."
            await _edit(query, text, kb([("🔄 Refresh", "alerts_list")], back="alerts"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="alerts"))
        return

    if action == "alerts_add_help":
        await _edit(query,
            "🔔 <b>Create Price Alert</b>\n\n"
            "Send:\n<code>/alert BTC above 70000</code>\n"
            "<code>/alert ETH below 3000</code>",
            kb(back="alerts"))
        return

    if action == "alerts_signals":
        await _edit(query,
            "📊 <b>Signal Alerts</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "Scheduled automated alerts:\n"
            "• 6:00 AM NPT — Morning news briefing\n"
            "• 8:00 AM NPT — Morning market analysis\n"
            "• 9:00 AM NPT — Best coin of the day\n"
            "• Sunday 10:00 AM NPT — Weekly report\n\n"
            "💡 Signals are pushed automatically to this chat!",
            kb(back="alerts"))
        return

    if action == "dca":
        try:
            plans = await get_dca_plans(uid)
            text = format_dca_plans(plans) if plans else \
                "📅 <b>DCA Planner</b>\n\nNo active plans.\n\nUse:\n<code>/dca BTC 50 weekly</code>"
            await _edit(query, text, kb([("🔄 Refresh", "dca"), ("➕ New Plan", "dca_help")], back="alerts"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="alerts"))
        return

    if action == "dca_help":
        await _edit(query,
            "📅 <b>DCA Planner</b>\n\n"
            "Send:\n<code>/dca BTC 50 weekly</code>\n"
            "<code>/dca ETH 100 monthly</code>\n"
            "<code>/dca SOL 25 daily</code>",
            kb(back="dca"))
        return

    # ── AI COACH ──────────────────────────────────────────────────────────────
    if action == "coach_menu":
        await _edit(query,
            "🤖 <b>AI Trading Coach</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "Ask me anything about trading.\n\n"
            "I explain concepts, analyse charts, review strategies, and help you become a better trader.",
            coach_keyboard())
        return

    if action == "coach_start":
        _coach_mode.add(uid)
        await _edit(query,
            "🤖 <b>AI Coach — Chat Mode</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "I'm ready! Ask me anything:\n\n"
            "• Should I buy BTC now?\n"
            "• Why is ETH dropping?\n"
            "• Explain RSI to me\n"
            "• Rate my trading strategy\n\n"
            "💬 <i>Just type your question!</i>\n\n"
            "<i>Tap Menu button to exit.</i>",
            kb([("🛑 Exit Coach", "coach_exit")], home=False))
        return

    if action == "coach_exit":
        _coach_mode.discard(uid)
        await _edit(query, home_text(), main_keyboard())
        return

    if action == "coach_clear":
        pool = await _get_pool_safe()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM coach_history WHERE chat_id=$1", uid)
        await _edit(query, "✅ Conversation history cleared.", coach_keyboard())
        return

    if action in ("coach_q_btc", "coach_q_port", "coach_q_rsi", "coach_q_plan"):
        questions = {
            "coach_q_btc": "Should I buy BTC right now? Give me a technical and fundamental analysis.",
            "coach_q_port": "What makes a well-diversified crypto portfolio? How should I allocate?",
            "coach_q_rsi": "Explain RSI indicator to me. How do I use it to find entry points?",
            "coach_q_plan": "Create a simple trading plan for a beginner with $1,000 capital.",
        }
        q = questions[action]
        await query.edit_message_text("🤖 Thinking...", parse_mode=ParseMode.HTML)
        history = await get_coach_history(uid)
        response = await ask_coach(q, history)
        await save_coach_message(uid, "user", q)
        await save_coach_message(uid, "assistant", response)
        await query.edit_message_text(
            f"💬 <b>You:</b> {q}\n\n🤖 <b>Coach:</b>\n{response}",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([("💬 Ask more", "coach_start")], back="coach_menu"))
        return

    # ── JOURNAL ───────────────────────────────────────────────────────────────
    if action == "journal":
        await _edit(query, "📊 <b>Trade Journal</b>\n━━━━━━━━━━━━━━━━━━\n\nRecord your trades and get AI analysis.", journal_keyboard())
        return

    if action == "journal_stats":
        try:
            stats = await get_journal_stats(uid)
            text = format_journal_stats(stats)
            await _edit(query, text, kb([("📋 Trades", "journal_list"), ("🔄 Refresh", "journal_stats")], back="journal"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="journal"))
        return

    if action == "journal_list":
        try:
            entries = await get_journal_entries(uid)
            text = format_journal_list(entries)
            await _edit(query, text, kb([("📊 Analysis", "journal_stats")], back="journal"))
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="journal"))
        return

    if action == "journal_add":
        await _edit(query,
            "➕ <b>Add Trade to Journal</b>\n\n"
            "<code>/journal BTC LONG 60000 65000 1000</code>\n\n"
            "Format: /journal COIN DIRECTION ENTRY EXIT [SIZE_USD]",
            kb(back="journal"))
        return

    if action == "journal_help":
        await _edit(query,
            "❓ <b>How to use the Journal</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Record a trade:</b>\n<code>/journal BTC LONG 60000 65000</code>\n\n"
            "<b>View analysis:</b>\nTap 📊 Analysis to see win rate, avg win/loss, and common mistakes.\n\n"
            "<b>Why journal?</b>\nJournaling is the #1 habit of profitable traders.",
            kb(back="journal"))
        return

    # ── CHALLENGES ────────────────────────────────────────────────────────────
    if action in ("challenges", "challenges_all"):
        await _edit(query, format_challenges_menu(), challenges_keyboard())
        return

    if action == "challenges_progress":
        try:
            active = await get_active_challenges(uid)
            completed = await get_completed_challenges(uid)
            text = "🏅 <b>My Challenge Progress</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            if active:
                text += "<b>Active:</b>\n"
                for ch in active:
                    info = ch.get("info", {})
                    pct = ch["progress"] / max(info.get("duration_days", 30), 1) * 100
                    text += f"  {info.get('emoji','🏆')} {info.get('name','')}\n"
                    text += f"  Day {ch['progress']}/{info.get('duration_days',30)}  ({pct:.0f}%)\n\n"
            else:
                text += "No active challenges.\n\n"
            if completed:
                text += f"<b>Completed:</b> {len(completed)} challenge(s) 🏆\n"
            await _edit(query, text, challenges_keyboard())
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="challenges"))
        return

    if action.startswith("ch_start_"):
        ch_id = action[9:]
        ch = CHALLENGES.get(ch_id)
        if not ch:
            await _edit(query, "❌ Challenge not found.", kb(back="challenges"))
            return
        success = await start_challenge(uid, ch_id)
        if success:
            text = (
                f"{ch['emoji']} <b>Challenge Started!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>{ch['name']}</b>\n\n{ch['description']}\n\n"
                f"<b>Duration:</b> {ch['duration_days']} days\n\n"
                f"<b>Daily tasks:</b>\n" +
                "".join(f"  ☐ {t}\n" for t in ch["tasks"]) +
                "\n💪 <i>Check in daily to track progress!</i>"
            )
        else:
            text = "⚠️ You already have this challenge active."
        await _edit(query, text, kb([("🏅 My Progress", "challenges_progress")], back="challenges"))
        return

    # ── PROFILE & SETTINGS ────────────────────────────────────────────────────
    if action == "profile":
        await _edit(query, "👤 <b>Profile & Settings</b>\n━━━━━━━━━━━━━━━━━━\n\nPersonalise your trading experience.", profile_keyboard())
        return

    if action == "profile_view":
        try:
            settings = await get_user_settings(uid)
            history = await get_quiz_history(uid)
            total_quiz = len(history)
            avg_score = sum(h["score"] / h["total"] * 100 for h in history) / total_quiz if history else 0
            active_ch = await get_active_challenges(uid)
            completed_ch = await get_completed_challenges(uid)
            text = (
                f"👤 <b>My Profile</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>ID:</b>           <code>{uid[:8]}...</code>\n"
                f"<b>Risk Profile:</b> {settings.get('risk_profile','moderate').capitalize()}\n"
                f"<b>Currency:</b>     {settings.get('currency','USD')}\n"
                f"<b>Timezone:</b>     {settings.get('timezone','Asia/Kathmandu')}\n\n"
                f"<b>📊 Stats:</b>\n"
                f"  Quizzes taken:      {total_quiz}\n"
                f"  Avg quiz score:     {avg_score:.0f}%\n"
                f"  Active challenges:  {len(active_ch)}\n"
                f"  Completed:          {len(completed_ch)}\n"
            )
            await _edit(query, text, profile_keyboard())
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="profile"))
        return

    if action == "settings":
        try:
            settings = await get_user_settings(uid)
            text = (
                f"⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Currency:</b>     {settings.get('currency','USD')}\n"
                f"<b>Timezone:</b>     {settings.get('timezone','Asia/Kathmandu')}\n"
                f"<b>Risk profile:</b> {settings.get('risk_profile','moderate')}\n"
                f"<b>AI style:</b>     {settings.get('ai_style','detailed')}\n"
                f"<b>Notifications:</b> {'On ✅' if settings.get('notifications',1) else 'Off ❌'}\n"
            )
            await _edit(query, text, settings_keyboard())
        except Exception as e:
            await _edit(query, f"❌ {e}", kb(back="profile"))
        return

    if action in ("set_currency", "set_timezone", "set_risk", "set_ai_style", "set_notifs"):
        options = {
            "set_currency": [("USD 🇺🇸", "cfg_currency_USD"), ("EUR 🇪🇺", "cfg_currency_EUR"), ("NPR 🇳🇵", "cfg_currency_NPR")],
            "set_timezone": [("Nepal (NPT)", "cfg_tz_Asia/Kathmandu"), ("UTC", "cfg_tz_UTC"), ("India (IST)", "cfg_tz_Asia/Kolkata")],
            "set_risk": [("Conservative 🟢", "cfg_risk_conservative"), ("Moderate 🟡", "cfg_risk_moderate"), ("Aggressive 🔴", "cfg_risk_aggressive")],
            "set_ai_style": [("Detailed 📚", "cfg_ai_detailed"), ("Concise ⚡", "cfg_ai_concise")],
            "set_notifs": [("On ✅", "cfg_notifs_1"), ("Off ❌", "cfg_notifs_0")],
        }
        labels = {
            "set_currency": "Select Currency", "set_timezone": "Select Timezone",
            "set_risk": "Select Risk Profile", "set_ai_style": "Select AI Style",
            "set_notifs": "Notifications",
        }
        opts = options[action]
        rows = [opts[i:i+2] for i in range(0, len(opts), 2)]
        await _edit(query, f"⚙️ <b>{labels[action]}</b>", kb(*rows, back="settings"))
        return

    if action.startswith("cfg_"):
        parts = action[4:].split("_", 1)
        setting_type, value = parts[0], (parts[1] if len(parts) > 1 else "")
        mapping = {"currency": "currency", "tz": "timezone", "risk": "risk_profile", "ai": "ai_style", "notifs": "notifications"}
        field = mapping.get(setting_type)
        if field:
            val = int(value) if setting_type == "notifs" else value
            await upsert_user_settings(uid, **{field: val})
            await _edit(query, f"✅ <b>{field.replace('_',' ').capitalize()}</b> updated to <code>{value}</code>", kb(back="settings"))
        return

    if action == "achievements":
        completed = await get_completed_challenges(uid)
        history = await get_quiz_history(uid)
        entries = await get_journal_entries(uid)
        text = "🏆 <b>Achievements</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        text += f"📊 Trades journaled: {len(entries)}\n"
        text += f"❓ Quizzes completed: {len(history)}\n"
        text += f"🏅 Challenges completed: {len(completed)}\n\n"
        if len(entries) >= 10:
            text += "🥉 <b>Journaler</b> — 10+ trades recorded\n"
        if len(history) >= 5:
            text += "📚 <b>Student</b> — 5+ quizzes completed\n"
        if completed:
            text += "🏆 <b>Champion</b> — Completed a challenge\n"
        await _edit(query, text, kb(back="profile"))
        return

    # ── CHART ─────────────────────────────────────────────────────────────────
    if action.startswith("chart_"):
        symbol = action[6:].upper()
        if symbol == "MENU":
            coins = [("BTC", "chart_btc"), ("ETH", "chart_eth"), ("SOL", "chart_sol"), ("BNB", "chart_bnb"), ("XRP", "chart_xrp")]
            await _edit(query, "📉 <b>Chart</b>\n\nSelect a coin:", kb(*[coins[i:i+2] for i in range(0, len(coins), 2)], back="menu"))
        else:
            await query.edit_message_text(f"📉 Generating {symbol} chart...", parse_mode=ParseMode.HTML)
            try:
                chart_buf, caption = await generate_chart(f"{symbol}/USDT")
                await query.message.reply_photo(chart_buf, caption=caption, parse_mode=ParseMode.HTML)
                await _edit(query, f"📉 <b>{symbol} Chart</b>\n(See above)", kb([("🔄 Refresh", action)], back="market"))
            except Exception as e:
                await _edit(query, f"❌ Chart error: {e}", kb(back="market"))
        return

    # Fallback
    await _edit(query, "❓ Unknown action. Returning to menu.", main_keyboard())


# ═══════════════════════════════════════════════════════════════════════════════
# QUIZ HELPER
# ═══════════════════════════════════════════════════════════════════════════════

async def _send_quiz_question(query, uid: str):
    state = _quiz_state.get(uid)
    if not state:
        return
    q = state["questions"][state["index"]]
    total = len(state["questions"])
    idx = state["index"]
    text = f"❓ <b>Question {idx + 1}/{total}</b>\n━━━━━━━━━━━━━━━━━━\n\n{q['q']}\n"
    opts = [(q["options"][i], f"quiz_ans_{i}") for i in range(len(q["options"]))]
    rows = [opts[i:i+2] for i in range(0, len(opts), 2)]
    await _edit(query, text, kb(*rows, home=False))


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    uid = _user_id(update)
    text = update.message.text.strip()

    if text.startswith("/"):
        return

    # AI Coach mode
    if uid in _coach_mode:
        msg = await update.message.reply_text("🤖 Thinking...", parse_mode=ParseMode.HTML)
        history = await get_coach_history(uid)
        response = await ask_coach(text, history)
        await save_coach_message(uid, "user", text)
        await save_coach_message(uid, "assistant", response)
        await msg.edit_text(
            f"🤖 <b>Coach:</b>\n\n{response}",
            parse_mode=ParseMode.HTML,
            reply_markup=kb([("🛑 Exit Coach", "coach_exit"), ("🏠 Menu", "menu")], home=False),
        )
        return

    # Coin lookup
    ticker = text.upper().strip()
    if 2 <= len(ticker) <= 8 and ticker.isalpha():
        msg = await update.message.reply_text(f"🔍 Scanning {ticker}...", parse_mode=ParseMode.HTML)
        try:
            result = await run_token_deep_dive(ticker)
            await msg.edit_text(result, parse_mode=ParseMode.HTML,
                                 reply_markup=kb(
                                     [("🔄 Refresh", f"scan_{ticker}"), ("📊 Chart", f"chart_{ticker.lower()}")],
                                     back="coin_scanner"))
        except Exception:
            await msg.edit_text(
                f"❓ I don't recognise <b>{ticker}</b> as a coin.\n\nTap 🤖 AI Coach to ask me anything!",
                parse_mode=ParseMode.HTML,
                reply_markup=kb([("🤖 Ask AI Coach", "coach_start")], back="menu"),
            )
        return

    # Default: suggest AI coach
    await update.message.reply_text(
        "💬 Tap <b>🤖 AI Coach</b> to chat, or type a coin ticker (BTC, ETH, SOL) for analysis.",
        parse_mode=ParseMode.HTML,
        reply_markup=kb([("🤖 AI Coach", "coach_start"), ("🏠 Menu", "menu")], home=False),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DATA BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _build_live_market(action: str) -> str:
    label_map = {
        "live_gainers": ("🚀 Top Gainers", "gainers"),
        "live_losers": ("📉 Top Losers", "losers"),
        "live_trending": ("🔥 Trending Coins", "trending"),
        "live_new": ("🆕 New Listings", "new"),
        "live_volume": ("💰 Highest Volume", "volume"),
        "live_volatile": ("⚡ Most Volatile", "volatile"),
        "live_whale_buy": ("🐋 Whales Buying", "whale_buy"),
        "live_whale_sell": ("🐻 Whales Selling", "whale_sell"),
    }
    title, mode = label_map.get(action, ("📊 Market", ""))

    tickers = []
    for sym in config.WATCHLIST:
        try:
            t = await fetch_ticker(sym)
            if t:
                tickers.append(t)
        except Exception:
            pass

    if not tickers:
        return "⚠️ Could not fetch market data. Try again."

    if mode in ("gainers", "volatile"):
        sorted_t = sorted(tickers, key=lambda x: x.get("percentage", 0), reverse=True)
    elif mode == "losers":
        sorted_t = sorted(tickers, key=lambda x: x.get("percentage", 0))
    else:
        sorted_t = sorted(tickers, key=lambda x: x.get("quoteVolume", 0), reverse=True)

    text = f"{title}\n━━━━━━━━━━━━━━━━━━\n<i>{npt_now()}</i>\n\n"
    for t in sorted_t[:8]:
        sym = t.get("symbol", "").replace("/USDT", "")
        price = t.get("last", 0)
        change = t.get("percentage", 0)
        vol = t.get("quoteVolume", 0)
        emoji = "🟢" if change > 0 else "🔴"
        vol_str = f"${vol/1_000_000:.1f}M" if vol > 1_000_000 else f"${vol:,.0f}"
        text += f"{emoji} <b>{sym}</b>  <code>${fp(price)}</code>  <code>{change:+.2f}%</code>  <i>Vol: {vol_str}</i>\n"

    text += f"\n<i>Data: {config.EXCHANGE.upper()} · {npt_now()}</i>"
    return text


async def _build_fear_greed() -> str:
    data = await fetch_fear_greed()
    if not data:
        return "⚠️ Could not fetch Fear & Greed data."
    val = data.get("value", 50)
    classification = data.get("value_classification", "Neutral")
    emoji = "😱" if val < 25 else "😨" if val < 40 else "😐" if val < 60 else "😁" if val < 80 else "🤑"
    bar = "▓" * (val // 5) + "░" * (20 - val // 5)
    return (
        f"😱 <b>Fear & Greed Index</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{classification}</b>  {emoji}\n\n"
        f"<code>{bar}</code>\n<code>{val}/100</code>\n\n"
        f"<b>0–24:</b>  Extreme Fear 😱\n"
        f"<b>25–49:</b> Fear 😨\n"
        f"<b>50–74:</b> Greed 😁\n"
        f"<b>75–100:</b> Extreme Greed 🤑\n\n"
        f"<i>High fear = potential buy opportunity.\nHigh greed = consider taking profits.</i>\n\n"
        f"<i>Updated: {npt_now()}</i>"
    )


def _build_daily_research(news: list, fg: dict) -> str:
    val = fg.get("value", 50) if fg else 50
    cls = fg.get("value_classification", "Neutral") if fg else "N/A"
    emoji = "😱" if val < 25 else "😨" if val < 40 else "😐" if val < 60 else "😁" if val < 80 else "🤑"
    text = (
        f"📰 <b>Daily Research</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"<i>{npt_now()}</i>\n\n"
        f"<b>Fear & Greed:</b> {cls} {emoji} ({val}/100)\n\n"
        f"<b>Latest News:</b>\n"
    )
    for n in (news[:5] if news else []):
        text += f"• {n.get('title', '')[:80]}\n"
    if not news:
        text += "• No news available right now.\n"
    text += "\n<b>Market Tip:</b>\n" + random.choice([
        "📐 Always identify support and resistance before entering a trade.",
        "🛡 Risk management saves accounts. Never skip your stop loss.",
        "📊 Volume confirms price moves. No volume = weak move.",
        "🧘 The best trade is sometimes no trade. Patience is profitable.",
        "💡 Trade the setup, not the hype. Let price come to your level.",
        "🎯 A 1:3 risk:reward trade only needs 25% win rate to profit.",
    ])
    return text


async def _build_portfolio_health(holdings: list) -> str:
    total = len(holdings)
    if total == 0:
        return "💼 Portfolio empty."
    symbols = [h["symbol"] for h in holdings]
    score = 100
    issues = []
    if total < 3:
        score -= 20
        issues.append("⚠️ Too concentrated — add more coins")
    if total > 15:
        score -= 15
        issues.append("⚠️ Too many positions — consider consolidating")
    if symbols.count("BTC") / total > 0.6:
        score -= 10
        issues.append("⚠️ Heavy BTC allocation")
    grade = "🟢 Healthy" if score >= 80 else "🟡 Fair" if score >= 60 else "🔴 Needs attention"
    text = (
        f"🏥 <b>Portfolio Health Check</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Health score:</b>  <code>{score}/100</code>  {grade}\n"
        f"<b>Holdings:</b>      <code>{total}</code>\n"
        f"<b>Diversification:</b> {'Good' if total >= 5 else 'Low'}\n\n"
    )
    if issues:
        text += "<b>Issues:</b>\n" + "\n".join(issues) + "\n\n"
    else:
        text += "✅ No major issues found!\n\n"
    text += (
        "<b>Recommended allocation:</b>\n"
        "🔵 BTC: 40–50%\n🟣 ETH: 20–30%\n🟡 Other top coins: 20–30%\n🟢 Small cap: 5–10% max"
    )
    return text


def _build_rebalance_suggestion(holdings: list) -> str:
    if not holdings:
        return "💼 Portfolio empty."
    symbols = set(h["symbol"] for h in holdings)
    text = (
        f"⚖️ <b>Rebalance Suggestion</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Current holdings:</b> {', '.join(symbols)}\n\n"
        f"<b>Suggested target allocation:</b>\n"
    )
    for coin, alloc, note in [("BTC", "40%", "🔵 Core"), ("ETH", "25%", "🟣 Blue chip"), ("SOL", "15%", "🟡 Growth"), ("Others", "20%", "🟢 Diversification")]:
        in_p = "✅" if coin in symbols or coin == "Others" else "⬜"
        text += f"  {in_p} <b>{coin}</b>  {alloc}  <i>{note}</i>\n"
    text += "\n💡 <i>Ask the AI Coach for a personalised rebalance plan!</i>"
    return text


async def _get_pool_safe():
    try:
        from utils.db import _get_pool
        return await _get_pool()
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULED TASKS
# ═══════════════════════════════════════════════════════════════════════════════

async def scheduled_morning_news(app: Application):
    try:
        await run_morning_news(app.bot, config.TELEGRAM_CHAT_ID)
    except Exception as e:
        logger.error("Morning news error: %s", e)


async def scheduled_morning_analytics(app: Application):
    try:
        await run_morning_analytics(app.bot, config.TELEGRAM_CHAT_ID, config.WATCHLIST)
    except Exception as e:
        logger.error("Morning analytics error: %s", e)


async def scheduled_alert_check(app: Application):
    try:
        all_alerts = await get_active_alerts()
        if all_alerts:
            await check_alerts(app.bot, all_alerts)
    except Exception as e:
        logger.error("Alert check error: %s", e)


async def scheduled_dca_check(app: Application):
    try:
        await check_due_dca(app.bot)
    except Exception as e:
        logger.error("DCA check error: %s", e)


async def scheduled_weekly_report(app: Application):
    try:
        text = await build_weekly_report()
        await app.bot.send_message(config.TELEGRAM_CHAT_ID, text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error("Weekly report error: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def post_init(app: Application):
    await init_db()
    scheduler.add_job(scheduled_morning_news, "cron",
                      hour=config.MORNING_NEWS_UTC_H, minute=config.MORNING_NEWS_UTC_M, args=[app])
    scheduler.add_job(scheduled_morning_analytics, "cron",
                      hour=config.MORNING_SCAN_UTC_H, minute=config.MORNING_SCAN_UTC_M, args=[app])
    scheduler.add_job(scheduled_alert_check, "interval", minutes=5, args=[app])
    scheduler.add_job(scheduled_dca_check, "interval", minutes=30, args=[app])
    scheduler.add_job(scheduled_weekly_report, "cron", day_of_week="sun", hour=4, minute=15, args=[app])
    scheduler.start()
    logger.info("DB initialised, scheduler started")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    import certifi
    import ssl
    from telegram.request import HTTPXRequest

    request = HTTPXRequest(connection_pool_size=8)
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .request(request)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("delalert", cmd_delalert))
    app.add_handler(CommandHandler("dca", cmd_dca))
    app.add_handler(CommandHandler("canceldca", cmd_canceldca))
    app.add_handler(CommandHandler("add", cmd_addholding))
    app.add_handler(CommandHandler("remove", cmd_removeholding))
    app.add_handler(CommandHandler("token", cmd_token))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("calc", cmd_calc))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("🤖 Trading AI Assistant started.")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
