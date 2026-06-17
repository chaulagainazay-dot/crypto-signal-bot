"""
L4 — Risk Gate
Validates signals against account risk rules and computes position size.
Can veto any signal regardless of score.
"""
from datetime import datetime, timezone

import config
from utils.db import get_today_pnl


POSITION_REGISTRY: list[dict] = []  # in-memory tracking of open positions


async def gate(signal: dict) -> tuple[bool, str, dict]:
    """
    Returns (approved, reason, enriched_signal).
    The Risk Gate is the final veto — it runs AFTER signal generation.
    """
    # 1. Daily loss limit
    pnl = await get_today_pnl()
    if pnl["halted"]:
        return False, "Daily halt active — no new signals until next UTC day.", signal
    if pnl["pnl_pct"] <= -config.DAILY_LOSS_LIMIT_PCT:
        return False, f"Daily loss limit hit ({pnl['pnl_pct']:.2f}%). Halting.", signal

    # 2. Max concurrent positions
    active = [p for p in POSITION_REGISTRY if p.get("status") == "open"]
    if len(active) >= config.MAX_CONCURRENT_POSITIONS:
        return False, f"Max concurrent positions ({config.MAX_CONCURRENT_POSITIONS}) reached.", signal

    # 3. Low-liquidity hour check
    now_utc = datetime.now(timezone.utc)
    if config.LOW_LIQ_START_UTC <= now_utc.hour < config.LOW_LIQ_END_UTC:
        liq_factor = 0.5  # reduce size during thin hours
    else:
        liq_factor = 1.0

    # 4. Position sizing: risk_$ / stop_distance
    entry = (signal["entry_low"] + signal["entry_high"]) / 2
    stop = signal["stop_loss"]
    if entry == 0 or stop == 0:
        return False, "Invalid entry/stop levels.", signal

    stop_distance = abs(entry - stop)
    if stop_distance < 0.0001 * entry:
        return False, "Stop distance too small — likely a data error.", signal

    risk_dollars = (config.RISK_PER_TRADE_PCT / 100) * config.ACCOUNT_SIZE * liq_factor
    position_size_usd = (risk_dollars / stop_distance) * entry

    # Cap at 20% of account
    position_size_usd = min(position_size_usd, config.ACCOUNT_SIZE * 0.20)

    signal = {**signal, "position_size_usd": round(position_size_usd, 2), "risk_dollars": round(risk_dollars, 2)}
    return True, "approved", signal


def register_open_position(signal: dict):
    POSITION_REGISTRY.append({**signal, "status": "open"})


def close_position(asset: str):
    for p in POSITION_REGISTRY:
        if p["asset"] == asset and p["status"] == "open":
            p["status"] = "closed"
            break
