"""Serves the webapp/dist/ static files via aiohttp on $PORT (default 8080).
Also exposes /api/check and /api/register for access control.
"""
import json
import os
import asyncio
import logging
from pathlib import Path
from aiohttp import web

log = logging.getLogger(__name__)

DIST = Path(__file__).parent / "webapp-v2" / "dist"


async def make_app() -> web.Application:
    from access_control import is_approved, is_pending, register_request

    app = web.Application()

    # ── Access control API ────────────────────────────────────────────────────

    async def api_check(req: web.Request) -> web.Response:
        """GET /api/check?user_id=123456"""
        user_id = req.rel_url.query.get("user_id", "").strip()
        if not user_id:
            return web.json_response({"ok": False, "error": "missing user_id"}, status=400)
        approved = is_approved(user_id)
        pending  = is_pending(user_id)
        return web.json_response({"ok": True, "approved": approved, "pending": pending})

    async def api_register(req: web.Request) -> web.Response:
        """POST /api/register  body: {user_id, username, first_name, reason}"""
        try:
            body = await req.json()
        except Exception:
            return web.json_response({"ok": False, "error": "invalid JSON"}, status=400)

        user_id    = str(body.get("user_id", "")).strip()
        username   = str(body.get("username", "")).strip()
        first_name = str(body.get("first_name", "")).strip()
        reason     = str(body.get("reason", "")).strip()

        if not user_id:
            return web.json_response({"ok": False, "error": "missing user_id"}, status=400)

        if is_approved(user_id):
            return web.json_response({"ok": True, "status": "already_approved"})

        if is_pending(user_id):
            return web.json_response({"ok": True, "status": "already_pending"})

        new = register_request(user_id, username, first_name, reason)
        if new:
            # Notify the admin bot (non-blocking — we fire and forget)
            asyncio.create_task(_notify_admin(user_id, username, first_name, reason))

        return web.json_response({"ok": True, "status": "pending"})

    async def _notify_admin(user_id: str, username: str, first_name: str, reason: str):
        """Send an approval request to the admin via the Telegram Bot API."""
        import aiohttp as _aiohttp
        token    = os.getenv("TELEGRAM_BOT_TOKEN", "")
        admin_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not admin_id:
            log.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — cannot notify admin")
            return
        display = f"@{username}" if username else first_name or f"ID:{user_id}"
        text = (
            f"🔐 <b>New App Access Request</b>\n\n"
            f"👤 <b>Name:</b> {first_name or '—'}\n"
            f"🏷 <b>Username:</b> @{username or '—'}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"💬 <b>Reason:</b> {reason or '—'}\n\n"
            f"Approve or deny access:"
        )
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Approve", "callback_data": f"access_approve_{user_id}"},
                {"text": "❌ Deny",    "callback_data": f"access_deny_{user_id}"},
            ]]
        }
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id":    admin_id,
            "text":       text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }
        try:
            async with _aiohttp.ClientSession() as s:
                await s.post(url, json=payload, timeout=_aiohttp.ClientTimeout(total=10))
        except Exception as e:
            log.error(f"Failed to notify admin: {e}")

    # ── Static SPA ────────────────────────────────────────────────────────────

    async def index(_req):
        return web.FileResponse(DIST / "index.html")

    app.router.add_get("/api/check",    api_check)
    app.router.add_post("/api/register", api_register)
    app.router.add_get("/", index)
    app.router.add_static("/assets", DIST / "assets", append_version=True)
    app.router.add_get("/{tail:.*}", index)

    return app


def run():
    port = int(os.environ.get("PORT", 8080))
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
    )
    log.info(f"Webapp serving {DIST} on port {port}")

    if not DIST.exists():
        log.error(f"dist/ not found at {DIST} — run `npm run build` inside webapp/")
        return

    web.run_app(make_app(), port=port)


if __name__ == "__main__":
    run()
