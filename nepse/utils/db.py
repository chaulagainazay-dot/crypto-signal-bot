"""Database layer — PostgreSQL via asyncpg (Supabase)."""
import asyncpg
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
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL,
                shares REAL NOT NULL, buy_price REAL NOT NULL,
                added_at TEXT NOT NULL, note TEXT)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL,
                condition TEXT NOT NULL, target_price REAL NOT NULL,
                created_at TEXT NOT NULL, triggered INTEGER DEFAULT 0, triggered_at TEXT)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS dca_plans (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL,
                amount_npr REAL NOT NULL, frequency TEXT NOT NULL,
                next_trigger_utc TEXT NOT NULL, active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL, executions INTEGER DEFAULT 0)""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL,
                added_at TEXT NOT NULL, UNIQUE(user_id, symbol))""")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id SERIAL PRIMARY KEY, scanned_at TEXT NOT NULL, notes TEXT)""")
    log.info("NEPSE DB init complete (Supabase PostgreSQL)")


async def add_holding(user_id, symbol, shares, buy_price, note=""):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""INSERT INTO portfolio (user_id,symbol,shares,buy_price,added_at,note)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
            user_id, symbol.upper(), shares, buy_price, datetime.now(timezone.utc).isoformat(), note)
        return row["id"]

async def get_holdings(user_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM portfolio WHERE user_id=$1 ORDER BY added_at DESC", user_id)
    return [dict(r) for r in rows]

async def remove_holding(holding_id, user_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM portfolio WHERE id=$1 AND user_id=$2", holding_id, user_id)

async def clear_portfolio(user_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM portfolio WHERE user_id=$1", user_id)


async def add_alert(user_id, symbol, condition, target_price):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""INSERT INTO price_alerts (user_id,symbol,condition,target_price,created_at)
            VALUES ($1,$2,$3,$4,$5) RETURNING id""",
            user_id, symbol.upper(), condition, target_price, datetime.now(timezone.utc).isoformat())
        return row["id"]

async def get_active_alerts(user_id=None):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if user_id:
            rows = await conn.fetch("SELECT * FROM price_alerts WHERE triggered=0 AND user_id=$1 ORDER BY created_at DESC", user_id)
        else:
            rows = await conn.fetch("SELECT * FROM price_alerts WHERE triggered=0 ORDER BY created_at DESC")
    return [dict(r) for r in rows]

async def trigger_alert(alert_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE price_alerts SET triggered=1,triggered_at=$1 WHERE id=$2",
            datetime.now(timezone.utc).isoformat(), alert_id)

async def delete_alert(alert_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM price_alerts WHERE id=$1", alert_id)


async def add_dca_plan(user_id, symbol, amount_npr, frequency, next_trigger_utc):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""INSERT INTO dca_plans (user_id,symbol,amount_npr,frequency,next_trigger_utc,created_at)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
            user_id, symbol.upper(), amount_npr, frequency, next_trigger_utc, datetime.now(timezone.utc).isoformat())
        return row["id"]

async def get_dca_plans(user_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM dca_plans WHERE user_id=$1 AND active=1 ORDER BY created_at DESC", user_id)
    return [dict(r) for r in rows]

async def get_due_dca_plans():
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM dca_plans WHERE active=1 AND next_trigger_utc <= $1",
            datetime.now(timezone.utc).isoformat())
    return [dict(r) for r in rows]

async def update_dca_next(plan_id, next_trigger_utc):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE dca_plans SET next_trigger_utc=$1,executions=executions+1 WHERE id=$2",
            next_trigger_utc, plan_id)

async def delete_dca_plan(plan_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE dca_plans SET active=0 WHERE id=$1", plan_id)


async def add_watchlist(user_id, symbol):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO watchlist (user_id,symbol,added_at) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
            user_id, symbol.upper(), datetime.now(timezone.utc).isoformat())

async def get_watchlist(user_id):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM watchlist WHERE user_id=$1 ORDER BY added_at ASC", user_id)
    return [dict(r) for r in rows]

async def remove_watchlist(user_id, symbol):
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM watchlist WHERE user_id=$1 AND symbol=$2", user_id, symbol.upper())
