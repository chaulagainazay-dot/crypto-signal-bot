"""Weekly NEPSE market summary report."""
from layers.nepse_data import fetch_market_summary
from utils.fmt import esc, fp, pct, npt_now, change_icon, SEP


async def build_weekly_report() -> str:
    data = await fetch_market_summary()
    if not data:
        return "⚠️ Could not build weekly report — no market data."

    overall  = data.get("overall", {})
    turnover = data.get("turnover", {}).get("detail", [])
    sectors  = data.get("sector", {}).get("detail", []) if isinstance(data.get("sector"), dict) else data.get("sector", [])

    total_turnover = float(overall.get("t", 0))
    total_qty      = int(float(overall.get("q", 0)))
    total_txn      = int(float(overall.get("tn", 0)))
    stocks_traded  = int(float(overall.get("st", 0)))
    market_cap     = float(overall.get("mc", 0))

    def _mill(v):
        if v >= 10_000_000: return f"रु {v/10_000_000:.2f}Cr"
        if v >= 100_000:    return f"रु {v/100_000:.2f}L"
        return f"रु {v:,.0f}"

    stocks_with_pc = [s for s in turnover if s.get("pc") is not None]
    gainers = sorted(stocks_with_pc, key=lambda x: x.get("pc", 0), reverse=True)[:10]
    losers  = sorted(stocks_with_pc, key=lambda x: x.get("pc", 0))[:5]
    top_vol = sorted(turnover, key=lambda x: x.get("t", 0), reverse=True)[:10]

    # Market sentiment
    pos = sum(1 for s in stocks_with_pc if s.get("pc", 0) > 0)
    neg = sum(1 for s in stocks_with_pc if s.get("pc", 0) < 0)
    neutral = len(stocks_with_pc) - pos - neg
    if pos > neg * 1.5:  sentiment = "🟢 Bullish"
    elif neg > pos * 1.5: sentiment = "🔴 Bearish"
    else:                sentiment = "🟡 Mixed/Sideways"

    lines = [
        "📊 <b>NEPSE Weekly Report</b>",
        SEP,
        f"<i>{npt_now()}</i>",
        "",
        f"<b>Market Cap</b>    <code>{_mill(market_cap)}</code>",
        f"<b>Turnover</b>      <code>{_mill(total_turnover)}</code>",
        f"<b>Transactions</b>  <code>{total_txn:,}</code>",
        f"<b>Stocks Traded</b> <code>{stocks_traded}</code>",
        f"<b>Sentiment</b>     {sentiment}",
        f"<b>Breadth</b>       🟢 <code>{pos}</code>  🔴 <code>{neg}</code>  ⚪ <code>{neutral}</code>",
        "",
    ]

    # Top gainers block
    g_rows = ""
    for s in gainers:
        icon = change_icon(s.get("pc", 0))
        g_rows += f"  {icon} <b>{esc(s['s'])}</b>  <code>रु {fp(s.get('lp',0))}</code>  <code>{pct(s.get('pc',0))}</code>\n"
    lines.append(
        "<blockquote expandable>"
        "<b>🚀 Top Gainers</b>\n\n"
        f"{g_rows.rstrip()}"
        "</blockquote>"
    )

    # Top losers block
    l_rows = ""
    for s in losers:
        icon = change_icon(s.get("pc", 0))
        l_rows += f"  {icon} <b>{esc(s['s'])}</b>  <code>रु {fp(s.get('lp',0))}</code>  <code>{pct(s.get('pc',0))}</code>\n"
    lines.append(
        "\n<blockquote expandable>"
        "<b>📉 Top Losers</b>\n\n"
        f"{l_rows.rstrip()}"
        "</blockquote>"
    )

    # Top by turnover
    tv_rows = ""
    for s in top_vol:
        tv_rows += f"  💰 <b>{esc(s['s'])}</b>  <code>{_mill(float(s.get('t',0)))}</code>  LTP <code>रु {fp(s.get('lp',0))}</code>\n"
    lines.append(
        "\n<blockquote expandable>"
        "<b>💰 Most Traded Stocks</b>\n\n"
        f"{tv_rows.rstrip()}"
        "</blockquote>"
    )

    # Sector block
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

    lines += [
        "",
        SEP,
        "<i>Data: merolagani.com · NEPSE Sun–Thu 11AM–3PM NPT · DYOR</i>",
    ]
    return "\n".join(lines)
