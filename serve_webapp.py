"""Serves the webapp/dist/ static files via aiohttp on $PORT (default 8080)."""
import os
import asyncio
import logging
from pathlib import Path
from aiohttp import web

log = logging.getLogger(__name__)

DIST = Path(__file__).parent / "webapp" / "dist"


async def make_app() -> web.Application:
    app = web.Application()

    async def index(_req):
        return web.FileResponse(DIST / "index.html")

    # SPA fallback — any non-asset path returns index.html
    app.router.add_get("/", index)
    app.router.add_static("/assets", DIST / "assets", append_version=True)
    # Catch-all for any route the SPA handles client-side
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
