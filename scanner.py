"""
Scanner — runs the 5-layer pipeline.
Called only on:
  1. Scheduled 8 AM NPT morning analytics push
  2. Manual button tap (Market Scan)
No continuous background polling.
"""
import asyncio
import logging
from typing import Optional

import aiohttp
from tqdm import tqdm

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver)
    return aiohttp.ClientSession(connector=connector)
import anthropic
from telegram import Bot

import config
import state_manager
from layers.l1_data import check_macro_lockout, fetch_latest_news, fetch_fear_greed
from layers.l2_technical import analyze, fetch_ticker
from layers.l3_signal import evaluate_asset
from layers.l4_risk import gate
from layers.l5_delivery import (
    deliver_signal, format_morning_analytics,
    format_morning_news, push,
)
from utils.db import log_scan

logger = logging.getLogger(__name__)


async def run_morning_news(bot: Bot):
    """6:00 AM NPT — push news brief to configured chat."""
    logger.info("Running morning news push (6 AM NPT)")
    try:
        news  = await fetch_latest_news(limit=6)
        fg    = await fetch_fear_greed()

        # Quick price changes for BTC / ETH
        async with _make_session() as _:
            btc_t = await fetch_ticker("BTC/USDT")
            eth_t = await fetch_ticker("ETH/USDT")

        # Regime label based on fear/greed
        fg_val = fg["value"]
        if fg_val <= 25:
            regime_label = "Defensive — BTC/ETH only, tighter stops"
        elif fg_val <= 45:
            regime_label = "Cautious — selective setups only"
        elif fg_val <= 55:
            regime_label = "Neutral — follow confirmation"
        elif fg_val <= 75:
            regime_label = "Constructive — standard setups valid"
        else:
            regime_label = "Euphoric — reduce size, be contrarian"

        text = format_morning_news(
            news_items   = news,
            fg           = fg,
            btc_change   = btc_t["change_pct"],
            eth_change   = eth_t["change_pct"],
            regime_label = regime_label,
        )
        await push(bot, text)
    except Exception as e:
        logger.error(f"Morning news push failed: {e}", exc_info=True)


async def run_morning_analytics(bot: Bot):
    """8:00 AM NPT — full market analytics + signals."""
    logger.info("Running morning analytics (8 AM NPT)")

    anthropic_client = None
    if config.ANTHROPIC_API_KEY:
        anthropic_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

    asset_rows   = []
    signals_sent = 0

    async with _make_session() as session:
        if await check_macro_lockout(session):
            await push(bot, "⚠️ Morning analytics delayed — macro event lockout active.")
            return

        for asset in tqdm(config.WATCHLIST, desc="Morning scan", unit="coin"):
            await asyncio.sleep(0.2)  # 0.2s between coins — stay within free-tier rate limits
            try:
                ticker = await fetch_ticker(asset)
                ta     = await analyze(asset)

                # Simple bias label
                if ta.ta_score >= 0.45:
                    bias = "Bullish → watch for long setup"
                elif ta.ta_score <= -0.45:
                    bias = "Bearish → no long entries"
                else:
                    bias = "Neutral → wait"

                # Short note
                if ta.regime == "chaotic":
                    note = "Chaotic regime — standing down"
                elif ta.rsi > 70:
                    note = f"RSI {ta.rsi:.0f} — overbought, avoid chasing"
                elif ta.rsi < 32:
                    note = f"RSI {ta.rsi:.0f} — oversold, bounce candidate"
                elif abs(ta.price - ta.ema21) / ta.ema21 < 0.005:
                    note = f"Sitting on EMA21 — key decision zone"
                else:
                    note = f"EMA21 {_fmt(ta.ema21)} · RSI {ta.rsi:.0f}"

                asset_rows.append({
                    "asset":      asset,
                    "price":      ticker["price"] or ta.price,
                    "high_24h":   ticker["high_24h"],
                    "low_24h":    ticker["low_24h"],
                    "change_pct": ticker["change_pct"],
                    "bias":       bias,
                    "note":       note,
                })

                # Check for signals
                signal = await evaluate_asset(ta, session, anthropic_client)
                if signal:
                    approved, reason, enriched = await gate(signal)
                    if approved:
                        entry_mid = (enriched["entry_low"] + enriched["entry_high"]) / 2
                        if state_manager.is_new_signal(asset, enriched["direction"], entry_mid):
                            state_manager.register_signal(asset, enriched["direction"], entry_mid)
                            await deliver_signal(bot, enriched)
                            signals_sent += 1

            except Exception as e:
                logger.error(f"Analytics error for {asset}: {e}")
                continue

    # Determine top watch and avoid note
    best = sorted(asset_rows, key=lambda r: abs(r["change_pct"]), reverse=True)
    top_watch  = best[0]["asset"].replace("/USDT","") if best else "—"
    avoid_note = "Altcoins in current fear regime" if True else "—"

    text = format_morning_analytics(
        asset_rows = asset_rows,
        top_watch  = top_watch,
        avoid_note = avoid_note,
    )
    await push(bot, text)
    await log_scan(len(config.WATCHLIST), signals_sent, "morning_analytics")

    if anthropic_client:
        await anthropic_client.close()


async def run_manual_scan(bot: Bot, notify_chat_id: str) -> tuple[int, int]:
    """Manual scan triggered by button tap. Returns (scanned, signals)."""
    signals_sent = 0
    scanned = 0

    anthropic_client = None
    if config.ANTHROPIC_API_KEY:
        anthropic_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

    async with _make_session() as session:
        for asset in tqdm(config.WATCHLIST, desc="Manual scan", unit="coin"):
            await asyncio.sleep(0.2)  # 0.2s between coins — stay within free-tier rate limits
            try:
                ta = await analyze(asset)
                scanned += 1
                signal = await evaluate_asset(ta, session, anthropic_client)
                if signal:
                    approved, reason, enriched = await gate(signal)
                    if approved:
                        entry_mid = (enriched["entry_low"] + enriched["entry_high"]) / 2
                        if state_manager.is_new_signal(asset, enriched["direction"], entry_mid):
                            state_manager.register_signal(asset, enriched["direction"], entry_mid)
                            await deliver_signal(bot, enriched, notify_chat_id)
                            signals_sent += 1
            except Exception as e:
                logger.error(f"Scan error {asset}: {e}")

    await log_scan(scanned, signals_sent, "manual")
    if anthropic_client:
        await anthropic_client.close()
    return scanned, signals_sent


def _fmt(price: float) -> str:
    if price >= 10000: return f"${price:,.0f}"
    if price >= 100:   return f"${price:,.1f}"
    if price >= 1:     return f"${price:,.3f}"
    return f"${price:.5f}"
