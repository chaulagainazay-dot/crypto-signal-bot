"""Watchlist — track favorite stocks with quick price updates."""
from layers.nepse_data import fetch_prices_bulk
from utils.fmt import esc, fp, pct, npt_now, change_icon, SEP


async def build_watchlist_view(user_id: str) -> str:
    from utils.db import get_watchlist
    items = await get_watchlist(user_id)

    lines = ["👁️ <b>My Watchlist</b>", SEP, f"<i>{npt_now()}</i>", ""]

    if not items:
        lines += [
            "Watchlist is empty.",
            "",
            "<b>Add stocks:</b>",
            "<code>/watch NABIL</code>",
            "<code>/watch NICA</code>",
            "",
            "<i>Remove: /unwatch SYMBOL</i>",
        ]
        return "\n".join(lines)

    symbols = [i["symbol"] for i in items]
    prices  = await fetch_prices_bulk(symbols)

    # Build price rows
    summary = await _get_change_data(symbols)

    for item in items:
        sym = item["symbol"]
        ltp = prices.get(sym, 0)
        pc  = summary.get(sym, {}).get("pc", 0)
        icon= change_icon(pc)
        lines.append(
            f"{icon} <b>{esc(sym)}</b>  <code>रु {fp(ltp)}</code>  <code>{pct(pc)}</code>"
        )

    lines += [
        "",
        SEP,
        "<i>/watch SYMBOL — add · /unwatch SYMBOL — remove · /stock SYMBOL — deep dive</i>",
    ]
    return "\n".join(lines)


async def _get_change_data(symbols: list) -> dict:
    """Get pc (percent change) for each symbol from market summary."""
    from layers.nepse_data import fetch_market_summary
    data = {}
    try:
        ms = await fetch_market_summary()
        for s in ms.get("turnover", {}).get("detail", []):
            sym = s.get("s", "").upper()
            if sym in [x.upper() for x in symbols]:
                data[sym] = {"pc": float(s.get("pc", 0))}
    except Exception:
        pass
    return data
