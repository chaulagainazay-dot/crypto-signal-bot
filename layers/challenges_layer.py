"""Challenge mode — trading discipline and learning challenges."""
import logging
from datetime import datetime, timezone, timedelta
from utils.db import _get_pool

log = logging.getLogger(__name__)

CHALLENGES = {
    "discipline_30": {
        "id": "discipline_30",
        "name": "30-Day Discipline Challenge",
        "emoji": "⚔️",
        "description": "Follow your trading plan for 30 consecutive days without breaking any rules.",
        "duration_days": 30,
        "tasks": [
            "Only take setups that match ALL your criteria",
            "Never exceed 2% risk per trade",
            "Log every trade in your journal",
            "Stop trading after hitting daily loss limit",
            "Never move stop loss against you",
        ],
    },
    "no_fomo": {
        "id": "no_fomo",
        "name": "No FOMO Challenge",
        "emoji": "🧘",
        "description": "Go 14 days without entering a trade out of FOMO. Only take planned setups.",
        "duration_days": 14,
        "tasks": [
            "Wait for price to come to your level (don't chase)",
            "Never buy after a 10%+ pump",
            "Plan entries before the market opens",
            "If you miss a setup, move on — don't chase",
        ],
    },
    "risk_mgmt": {
        "id": "risk_mgmt",
        "name": "Risk Management Challenge",
        "emoji": "🛡",
        "description": "Perfect risk management for 21 days. Never risk more than 1% per trade.",
        "duration_days": 21,
        "tasks": [
            "Calculate position size using the formula every trade",
            "Always set stop loss BEFORE entering",
            "Maximum 1% risk per trade",
            "Maximum 3% total open risk at any time",
            "Use /tools position calculator for every trade",
        ],
    },
    "learning_streak": {
        "id": "learning_streak",
        "name": "7-Day Learning Streak",
        "emoji": "📚",
        "description": "Complete one lesson in Learn Trading every day for 7 days.",
        "duration_days": 7,
        "tasks": [
            "Read one lesson per day",
            "Take the daily quiz",
            "Score 7/10 or higher on the quiz",
        ],
    },
    "quiz_streak": {
        "id": "quiz_streak",
        "name": "Quiz Master",
        "emoji": "🏆",
        "description": "Score 8/10 or higher on the trading quiz 5 days in a row.",
        "duration_days": 5,
        "tasks": [
            "Take the daily quiz every day",
            "Score 8/10 or higher",
            "Read the explanation for every wrong answer",
        ],
    },
}


async def start_challenge(chat_id: str, challenge_id: str) -> bool:
    if challenge_id not in CHALLENGES:
        return False
    pool = await _get_pool()
    ch = CHALLENGES[challenge_id]
    expires = (datetime.now(timezone.utc) + timedelta(days=ch["duration_days"])).isoformat()
    async with pool.acquire() as conn:
        # Check if already active
        existing = await conn.fetchrow(
            "SELECT id FROM user_challenges WHERE chat_id=$1 AND challenge_id=$2 AND completed=0",
            chat_id, challenge_id)
        if existing:
            return False
        await conn.execute("""
            INSERT INTO user_challenges (chat_id, challenge_id, started_at, expires_at, progress, completed)
            VALUES ($1,$2,$3,$4,$5,0)""",
            chat_id, challenge_id,
            datetime.now(timezone.utc).isoformat(), expires, 0)
    return True


async def get_active_challenges(chat_id: str) -> list[dict]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM user_challenges WHERE chat_id=$1 AND completed=0 ORDER BY started_at DESC",
            chat_id)
    results = []
    for r in rows:
        d = dict(r)
        d["info"] = CHALLENGES.get(d["challenge_id"], {})
        results.append(d)
    return results


async def get_completed_challenges(chat_id: str) -> list[dict]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM user_challenges WHERE chat_id=$1 AND completed=1 ORDER BY started_at DESC",
            chat_id)
    return [dict(r) for r in rows]


async def check_in_challenge(chat_id: str, challenge_id: str) -> dict:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM user_challenges WHERE chat_id=$1 AND challenge_id=$2 AND completed=0",
            chat_id, challenge_id)
        if not row:
            return {"error": "Challenge not active"}

        ch = CHALLENGES.get(challenge_id, {})
        new_progress = row["progress"] + 1
        completed = new_progress >= ch.get("duration_days", 30)

        await conn.execute(
            "UPDATE user_challenges SET progress=$1, completed=$2 WHERE id=$3",
            new_progress, 1 if completed else 0, row["id"])

        return {
            "progress": new_progress,
            "total": ch.get("duration_days", 30),
            "completed": completed,
            "name": ch.get("name", ""),
        }


def format_challenges_menu() -> str:
    text = "🏆 <b>Challenge Mode</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    text += "Complete challenges to build discipline and skill.\n\n"
    for ch in CHALLENGES.values():
        text += (
            f"{ch['emoji']} <b>{ch['name']}</b>\n"
            f"   {ch['description']}\n"
            f"   <i>{ch['duration_days']} days</i>\n\n"
        )
    return text
