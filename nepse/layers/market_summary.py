"""NEPSE market overview: index, turnover, top gainers/losers, sector breakdown."""
from layers.nepse_data import fetch_market_summary
from utils.fmt import esc, npr, fp, pct, npt_now, market_status_badge, change_icon, SEP


def _mill(v: float) -> str:
    if v >= 1_000_000_000: return f"रु {v/1_000_000_000:.2f} Arba"
    if v >= 10_000_000:    return f"रु {v/10_000_000:.2f} Cr"
    if v >= 100_000:       return f"रु {v/100_000:.2f} L"
    return f"रु {v:,.0f}"


async def build_market_overview() -> str:
    data = await fetch_market_summary()
    if not data:
        return "⚠️ Could not fetch NEPSE data. Please try again."

    overall  = data.get("overall", {})
    turnover = data.get("turnover", {}).get("detail", [])
    sectors  = data.get("sector", {}).get("detail", []) if isinstance(data.get("sector"), dict) else data.get("sector", [])

    total_turnover = float(overall.get("t", 0))
    total_qty      = int(float(overall.get("q", 0)))
    total_txn      = int(float(overall.get("tn", 0)))
    stocks_traded  = int(float(overall.get("st", 0)))
    market_cap     = float(overall.get("mc", 0))

    # Sort gainers/losers
    stocks_with_pc = [s for s in turnover if s.get("pc") is not None]
    gainers = sorted(stocks_with_pc, key=lambda x: x.get("pc", 0), reverse=True)[:5]
    losers  = sorted(stocks_with_pc, key=lambda x: x.get("pc", 0))[:5]

    lines = [
        "🏛️ <b>NEPSE Market Overview</b>",
        SEP,
        f"<i>{npt_now()}</i>",
        f"Market  {market_status_badge()}",
        "",
        f"<b>Market Cap</b>    <code>{_mill(market_cap)}</code>",
        f"<b>Turnover</b>      <code>{_mill(total_turnover)}</code>",
        f"<b>Transactions</b>  <code>{total_txn:,}</code>",
        f"<b>Volume</b>        <code>{total_qty:,}</code> shares",
        f"<b>Stocks Traded</b> <code>{stocks_traded}</code>",
        "",
    ]

    # Top 5 Gainers block
    g_rows = ""
    for s in gainers:
        icon = change_icon(s.get("pc", 0))
        g_rows += f"  {icon} <b>{esc(s['s'])}</b>  <code>{fp(s.get('lp',0))}</code>  <code>{pct(s.get('pc',0))}</code>\n"

    lines.append(
        "<blockquote expandable>"
        "<b>🚀 Top Gainers</b>\n\n"
        f"{g_rows.rstrip()}"
        "</blockquote>"
    )

    # Top 5 Losers block
    l_rows = ""
    for s in losers:
        icon = change_icon(s.get("pc", 0))
        l_rows += f"  {icon} <b>{esc(s['s'])}</b>  <code>{fp(s.get('lp',0))}</code>  <code>{pct(s.get('pc',0))}</code>\n"

    lines.append(
        "\n<blockquote expandable>"
        "<b>📉 Top Losers</b>\n\n"
        f"{l_rows.rstrip()}"
        "</blockquote>"
    )

    # Sector breakdown
    if sectors:
        sec_rows = ""
        sectors_sorted = sorted(sectors, key=lambda x: float(x.get("t",0)), reverse=True)
        for sec in sectors_sorted[:12]:
            name = esc(sec.get("s") or sec.get("n") or sec.get("sn") or "")
            tv   = float(sec.get("t") or sec.get("turnover") or 0)
            qty  = int(float(sec.get("q") or 0))
            sec_rows += f"  💰 <b>{name}</b>  <code>{_mill(tv)}</code>  <i>{qty:,} shares</i>\n"

        lines.append(
            "\n<blockquote expandable>"
            "<b>🗂️ Sector Performance</b>\n\n"
            f"{sec_rows.rstrip()}"
            "</blockquote>"
        )

    # Top by turnover
    top_t = sorted(turnover, key=lambda x: x.get("t", 0), reverse=True)[:5]
    tr_rows = ""
    for s in top_t:
        tr_rows += f"  💰 <b>{esc(s['s'])}</b>  <code>{_mill(float(s.get('t',0)))}</code>  LTP <code>{fp(s.get('lp',0))}</code>\n"

    lines.append(
        "\n<blockquote expandable>"
        "<b>💰 Most Traded (Turnover)</b>\n\n"
        f"{tr_rows.rstrip()}"
        "</blockquote>"
    )

    lines += [
        "",
        SEP,
        "<i>Data: merolagani.com · Sun–Thu 11AM–3PM NPT</i>",
    ]
    return "\n".join(lines)


async def build_gainers_losers(mode: str = "gainers") -> str:
    data = await fetch_market_summary()
    if not data:
        return "⚠️ Could not fetch NEPSE data."

    turnover = data.get("turnover", {}).get("detail", [])
    stocks = [s for s in turnover if s.get("pc") is not None]

    if mode == "gainers":
        stocks = sorted(stocks, key=lambda x: x.get("pc", 0), reverse=True)[:15]
        title  = "🚀 <b>Top Gainers</b>"
    else:
        stocks = sorted(stocks, key=lambda x: x.get("pc", 0))[:15]
        title  = "📉 <b>Top Losers</b>"

    lines = [title, SEP, f"<i>{npt_now()}</i>", ""]
    for i, s in enumerate(stocks, 1):
        icon = change_icon(s.get("pc", 0))
        h = fp(s.get("h", 0))
        l = fp(s.get("l", 0))
        lines.append(
            f"{i:>2}. {icon} <b>{esc(s['s'])}</b>\n"
            f"     LTP <code>{fp(s.get('lp',0))}</code>  Change <code>{pct(s.get('pc',0))}</code>\n"
            f"     H <code>{h}</code>  L <code>{l}</code>  Vol <code>{int(s.get('q',0)):,}</code>"
        )

    lines += ["", SEP, "<i>Data: merolagani.com</i>"]
    return "\n".join(lines)
