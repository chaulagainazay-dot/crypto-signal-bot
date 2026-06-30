"""
HCG AI Crypto Trading Bot - Database Models
PostgreSQL via asyncpg — all schema DDL + CRUD helpers
"""

import asyncpg
from typing import Dict, List, Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id           BIGINT PRIMARY KEY,
    username     TEXT,
    first_name   TEXT,
    risk_profile TEXT DEFAULT 'medium',
    capital      DECIMAL DEFAULT 1000,
    timezone     TEXT DEFAULT 'UTC',
    plan         TEXT DEFAULT 'free',
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     BIGINT,
    symbol      TEXT NOT NULL,
    action      TEXT NOT NULL,
    confidence  INT,
    price       DECIMAL,
    reasons     JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolio (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    BIGINT REFERENCES users(id) ON DELETE CASCADE,
    symbol     TEXT NOT NULL,
    amount     DECIMAL NOT NULL,
    buy_price  DECIMAL NOT NULL,
    added_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trades (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          BIGINT REFERENCES users(id) ON DELETE CASCADE,
    symbol           TEXT NOT NULL,
    entry_price      DECIMAL,
    exit_price       DECIMAL,
    stop_loss        DECIMAL,
    target_price     DECIMAL,
    optimal_entry_time BIGINT,
    entry_time       BIGINT,
    exit_time        BIGINT,
    local_top_time   BIGINT,
    pnl_percent      DECIMAL,
    hold_time_hours  INT,
    setup_type       TEXT,
    mistakes         JSONB,
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      BIGINT REFERENCES users(id) ON DELETE CASCADE,
    symbol       TEXT NOT NULL,
    target_price DECIMAL NOT NULL,
    direction    TEXT NOT NULL,
    triggered    BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS whale_activity (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity      TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    action      TEXT NOT NULL,
    amount      DECIMAL,
    value_usd   DECIMAL,
    tx_hash     TEXT,
    detected_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_user_date    ON signals    (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_portfolio_user       ON portfolio  (user_id);
CREATE INDEX IF NOT EXISTS idx_trades_user          ON trades     (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_user          ON price_alerts (user_id, triggered);
CREATE INDEX IF NOT EXISTS idx_whale_symbol         ON whale_activity (symbol, detected_at);
"""


class Database:
    def __init__(self, dsn: Optional[str] = None):
        import os
        self.dsn = dsn or os.getenv("DATABASE_URL", "postgresql://localhost/hcg")
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)

    async def close(self):
        if self.pool:
            await self.pool.close()

    # ─── USERS ────────────────────────────────────────────────────────────────

    async def upsert_user(self, telegram_id: int, username: str, first_name: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (id, username, first_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET
                    username   = EXCLUDED.username,
                    first_name = EXCLUDED.first_name
            """, telegram_id, username, first_name)

    async def get_user(self, telegram_id: int) -> Dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1", telegram_id
            )
            if row:
                return dict(row)
        return {'id': telegram_id, 'risk_profile': 'medium', 'capital': 1000, 'plan': 'free'}

    async def update_user_plan(self, telegram_id: int, plan: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET plan = $1 WHERE id = $2", plan, telegram_id
            )

    # ─── SIGNALS ──────────────────────────────────────────────────────────────

    async def log_signal(self, user_id: int, signal: Dict):
        import json
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO signals (user_id, symbol, action, confidence, price, reasons)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, user_id, signal['symbol'], signal['action'],
                signal.get('confidence'), signal.get('price'),
                json.dumps(signal.get('reasons', [])))

    async def daily_signal_count(self, user_id: int) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("""
                SELECT COUNT(*) FROM signals
                WHERE user_id = $1 AND created_at >= CURRENT_DATE
            """, user_id) or 0

    async def get_signals(self, days: int = 30) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT symbol, action, confidence, price, created_at
                FROM signals
                WHERE created_at >= NOW() - ($1 || ' days')::INTERVAL
                ORDER BY created_at DESC
            """, str(days))
            return [dict(r) for r in rows]

    # ─── PORTFOLIO ────────────────────────────────────────────────────────────

    async def get_portfolio(self, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM portfolio WHERE user_id = $1", user_id
            )
            return [dict(r) for r in rows]

    async def add_holding(self, user_id: int, symbol: str, amount: float, buy_price: float):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO portfolio (user_id, symbol, amount, buy_price)
                VALUES ($1, $2, $3, $4)
            """, user_id, symbol, amount, buy_price)

    async def remove_holding(self, holding_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM portfolio WHERE id = $1", holding_id)

    # ─── TRADES ───────────────────────────────────────────────────────────────

    async def log_trade(self, user_id: int, trade: Dict):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO trades
                    (user_id, symbol, entry_price, exit_price, stop_loss,
                     target_price, pnl_percent, notes)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            """, user_id, trade['symbol'],
                trade.get('entry_price'), trade.get('exit_price'),
                trade.get('stop_loss'),   trade.get('target_price'),
                trade.get('pnl_percent'), trade.get('notes', ''))

    async def get_trades(self, user_id: int, limit: int = 50) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM trades
                WHERE user_id = $1
                ORDER BY created_at DESC LIMIT $2
            """, user_id, limit)
            return [dict(r) for r in rows]

    # ─── ALERTS ───────────────────────────────────────────────────────────────

    async def add_alert(self, user_id: int, symbol: str, target: float, direction: str):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO price_alerts (user_id, symbol, target_price, direction)
                VALUES ($1, $2, $3, $4)
            """, user_id, symbol, target, direction)

    async def get_active_alerts(self, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM price_alerts
                WHERE user_id = $1 AND triggered = FALSE
            """, user_id)
            return [dict(r) for r in rows]

    async def get_all_active_alerts(self) -> List[Dict]:
        """Used by price alert checker loop"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM price_alerts WHERE triggered = FALSE"
            )
            return [dict(r) for r in rows]

    async def mark_alert_triggered(self, alert_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE price_alerts SET triggered = TRUE WHERE id = $1", alert_id
            )

    # ─── WHALE DATA ───────────────────────────────────────────────────────────

    async def log_whale_activity(
        self, entity: str, symbol: str, action: str,
        amount: float, value_usd: float, tx_hash: str = ""
    ):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO whale_activity (entity, symbol, action, amount, value_usd, tx_hash)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, entity, symbol, action, amount, value_usd, tx_hash)

    async def get_whale_activity(self, symbol: str, limit: int = 10) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM whale_activity
                WHERE symbol = $1 ORDER BY detected_at DESC LIMIT $2
            """, symbol, limit)
            return [dict(r) for r in rows]
