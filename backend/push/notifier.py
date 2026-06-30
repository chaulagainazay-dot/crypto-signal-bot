"""
HCG AI Crypto Trading Bot - Push Notifier
Proactively sends Telegram messages to users
"""

from typing import Dict, List, Optional


class PushNotifier:
    def __init__(self, bot):
        self.bot = bot

    async def send_high_confidence_signal(self, signal: Dict, user_id: int):
        """Only fires for confidence >= 85"""
        if signal.get('confidence', 0) < 85:
            return

        entry = signal.get('entry', signal.get('price', 0))
        rr    = signal.get('risk_reward', 0)

        msg = (
            f"🚨 <b>HIGH CONFIDENCE SIGNAL</b>\n\n"
            f"<b>{signal['symbol']}</b> {signal['action']}\n"
            f"Confidence: <b>{signal['confidence']}%</b>\n\n"
            f"Entry:  ${entry:,.4f}\n"
            f"Stop:   ${signal.get('stop', 'N/A')}\n"
            f"Target: ${signal.get('target', 'N/A')}\n\n"
            f"R:R: 1:{rr:.1f}\n"
            f"Expected Hold: {signal.get('expected_hold', 'N/A')}\n\n"
            f"Why:\n"
        )
        for reason in signal.get('reasons', [])[:3]:
            msg += f"• {reason}\n"
        msg += "\n⚠️ <i>Educational only. Not financial advice.</i>"

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📊 Analysis",  callback_data=f"analysis:{signal['symbol']}"),
            InlineKeyboardButton("🔔 Set Alert", callback_data=f"alert:{signal['symbol']}"),
            InlineKeyboardButton("🤖 Mentor",    callback_data=f"mentor:{signal['symbol']}"),
        ]])

        await self.bot.send_message(
            chat_id=user_id, text=msg,
            parse_mode='HTML', reply_markup=keyboard,
        )

    async def send_daily_brief(self, user_id: int, brief: Dict):
        msg = (
            f"☀️ <b>Good Morning! 30-second brief:</b>\n\n"
            f"₿ BTC: {brief.get('btc_sentiment', 'Neutral')}\n"
            f"Ξ ETH: {brief.get('eth_sentiment', 'Neutral')}\n"
            f"🌐 Alts: {brief.get('alt_sentiment', 'Neutral')}\n\n"
            f"⚡ Today: {brief.get('top_event', 'No major events')}\n\n"
            f"<b>Key Levels:</b>\n"
        )
        for asset, level in brief.get('key_levels', {}).items():
            msg += f"  {asset}: ${level}\n"
        msg += "\nHave a great trading day! 🎯"
        await self.bot.send_message(chat_id=user_id, text=msg, parse_mode='HTML')

    async def send_price_alert(self, user_id: int, alert: Dict, current_price: float):
        direction = alert.get('direction', '')
        emoji = '🔴' if direction == 'below' else '🟢'
        msg = (
            f"{emoji} <b>PRICE ALERT TRIGGERED</b>\n\n"
            f"<b>{alert['symbol']}</b> reached your target!\n\n"
            f"Alert: {direction} ${alert['target_price']:,.4f}\n"
            f"Current: ${current_price:,.4f}\n\n"
            f"⚠️ <i>Educational only. Not financial advice.</i>"
        )
        await self.bot.send_message(chat_id=user_id, text=msg, parse_mode='HTML')

    async def send_whale_alert(self, user_id: int, whale: Dict):
        msg = (
            f"🐋 <b>WHALE ACTIVITY DETECTED</b>\n\n"
            f"{whale.get('entity', 'Unknown')} "
            f"{whale.get('action', 'moved')} "
            f"{whale.get('amount', 0):,} {whale.get('symbol', 'BTC')}\n"
            f"Value: ${whale.get('value_usd_m', 0)}M\n"
            f"Time: {whale.get('time', 'just now')}"
        )
        await self.bot.send_message(chat_id=user_id, text=msg, parse_mode='HTML')

    async def broadcast(self, user_ids: List[int], message: str):
        """Send same message to multiple users"""
        for uid in user_ids:
            try:
                await self.bot.send_message(chat_id=uid, text=message, parse_mode='HTML')
            except Exception as e:
                print(f"[PushNotifier] failed to send to {uid}: {e}")
