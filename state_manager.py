"""
Signal State Manager
Prevents duplicate/spam alerts. Tracks active signals per asset.
A signal is "new" only if:
  - No signal for that asset in the last EXPIRY minutes, OR
  - Direction changed since last signal, OR
  - Entry zone shifted >0.5% from last signal
"""
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

import config

# In-memory state: asset -> last signal metadata
_state: dict[str, dict] = {}


def _sig_hash(asset: str, direction: str, entry_mid: float) -> str:
    bucket = round(entry_mid / (entry_mid * 0.005)) * (entry_mid * 0.005)  # 0.5% bucket
    key = f"{asset}:{direction}:{bucket:.0f}"
    return hashlib.md5(key.encode()).hexdigest()[:8]


def is_new_signal(asset: str, direction: str, entry_mid: float) -> bool:
    """Returns True only if this signal is meaningfully different from the last one."""
    now = datetime.now(timezone.utc)
    prev = _state.get(asset)

    if prev is None:
        return True

    # Expired
    if now > prev["expires_at"]:
        return True

    # Direction flipped
    if prev["direction"] != direction:
        return True

    # Entry zone shifted >0.5%
    if abs(entry_mid - prev["entry_mid"]) / prev["entry_mid"] > 0.005:
        return True

    return False  # Same setup still active — suppress


def register_signal(asset: str, direction: str, entry_mid: float):
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.SIGNAL_EXPIRY_MINUTES)
    _state[asset] = {
        "direction": direction,
        "entry_mid": entry_mid,
        "expires_at": expires,
        "sig_hash": _sig_hash(asset, direction, entry_mid),
        "sent_at": datetime.now(timezone.utc),
    }


def get_active(asset: str) -> Optional[dict]:
    now = datetime.now(timezone.utc)
    prev = _state.get(asset)
    if prev and now <= prev["expires_at"]:
        return prev
    return None


def invalidate(asset: str):
    if asset in _state:
        _state[asset]["expires_at"] = datetime.now(timezone.utc)


def clear_all():
    _state.clear()
