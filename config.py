import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
WEBAPP_URL         = os.getenv("WEBAPP_URL", "")

ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")

# Exchange — bybit works globally, no geo-restrictions
# Alternatives: kucoin, okx, gate
EXCHANGE  = os.getenv("EXCHANGE", "bybit")
WATCHLIST = os.getenv("WATCHLIST", "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT").split(",")

# Nepal Standard Time = UTC+5:45
# Scheduled push times (stored as UTC hour, minute)
MORNING_NEWS_UTC_H  = 0   # 00:15 UTC = 6:00 AM NPT
MORNING_NEWS_UTC_M  = 15
MORNING_SCAN_UTC_H  = 2   # 02:15 UTC = 8:00 AM NPT
MORNING_SCAN_UTC_M  = 15

# Signal settings
COMPOSITE_THRESHOLD  = 0.65
TA_MIN_THRESHOLD     = 0.45
SIGNAL_EXPIRY_MINUTES = 45

# Score weights
W_TA        = 0.60
W_NEWS      = 0.25
W_SENTIMENT = 0.15

# Macro lockout windows (minutes)
MACRO_LOCKOUT_BEFORE = 30
MACRO_LOCKOUT_AFTER  = 60
