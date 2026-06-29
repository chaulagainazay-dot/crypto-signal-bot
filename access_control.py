"""Shared access control — approved/pending user registry backed by data/access.json."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ACCESS_FILE = Path(__file__).parent / "data" / "access.json"

# Admin user IDs that always have access (never need approval)
# TELEGRAM_CHAT_ID is Ajay's personal chat — auto-approved
_ADMIN_IDS: set[str] = set()
try:
    _cid = os.getenv("TELEGRAM_CHAT_ID", "")
    if _cid:
        _ADMIN_IDS.add(str(_cid))
except Exception:
    pass


def _load() -> dict:
    try:
        return json.loads(ACCESS_FILE.read_text())
    except Exception:
        return {"approved": [], "pending": []}


def _save(data: dict) -> None:
    ACCESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACCESS_FILE.write_text(json.dumps(data, indent=2))


def is_approved(user_id: str) -> bool:
    user_id = str(user_id)
    if user_id in _ADMIN_IDS:
        return True
    data = _load()
    return user_id in [str(u["user_id"]) for u in data.get("approved", [])]


def is_pending(user_id: str) -> bool:
    user_id = str(user_id)
    data = _load()
    return user_id in [str(u["user_id"]) for u in data.get("pending", [])]


def register_request(user_id: str, username: str, first_name: str, reason: str = "") -> bool:
    """Add to pending list. Returns True if newly added, False if already exists."""
    user_id = str(user_id)
    if is_approved(user_id):
        return False
    data = _load()
    existing_ids = [str(u["user_id"]) for u in data["pending"]]
    if user_id in existing_ids:
        return False  # already pending
    data["pending"].append({
        "user_id":    user_id,
        "username":   username or "",
        "first_name": first_name or "",
        "reason":     reason or "",
        "requested_at": datetime.now(timezone.utc).isoformat(),
    })
    _save(data)
    return True


def approve_user(user_id: str) -> dict | None:
    """Move from pending → approved. Returns the user record or None."""
    user_id = str(user_id)
    data = _load()
    pending = data.get("pending", [])
    match = next((u for u in pending if str(u["user_id"]) == user_id), None)
    if not match:
        # Could be a direct approve (not via pending), create minimal record
        match = {"user_id": user_id, "username": "", "first_name": "", "reason": "direct"}
    data["pending"]  = [u for u in pending if str(u["user_id"]) != user_id]
    data.setdefault("approved", [])
    # avoid duplicates
    if user_id not in [str(u["user_id"]) for u in data["approved"]]:
        match["approved_at"] = datetime.now(timezone.utc).isoformat()
        data["approved"].append(match)
    _save(data)
    return match


def deny_user(user_id: str) -> bool:
    """Remove from pending list. Returns True if found."""
    user_id = str(user_id)
    data = _load()
    before = len(data.get("pending", []))
    data["pending"] = [u for u in data["pending"] if str(u["user_id"]) != user_id]
    _save(data)
    return len(data["pending"]) < before


def revoke_user(user_id: str) -> bool:
    """Remove from approved list."""
    user_id = str(user_id)
    data = _load()
    before = len(data.get("approved", []))
    data["approved"] = [u for u in data["approved"] if str(u["user_id"]) != user_id]
    _save(data)
    return len(data["approved"]) < before


def list_pending() -> list[dict]:
    return _load().get("pending", [])


def list_approved() -> list[dict]:
    return _load().get("approved", [])
