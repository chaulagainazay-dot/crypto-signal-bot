"""Database layer — PostgreSQL via asyncpg (Supabase)."""
import asyncpg
import json
import os
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL", "")
_pool = None


async def _get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set.")
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5, statement_cache_size=0)
    return _pool


async def init_db():
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id SERIAL PRIMARY KEY, created_at TEXT NOT NULL, asset TEXT NOT NULL,
                direction TEXT NOT NULL, entry_low REAL, entry_high REAL, stop_loss REAL,
                tp1 REAL, tp2 REAL, position_size_usd REAL, composite_score REAL,
                ta_score REAL, news_score REAL, sentiment_score REAL, reasoning TEXT,
                expires_at TEXT, outcome TEXT DEFAULT 'pending', closed_at TEXT,
                close_price REAL, pnl_pct REAL)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_pnl (
                id SERIAL PRIMARY KEY, date TEXT NOT NULL UNIQUE,
                pnl_pct REAL DEFAULT 0.0, trade_count INTEGER DEFAULT 0, halted INTEGER DEFAULT 0)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id SERIAL PRIMARY KEY, scanned_at TEXT NOT NULL,
                assets_scanned INTEGER, signals_issued INTEGER, notes TEXT)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL, symbol TEXT NOT NULL,
                condition TEXT NOT NULL, target_price REAL NOT NULL, created_at TEXT NOT NULL,
                triggered INTEGER DEFAULT 0, triggered_at TEXT)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS dca_plans (
                id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL, symbol TEXT NOT NULL,
                amount_usd REAL NOT NULL, frequency TEXT NOT NULL, next_trigger_utc TEXT NOT NULL,
                active INTEGER DEFAULT 1, created_at TEXT NOT NULL, executions INTEGER DEFAULT 0)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS whale_picks (
                id SERIAL PRIMARY KEY, date TEXT NOT NULL, symbol TEXT NOT NULL,
                price_at_pick REAL, score REAL, signals TEXT, created_at TEXT NOT NULL)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL, symbol TEXT NOT NULL,
                amount REAL NOT NULL, buy_price REAL NOT NULL, added_at TEXT NOT NULL, note TEXT)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_journal (
                id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL, coin TEXT NOT NULL,
                direction TEXT NOT NULL, entry_price REAL NOT NULL, exit_price REAL NOT NULL,
                size_usd REAL NOT NULL DEFAULT 0, pnl_pct REAL NOT NULL, pnl_usd REAL NOT NULL DEFAULT 0,
                emotion TEXT, mistakes TEXT, lessons TEXT,
                traded_at TEXT NOT NULL)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_challenges (
                id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL, challenge_id TEXT NOT NULL,
                started_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                progress INTEGER DEFAULT 0, completed INTEGER DEFAULT 0)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                chat_id TEXT PRIMARY KEY, language TEXT DEFAULT 'en',
                timezone TEXT DEFAULT 'Asia/Kathmandu', currency TEXT DEFAULT 'USD',
                risk_profile TEXT DEFAULT 'moderate',
                ai_style TEXT DEFAULT 'detailed', notifications INTEGER DEFAULT 1,
                updated_at TEXT NOT NULL)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS quiz_scores (
                id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL,
                score INTEGER NOT NULL, total INTEGER NOT NULL,
                taken_at TEXT NOT NULL)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS coach_history (
                id SERIAL PRIMARY KEY, chat_id TEXT NOT NULL,
                role TEXT NOT NULL, content TEXT NOT NULL,
                created_at TEXT NOT NULL)""")
    log.info("DB init complete (Supabase PostgreSQL)")


async def log_signal(signal: dict) -> int:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO signals (created_at,asset,direction,entry_low,entry_high,stop_loss,
            tp1,tp2,position_size_usd,composite_score,ta_score,news_score,sentiment_score,reasoning,expires_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15) RETURNING id""",
            datetime.now(timezone.utc).isoformat(), signal.get("asset"), signal.get("direction"),
            signal.get("entry_low"), signal.get("entry_high"), signal.get("stop_loss"),
            signal.get("tp1"), signal.get("tp2"), signal.get("position_size_usd"),
            signal.get("composite_score"), signal.get("ta_score"), signal.get("news_score"),
            signal.get("sentiment_score"), signal.get("reasoning"), signal.get("expires_at"))
        return row["id"]


async def close_signal(signal_id: int, outcome: str, close_price: float, pnl_pct: float = 0.0):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE signals SET outcome=$1,closed_at=$2,close_price=$3,pnl_pct=$4 WHERE id=$5",
            outcome, datetime.now(timezone.utc).isoformat(), close_price, pnl_pct, signal_id)


async def get_recent_signals(limit: int = 10) -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM signals ORDER BY created_at DESC LIMIT $1", limit)
    return [dict(r) for r in rows]


async def get_pending_signals() -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM signals WHERE outcome='pending' ORDER BY created_at DESC")
    return [dict(r) for r in rows]


async def get_weekly_stats() -> dict:
    from datetime import timedelta
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = [dict(r) for r in await conn.fetch("SELECT * FROM signals WHERE created_at >= $1", week_ago)]
    total = len(rows)
    wins = sum(1 for r in rows if r["outcome"] in ("tp1","tp2"))
    losses = sum(1 for r in rows if r["outcome"] == "sl")
    pending = sum(1 for r in rows if r["outcome"] == "pending")
    expired = sum(1 for r in rows if r["outcome"] == "expired")
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    best = max(rows, key=lambda r: r.get("pnl_pct") or 0, default=None)
    worst = min(rows, key=lambda r: r.get("pnl_pct") or 0, default=None)
    return dict(total=total, wins=wins, losses=losses, pending=pending,
                expired=expired, win_rate=win_rate, signals=rows, best=best, worst=worst)


async def log_scan(assets_scanned: int, signals_issued: int, notes: str = ""):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO scan_log (scanned_at,assets_scanned,signals_issued,notes) VALUES ($1,$2,$3,$4)",
            datetime.now(timezone.utc).isoformat(), assets_scanned, signals_issued, notes)


async def get_today_pnl() -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT pnl_pct,trade_count,halted FROM daily_pnl WHERE date=$1", today)
    if row:
        return {"pnl_pct": row["pnl_pct"], "trade_count": row["trade_count"], "halted": bool(row["halted"])}
    return {"pnl_pct": 0.0, "trade_count": 0, "halted": False}


async def add_alert(chat_id: str, symbol: str, condition: str, target_price: float) -> int:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""INSERT INTO price_alerts (chat_id,symbol,condition,target_price,created_at)
            VALUES ($1,$2,$3,$4,$5) RETURNING id""",
            chat_id, symbol.upper(), condition, target_price, datetime.now(timezone.utc).isoformat())
        return row["id"]


async def get_active_alerts(chat_id: str = None) -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if chat_id:
            rows = await conn.fetch("SELECT * FROM price_alerts WHERE triggered=0 AND chat_id=$1 ORDER BY created_at DESC", chat_id)
        else:
            rows = await conn.fetch("SELECT * FROM price_alerts WHERE triggered=0 ORDER BY created_at DESC")
    return [dict(r) for r in rows]


async def delete_alert(alert_id: int):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM price_alerts WHERE id=$1", alert_id)


async def trigger_alert(alert_id: int):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE price_alerts SET triggered=1,triggered_at=$1 WHERE id=$2",
            datetime.now(timezone.utc).isoformat(), alert_id)


async def add_dca_plan(chat_id: str, symbol: str, amount_usd: float, frequency: str, next_trigger_utc: str) -> int:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""INSERT INTO dca_plans (chat_id,symbol,amount_usd,frequency,next_trigger_utc,created_at)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
            chat_id, symbol.upper(), amount_usd, frequency, next_trigger_utc, datetime.now(timezone.utc).isoformat())
        return row["id"]


async def get_dca_plans(chat_id: str) -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM dca_plans WHERE chat_id=$1 AND active=1 ORDER BY created_at DESC", chat_id)
    return [dict(r) for r in rows]


async def get_due_dca_plans() -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM dca_plans WHERE active=1 AND next_trigger_utc <= $1", datetime.now(timezone.utc).isoformat())
    return [dict(r) for r in rows]


async def update_dca_next(plan_id: int, next_trigger_utc: str):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE dca_plans SET next_trigger_utc=$1,executions=executions+1 WHERE id=$2", next_trigger_utc, plan_id)


async def delete_dca_plan(plan_id: int):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE dca_plans SET active=0 WHERE id=$1", plan_id)


async def log_whale_pick(symbol: str, price: float, score: float, signals: list):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO whale_picks (date,symbol,price_at_pick,score,signals,created_at)
            VALUES ($1,$2,$3,$4,$5,$6)""",
            datetime.now(timezone.utc).date().isoformat(), symbol, price, score,
            json.dumps(signals[:3]), datetime.now(timezone.utc).isoformat())


async def get_whale_picks_history(limit: int = 7) -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM whale_picks ORDER BY created_at DESC LIMIT $1", limit)
    return [dict(r) for r in rows]


async def add_holding(chat_id: str, symbol: str, amount: float, buy_price: float, note: str = "") -> int:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""INSERT INTO portfolio (chat_id,symbol,amount,buy_price,added_at,note)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
            chat_id, symbol.upper(), amount, buy_price, datetime.now(timezone.utc).isoformat(), note)
        return row["id"]


async def get_holdings(chat_id: str) -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM portfolio WHERE chat_id=$1 ORDER BY added_at DESC", chat_id)
    return [dict(r) for r in rows]


async def remove_holding(holding_id: int, chat_id: str):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM portfolio WHERE id=$1 AND chat_id=$2", holding_id, chat_id)


async def clear_portfolio(chat_id: str):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM portfolio WHERE chat_id=$1", chat_id)


# ── Quiz ──────────────────────────────────────────────────────────────────────
async def save_quiz_score(chat_id: str, score: int, total: int):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO quiz_scores (chat_id, score, total, taken_at) VALUES ($1,$2,$3,$4)",
            chat_id, score, total, datetime.now(timezone.utc).isoformat())


async def get_quiz_history(chat_id: str, limit: int = 10) -> list:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM quiz_scores WHERE chat_id=$1 ORDER BY taken_at DESC LIMIT $2",
            chat_id, limit)
    return [dict(r) for r in rows]


# ── User settings ─────────────────────────────────────────────────────────────
async def get_user_settings(chat_id: str) -> dict:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM user_settings WHERE chat_id=$1", chat_id)
    if row:
        return dict(row)
    return {"chat_id": chat_id, "language": "en", "timezone": "Asia/Kathmandu",
            "currency": "USD", "risk_profile": "moderate", "ai_style": "detailed",
            "notifications": 1}


async def upsert_user_settings(chat_id: str, **kwargs):
    pool = await _get_pool()
    kwargs["chat_id"] = chat_id
    kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT chat_id FROM user_settings WHERE chat_id=$1", chat_id)
        if existing:
            sets = ", ".join(f"{k}=${i+2}" for i, k in enumerate(k for k in kwargs if k != "chat_id"))
            vals = [v for k, v in kwargs.items() if k != "chat_id"]
            await conn.execute(f"UPDATE user_settings SET {sets} WHERE chat_id=$1", chat_id, *vals)
        else:
            cols = ", ".join(kwargs.keys())
            placeholders = ", ".join(f"${i+1}" for i in range(len(kwargs)))
            await conn.execute(f"INSERT INTO user_settings ({cols}) VALUES ({placeholders})", *kwargs.values())


# ── Coach history ─────────────────────────────────────────────────────────────
async def save_coach_message(chat_id: str, role: str, content: str):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO coach_history (chat_id, role, content, created_at) VALUES ($1,$2,$3,$4)",
            chat_id, role, content, datetime.now(timezone.utc).isoformat())
        # Keep only last 20 messages per user
        await conn.execute("""
            DELETE FROM coach_history WHERE chat_id=$1 AND id NOT IN (
                SELECT id FROM coach_history WHERE chat_id=$1 ORDER BY created_at DESC LIMIT 20)""",
            chat_id)


async def get_coach_history(chat_id: str, limit: int = 6) -> list[dict]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content FROM coach_history WHERE chat_id=$1 ORDER BY created_at DESC LIMIT $2",
            chat_id, limit)
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
