"""NEPSE portfolio manager — NPR-denominated, integer shares."""
from datetime import datetime, timezone, timedelta
from utils.fmt import esc, npr, fp, pct, npt_now, pnl_icon, SEP


def _bar(pct_v: float, width: int = 10) -> str:
    filled = round(min(100, max(0, pct_v)) / 100 * width)
    return "▓" * filled + "░" * (width - filled)


def _risk_label(pct_v: float) -> str:
    if pct_v >= 40: return "🔴 Heavy"
    if pct_v >= 25: return "🟠 High"
    if pct_v >= 15: return "🟡 Moderate"
    return "🟢 Balanced"


def parse_addstock(text: str) -> dict:
    """Parse /addstock NABIL 10 1200 [note]"""
    parts = text.strip().split(maxsplit=4)
    if len(parts) < 4:
        return None
    try:
        symbol    = parts[1].upper()
        shares    = float(parts[2].replace(",", ""))
        buy_price = float(parts[3].replace(",", ""))
        note      = parts[4] if len(parts) > 4 else ""
        return {"symbol": symbol, "shares": shares, "buy_price": buy_price, "note": note}
    except (ValueError, IndexError):
        return None


def analyze_portfolio(holdings: list, prices: dict) -> dict:
    enriched = []
    for h in holdings:
        sym = h["symbol"].upper()
        ltp = prices.get(sym, 0)
        current_val = ltp * h["shares"]
        cost_basis  = h["buy_price"] * h["shares"]
        pnl_npr  = current_val - cost_basis
        pnl_pct  = (pnl_npr / cost_basis * 100) if cost_basis > 0 else 0
        enriched.append({
            **h,
            "symbol":      sym,
            "ltp":         ltp,
            "current_val": current_val,
            "cost_basis":  cost_basis,
            "pnl_npr":     pnl_npr,
            "pnl_pct":     pnl_pct,
        })

    total_val  = sum(h["current_val"] for h in enriched)
    total_cost = sum(h["cost_basis"] for h in enriched)
    total_pnl  = total_val - total_cost
    total_pct  = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    for h in enriched:
        h["alloc_pct"] = (h["current_val"] / total_val * 100) if total_val > 0 else 0

    enriched.sort(key=lambda x: x["current_val"], reverse=True)

    # Diversification score
    n = len(enriched)
    count_score = min(40, n * 8)
    hhi = sum((h["alloc_pct"] / 100) ** 2 for h in enriched) * 100
    conc_score  = max(0, 40 - int(hhi * 1.5))
    max_alloc   = max((h["alloc_pct"] for h in enriched), default=0)
    # Sector variety approximation: banking stocks (NABIL,NBL,SBI,NICA,KBL,EBL etc) vs others
    div_score   = min(100, count_score + conc_score + 20)
    if   div_score >= 75: div_label = "🟢 Well Diversified"
    elif div_score >= 50: div_label = "🟡 Moderate"
    elif div_score >= 30: div_label = "🟠 Concentrated"
    else:                 div_label = "🔴 High Risk"

    advice_parts = []
    if n < 4:            advice_parts.append("Add more stocks for better spread")
    if max_alloc > 40:   advice_parts.append(f"Reduce top position ({max_alloc:.0f}%)")
    advice = " · ".join(advice_parts) if advice_parts else "Portfolio looks balanced."

    best  = max(enriched, key=lambda h: h["pnl_pct"], default=None) if enriched else None
    worst = min(enriched, key=lambda h: h["pnl_pct"], default=None) if enriched else None

    return dict(
        holdings=enriched,
        total_val=total_val,
        total_cost=total_cost,
        total_pnl=total_pnl,
        total_pct=total_pct,
        div_score=div_score,
        div_label=div_label,
        advice=advice,
        best=best,
        worst=worst,
    )


def _mill(v: float) -> str:
    if v >= 10_000_000: return f"रु {v/10_000_000:.2f}Cr"
    if v >= 100_000:    return f"रु {v/100_000:.2f}L"
    if v >= 1000:       return f"रु {v:,.0f}"
    return f"रु {v:.2f}"


def format_portfolio_html(analysis: dict) -> str:
    h_list   = analysis["holdings"]
    pnl_icon = "🟢" if analysis["total_pnl"] >= 0 else "🔴"
    arrow    = "▲" if analysis["total_pnl"] >= 0 else "▼"

    lines = [
        "📊 <b>My NEPSE Portfolio</b>",
        SEP,
        f"<i>{npt_now()}</i>",
        "",
        f"<b>Total Value</b>  <code>{_mill(analysis['total_val'])}</code>",
        f"<b>Total Cost</b>   <code>{_mill(analysis['total_cost'])}</code>",
        f"<b>P&amp;L</b>          {pnl_icon} <code>{arrow} {_mill(abs(analysis['total_pnl']))}  ({analysis['total_pct']:+.2f}%)</code>",
        f"<b>Holdings</b>     <code>{len(h_list)}</code>  stocks",
        f"<b>Diversity</b>    {analysis['div_label']}  <code>{analysis['div_score']}/100</code>",
        "",
    ]

    # Per-stock detail
    h_rows = ""
    for h in h_list:
        pi    = "🟢" if h["pnl_pct"] >= 0 else "🔴"
        arrow2= "▲" if h["pnl_pct"] >= 0 else "▼"
        ltp_s = f"रु {fp(h['ltp'])}" if h["ltp"] else "⚠️ no price"
        h_rows += (
            f"<b>{esc(h['symbol'])}</b>  {ltp_s}  {pi} <code>{h['pnl_pct']:+.2f}%</code>\n"
            f"  Shares <code>{h['shares']:,g}</code>  ·  Entry <code>रु {fp(h['buy_price'])}</code>\n"
            f"  Value  <code>{_mill(h['current_val'])}</code>  ·  Alloc <code>{h['alloc_pct']:.1f}%</code>  {_bar(h['alloc_pct'])}\n"
        )
        if h.get("note"):
            h_rows += f"  <i>{esc(h['note'])}</i>\n"
        h_rows += "\n"

    lines.append(
        "<blockquote expandable>"
        "<b>📋 All Holdings</b>\n\n"
        f"{h_rows.rstrip()}"
        "</blockquote>"
    )

    # Allocation chart
    alloc_rows = ""
    for h in h_list[:8]:
        alloc_rows += f"  <b>{esc(h['symbol'])}</b>  <code>{h['alloc_pct']:.1f}%</code>  {_bar(h['alloc_pct'],12)}  {_risk_label(h['alloc_pct'])}\n"

    lines.append(
        "\n<blockquote expandable>"
        "<b>🥧 Allocation</b>\n\n"
        f"{alloc_rows.rstrip()}"
        "</blockquote>"
    )

    # Best / Worst
    best  = analysis["best"]
    worst = analysis["worst"]
    if best or worst:
        pw_rows = ""
        if best:
            pw_rows += f"🏆 <b>Best</b>   <b>{esc(best['symbol'])}</b>  <code>{best['pnl_pct']:+.2f}%</code>  <i>({_mill(best['pnl_npr'])})</i>\n"
        if worst and worst != best:
            pw_rows += f"💀 <b>Worst</b>  <b>{esc(worst['symbol'])}</b>  <code>{worst['pnl_pct']:+.2f}%</code>  <i>({_mill(worst['pnl_npr'])})</i>\n"
        lines.append(
            "\n<blockquote expandable>"
            "<b>🏅 Performers</b>\n\n"
            f"{pw_rows.rstrip()}"
            "</blockquote>"
        )

    # Advice
    lines.append(
        "\n<blockquote expandable>"
        f"<b>💡 Portfolio Advice</b>\n\n"
        f"  Score   <code>{analysis['div_score']}/100</code>  {analysis['div_label']}\n"
        f"  Advice  <i>{esc(analysis['advice'])}</i>"
        "</blockquote>"
    )

    lines += [
        "",
        SEP,
        "<i>Add: /addstock NABIL 10 1200 · Remove: /removestock &lt;id&gt;</i>",
        "<i>Prices are live NEPSE market data</i>",
    ]
    return "\n".join(lines)


def format_empty_portfolio() -> str:
    return (
        "📊 <b>My NEPSE Portfolio</b>\n"
        f"{SEP}\n\n"
        "Your portfolio is empty.\n\n"
        "<b>How to add a stock:</b>\n"
        "<code>/addstock NABIL 10 1200</code>\n"
        "<code>/addstock NICA 25 800</code>\n"
        "<code>/addstock NLIC 5 3500 long-term</code>\n\n"
        "<i>Format: /addstock SYMBOL SHARES BUY_PRICE [note]</i>\n\n"
        f"{SEP}\n"
        "<i>Prices update live from NEPSE market data.</i>"
    )


def format_holdings_list(holdings: list) -> str:
    if not holdings:
        return format_empty_portfolio()
    lines = ["📋 <b>Holdings List</b>\n", ""]
    for h in holdings:
        dt = h["added_at"][:10]
        lines.append(
            f"<code>#{h['id']}</code>  <b>{esc(h['symbol'])}</b>  "
            f"<code>{h['shares']:,g}</code> shares @ <code>रु {fp(h['buy_price'])}</code>"
            f"  <i>{dt}</i>"
        )
        if h.get("note"):
            lines.append(f"  <i>{esc(h['note'])}</i>")
    lines += [
        "",
        "<i>Remove: /removestock &lt;id&gt;</i>",
        "<i>Clear all: /clearportfolio</i>",
    ]
    return "\n".join(lines)


async def build_portfolio_analysis(user_id: str) -> str:
    from utils.db import get_holdings
    from layers.nepse_data import fetch_prices_bulk
    holdings = await get_holdings(user_id)
    if not holdings:
        return format_empty_portfolio()
    symbols = list({h["symbol"].upper() for h in holdings})
    prices  = await fetch_prices_bulk(symbols)
    analysis = analyze_portfolio(holdings, prices)
    return format_portfolio_html(analysis)
