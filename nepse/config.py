import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID   = os.getenv("CHAT_ID", "")

BASE_DIR  = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Merolagani API base
ML_BASE = "https://merolagani.com/handlers/webrequesthandler.ashx"

# NEPSE market hours: Sun–Thu, 11:00–15:00 NPT (UTC+5:45 → UTC 05:15–09:15)
MARKET_OPEN_UTC  = (5, 15)   # 11:00 NPT
MARKET_CLOSE_UTC = (9, 15)   # 15:00 NPT
MARKET_DAYS      = {6, 0, 1, 2, 3}  # Sun=6, Mon=0, Tue=1, Wed=2, Thu=3

# Circuit breaker
CIRCUIT_LIMIT_PCT = 10.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://merolagani.com/",
}
