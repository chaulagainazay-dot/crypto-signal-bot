"""
Portfolio Manager — add/remove holdings, live P&L, allocation analysis,
risk/diversification scoring, rebalancing suggestions.
HTML output with expandable blockquotes (Bot API 9.0+).
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False)
    return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=12))

def _esc(t) -> str:
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


# ── Price fetcher ──────────────────────────────────────────────────────────────

async def fetch_prices(symbols: list) -> dict:
    """Fetch live USD prices for a list of symbols via Bybit → Binance fallback."""
    prices = {}
    async with _make_session() as session:
        tasks = [_fetch_one(session, s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    for sym, result in zip(symbols, results):
        if isinstance(result, float) and result > 0:
            prices[sym.upper()] = result
    return prices


async def _fetch_one(session, symbol: str) -> float:
    sym = symbol.upper().replace("/","").replace("-","")
    if not sym.endswith("USDT"):
        sym += "USDT"
    # Bybit
    try:
        async with session.get(
            "https://api.bybit.com/v5/market/tickers",
            params={"category": "spot", "symbol": sym}
        ) as r:
            data = await r.json()
            return float(data["result"]["list"][0]["lastPrice"])
    except Exception:
        pass
    # Binance fallback
    try:
        async with session.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": sym}
        ) as r:
            data = await r.json()
            return float(data["price"])
    except Exception:
        pass
    # CoinGecko fallback
    try:
        cg_id = symbol.lower()
        async with session.get(
            f"https://api.coingecko.com/api/v3/simple/price",
            params={"ids": cg_id, "vs_currencies": "usd"}
        ) as r:
            data = await r.json()
            return float(list(data.values())[0]["usd"])
    except Exception:
        return 0.0


# ── Analysis ───────────────────────────────────────────────────────────────────

def _parse_command(text: str) -> dict:
    """
    Parse /addholding BTC 0.5 45000 [note]
    Returns dict with symbol, amount, buy_price, note or None on error.
    """
    parts = text.strip().split(maxsplit=4)
    if len(parts) < 4:
        return None
    try:
        symbol    = parts[1].upper().replace("USDT","").replace("/","")
        amount    = float(parts[2].replace(",",""))
        buy_price = float(parts[3].replace(",","").replace("$",""))
        note      = parts[4] if len(parts) > 4 else ""
        return {"symbol": symbol, "amount": amount, "buy_price": buy_price, "note": note}
    except (ValueError, IndexError):
        return None


def _allocation_bar(pct: float, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    return "▓" * filled + "░" * (width - filled)


def _risk_label(pct: float) -> str:
    if pct >= 40: return "🔴 Concentrated"
    if pct >= 25: return "🟠 High weight"
    if pct >= 15: return "🟡 Moderate"
    return "🟢 Balanced"


def _diversification_score(holdings_with_prices: list) -> tuple:
    """
    Score how well-diversified the portfolio is.
    Returns (score 0-100, label, advice).
    """
    n = len(holdings_with_prices)
    if n == 0:
        return 0, "Empty", "Add some holdings first."

    total_val = sum(h["current_value"] for h in holdings_with_prices)
    if total_val == 0:
        return 0, "No price data", "Could not fetch live prices."

    allocs = [h["current_value"] / total_val * 100 for h in holdings_with_prices]
    max_alloc = max(allocs)
    hhi = sum((a/100)**2 for a in allocs) * 100  # Herfindahl index 0-100

    # Coin count score (0-40)
    count_score = min(40, n * 8)

    # Concentration score (0-40)
    conc_score = max(0, 40 - int(hhi * 1.5))

    # Large-cap mix — check if BTC or ETH present (0-20)
    syms = {h["symbol"].upper() for h in holdings_with_prices}
    has_btc = "BTC" in syms
    has_eth = "ETH" in syms
    bluechip_score = (10 if has_btc else 0) + (10 if has_eth else 0)

    total = count_score + conc_score + bluechip_score
    total = min(100, total)

    if total >= 75:   label = "🟢 Well Diversified"
    elif total >= 50: label = "🟡 Moderate"
    elif total >= 30: label = "🟠 Concentrated"
    else:             label = "🔴 High Risk"

    advice_parts = []
    if not has_btc:   advice_parts.append("Add BTC as a base layer")
    if not has_eth:   advice_parts.append("Add ETH for DeFi exposure")
    if max_alloc > 40: advice_parts.append(f"Reduce largest position ({max_alloc:.0f}%)")
    if n < 4:         advice_parts.append("Add more coins for better spread")
    advice = " · ".join(advice_parts) if advice_parts else "Portfolio is well structured."

    return total, label, advice


def analyze_portfolio(holdings: list, prices: dict) -> dict:
    """Compute full portfolio metrics from raw holdings + live prices."""
    enriched = []
    for h in holdings:
        sym = h["symbol"].upper()
        current_price = prices.get(sym, 0)
        current_value = current_price * h["amount"]
        cost_basis    = h["buy_price"] * h["amount"]
        pnl_usd  = current_value - cost_basis
        pnl_pct  = (pnl_usd / cost_basis * 100) if cost_basis > 0 else 0
        enriched.append({
            **h,
            "symbol":        sym,
            "current_price": current_price,
            "current_value": current_value,
            "cost_basis":    cost_basis,
            "pnl_usd":       pnl_usd,
            "pnl_pct":       pnl_pct,
        })

    total_value = sum(h["current_value"] for h in enriched)
    total_cost  = sum(h["cost_basis"]    for h in enriched)
    total_pnl_usd = total_value - total_cost
    total_pnl_pct = (total_pnl_usd / total_cost * 100) if total_cost > 0 else 0

    # Allocation %
    for h in enriched:
        h["alloc_pct"] = (h["current_value"] / total_value * 100) if total_value > 0 else 0

    # Sort by value descending
    enriched.sort(key=lambda x: x["current_value"], reverse=True)

    div_score, div_label, div_advice = _diversification_score(enriched)

    # Best and worst performers
    with_prices = [h for h in enriched if h["current_price"] > 0]
    best  = max(with_prices, key=lambda h: h["pnl_pct"], default=None)
    worst = min(with_prices, key=lambda h: h["pnl_pct"], default=None)

    return dict(
        holdings=enriched,
        total_value=total_value,
        total_cost=total_cost,
        total_pnl_usd=total_pnl_usd,
        total_pnl_pct=total_pnl_pct,
        div_score=div_score,
        div_label=div_label,
        div_advice=div_advice,
        best=best,
        worst=worst,
    )


# ── Formatters ─────────────────────────────────────────────────────────────────

def _fp(p: float) -> str:
    if not p or p == 0: return "$0"
    if p >= 10000: return f"${p:,.0f}"
    if p >= 100:   return f"${p:,.2f}"
    if p >= 1:     return f"${p:,.4f}"
    if p >= 0.01:  return f"${p:.6f}"
    return f"${p:.8f}"

def _fv(v: float) -> str:
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000:     return f"${v:,.0f}"
    return f"${v:.2f}"


def format_portfolio_html(analysis: dict, chat_id: str) -> str:
    holdings  = analysis["holdings"]
    total_val = analysis["total_value"]
    total_pnl = analysis["total_pnl_usd"]
    pnl_pct   = analysis["total_pnl_pct"]
    div_score = analysis["div_score"]
    div_label = analysis["div_label"]
    div_advice= analysis["div_advice"]
    best      = analysis["best"]
    worst     = analysis["worst"]

    pnl_icon = "🟢" if total_pnl >= 0 else "🔴"
    arrow    = "▲" if total_pnl >= 0 else "▼"

    from datetime import timedelta
    npt = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime("%I:%M %p NPT · %a %b %d")

    lines = [
        "💼 <b>Portfolio Analysis</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"<i>{npt}</i>",
        "",
        f"<b>Total Value</b>  <code>{_fv(total_val)}</code>",
        f"<b>Total P&amp;L</b>   {pnl_icon} <code>{arrow} {_fv(abs(total_pnl))}  ({pnl_pct:+.2f}%)</code>",
        f"<b>Holdings</b>    <code>{len(holdings)}</code>  coins",
        f"<b>Diversity</b>   {div_label}  <code>{div_score}/100</code>",
        "",
    ]

    # ── Per-holding block ─────────────────────────────────────────────────
    holdings_detail = ""
    for h in holdings:
        pnl_i = "🟢" if h["pnl_pct"] >= 0 else "🔴"
        bar   = _allocation_bar(h["alloc_pct"])
        price_str  = _fp(h["current_price"]) if h["current_price"] else "⚠️ no price"
        value_str  = _fv(h["current_value"])
        pnl_str    = f"{h['pnl_pct']:+.2f}%"
        holdings_detail += (
            f"<b>{_esc(h['symbol'])}</b>  {price_str}  {pnl_i} <code>{pnl_str}</code>\n"
            f"  Amount  <code>{h['amount']:,g}</code>   Value  <code>{value_str}</code>\n"
            f"  Entry   <code>{_fp(h['buy_price'])}</code>   Alloc  <code>{h['alloc_pct']:.1f}%</code>  {bar}\n"
        )
        if h.get("note"):
            holdings_detail += f"  <i>{_esc(h['note'])}</i>\n"
        holdings_detail += "\n"

    lines.append(
        "<blockquote expandable>"
        "<b>📊 All Holdings</b>\n\n"
        f"{holdings_detail.rstrip()}"
        "</blockquote>"
    )

    # ── Allocation chart ──────────────────────────────────────────────────
    alloc_rows = ""
    for h in holdings[:8]:
        bar  = _allocation_bar(h["alloc_pct"], width=12)
        risk = _risk_label(h["alloc_pct"])
        alloc_rows += (
            f"  <b>{_esc(h['symbol'])}</b>  <code>{h['alloc_pct']:.1f}%</code>  {bar}  {risk}\n"
        )

    lines.append(
        "\n<blockquote expandable>"
        "<b>🥧 Allocation Breakdown</b>\n\n"
        f"{alloc_rows.rstrip()}"
        "</blockquote>"
    )

    # ── Best / Worst ──────────────────────────────────────────────────────
    if best or worst:
        perf_rows = ""
        if best:
            perf_rows += f"🏆 <b>Best</b>   <b>{_esc(best['symbol'])}</b>  <code>{best['pnl_pct']:+.2f}%</code>  (<code>{_fv(best['pnl_usd'])}</code>)\n"
        if worst and worst != best:
            perf_rows += f"💀 <b>Worst</b>  <b>{_esc(worst['symbol'])}</b>  <code>{worst['pnl_pct']:+.2f}%</code>  (<code>{_fv(worst['pnl_usd'])}</code>)\n"
        lines.append(
            "\n<blockquote expandable>"
            "<b>🏅 Top & Bottom Performers</b>\n\n"
            f"{perf_rows.rstrip()}"
            "</blockquote>"
        )

    # ── Risk & Diversification ────────────────────────────────────────────
    lines.append(
        "\n<blockquote expandable>"
        f"<b>⚠️ Risk &amp; Diversification</b>\n\n"
        f"Score   <code>{div_score}/100</code>  {div_label}\n"
        f"Advice  <i>{_esc(div_advice)}</i>"
        "</blockquote>"
    )

    # ── Footer ────────────────────────────────────────────────────────────
    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━",
        "<i>Prices are live · Add holdings with /addholding · Remove with /removeholding &lt;id&gt;</i>",
    ]

    return "\n".join(lines)


def format_empty_portfolio_html() -> str:
    return (
        "💼 <b>My Portfolio</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Your portfolio is empty.\n\n"
        "<b>How to add a holding:</b>\n"
        "<code>/addholding BTC 0.5 45000</code>\n"
        "<code>/addholding ETH 2 2800</code>\n"
        "<code>/addholding SOL 10 120 long-term</code>\n\n"
        "<i>Format: /addholding SYMBOL AMOUNT BUY_PRICE [note]</i>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<i>Prices are updated live every time you open the portfolio.</i>"
    )


def format_holdings_list_html(holdings: list) -> str:
    """Simple list for removal — shows IDs."""
    if not holdings:
        return format_empty_portfolio_html()
    lines = ["💼 <b>Holdings List</b>\n", ""]
    for h in holdings:
        dt = h["added_at"][:10]
        lines.append(
            f"<code>#{h['id']}</code>  <b>{_esc(h['symbol'])}</b>  "
            f"<code>{h['amount']:,g}</code> @ <code>{_fp(h['buy_price'])}</code>"
            f"  <i>{dt}</i>"
        )
        if h.get("note"):
            lines.append(f"  <i>{_esc(h['note'])}</i>")
    lines += [
        "",
        "<i>Remove: /removeholding &lt;id&gt;</i>",
        "<i>Clear all: /clearportfolio</i>",
    ]
    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

async def build_portfolio_analysis(chat_id: str) -> str:
    from utils.db import get_holdings
    holdings = await get_holdings(chat_id)
    if not holdings:
        return format_empty_portfolio_html()

    symbols = list({h["symbol"].upper() for h in holdings})
    prices  = await fetch_prices(symbols)
    analysis = analyze_portfolio(holdings, prices)
    return format_portfolio_html(analysis, chat_id)
