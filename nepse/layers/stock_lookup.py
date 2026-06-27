"""
Deep dive on a single NEPSE stock.
Combines market data + fundamental metrics + simple TA signals.
"""
import asyncio
from layers.nepse_data import fetch_stock_detail, fetch_market_summary
from utils.fmt import esc, npr, fp, pct, npt_now, change_icon, SEP


def _risk_label(v: float, mid: float, high: float) -> str:
    if v >= high: return "🔴 High"
    if v >= mid:  return "🟠 Moderate"
    return "🟢 Low"


def _signal(ltp: float, wk52_low: float, wk52_high: float, sma: float) -> str:
    if not ltp: return "⚪ No Data"
    signals = []
    if wk52_low and ltp <= wk52_low * 1.05:
        signals.append("🔔 Near 52W Low")
    if wk52_high and ltp >= wk52_high * 0.95:
        signals.append("⚠️ Near 52W High")
    if sma and ltp > sma:
        signals.append("📈 Above MA")
    elif sma and ltp < sma:
        signals.append("📉 Below MA")
    return "  ".join(signals) if signals else "⚪ Neutral"


async def build_stock_deep_dive(symbol: str) -> str:
    symbol = symbol.upper().strip()

    # Try to get from market summary first (fast)
    summary_data = await fetch_market_summary()
    turnover = summary_data.get("turnover", {}).get("detail", [])
    basic = next((s for s in turnover if s.get("s", "").upper() == symbol), None)

    # Also try stock detail endpoint
    detail = await fetch_stock_detail(symbol)

    if not basic and not detail:
        return f"⚠️ Stock <b>{esc(symbol)}</b> not found. Check the symbol and try again."

    # Extract from basic market data
    ltp    = float((basic or {}).get("lp", 0) or (detail or {}).get("lp", 0) or 0)
    pc     = float((basic or {}).get("pc", 0) or 0)
    high   = float((basic or {}).get("h", 0) or 0)
    low    = float((basic or {}).get("l", 0) or 0)
    open_p = float((basic or {}).get("op", 0) or 0)
    vol    = int(float((basic or {}).get("q", 0) or 0))
    t_npr  = float((basic or {}).get("t", 0) or 0)

    # From detail endpoint (may be empty if endpoint returns nothing)
    eps       = float((detail or {}).get("eps", 0) or 0)
    pe        = float((detail or {}).get("pe", 0) or 0)
    book_val  = float((detail or {}).get("bv", 0) or 0)
    wk52_h    = float((detail or {}).get("wh", 0) or 0)
    wk52_l    = float((detail or {}).get("wl", 0) or 0)
    listed    = (detail or {}).get("ls", "")
    sector    = (detail or {}).get("sector", "") or (detail or {}).get("sn", "")
    div       = float((detail or {}).get("div", 0) or 0)
    bonus     = float((detail or {}).get("bonus", 0) or 0)
    shares    = float((detail or {}).get("listedShares", 0) or 0)

    # Derived
    pbv    = (ltp / book_val) if book_val > 0 else 0
    sma_approx = (high + low) / 2 if high and low else 0
    mktcap = ltp * shares if ltp and shares else 0

    # Change from open
    day_change = ltp - open_p if open_p else 0

    icon = change_icon(pc)

    def _mill(v):
        if v >= 10_000_000: return f"रु {v/10_000_000:.2f}Cr"
        if v >= 100_000:    return f"रु {v/100_000:.2f}L"
        return f"रु {v:,.0f}"

    lines = [
        f"📋 <b>Stock Deep Dive — {esc(symbol)}</b>",
        SEP,
        f"<i>{npt_now()}</i>",
        "",
        f"<b>LTP</b>  <code>रु {fp(ltp)}</code>  {icon} <code>{pct(pc)}</code>",
        f"<b>Day</b>  O <code>{fp(open_p)}</code>  H <code>{fp(high)}</code>  L <code>{fp(low)}</code>",
    ]
    if sector:
        lines.append(f"<b>Sector</b>  <i>{esc(sector)}</i>")
    lines.append("")

    # Price performance block
    perf_rows = f"  Day Change    <code>रु {fp(abs(day_change))}</code>  <code>{pct(pc)}</code>\n"
    if wk52_h: perf_rows += f"  52W High      <code>रु {fp(wk52_h)}</code>\n"
    if wk52_l: perf_rows += f"  52W Low       <code>रु {fp(wk52_l)}</code>\n"
    if wk52_h and wk52_l and ltp:
        pos_in_range = ((ltp - wk52_l) / (wk52_h - wk52_l) * 100) if (wk52_h - wk52_l) > 0 else 0
        perf_rows += f"  Range Pos     <code>{pos_in_range:.1f}%</code>  (0=52W Low, 100=52W High)\n"

    lines.append(
        "<blockquote expandable>"
        "<b>📊 Price Performance</b>\n\n"
        f"{perf_rows.rstrip()}"
        "</blockquote>"
    )

    # Fundamentals block
    if eps or pe or book_val:
        fund_rows = ""
        if eps:      fund_rows += f"  EPS         <code>रु {fp(eps)}</code>\n"
        if pe:       fund_rows += f"  P/E Ratio   <code>{fp(pe)}x</code>\n"
        if book_val: fund_rows += f"  Book Value  <code>रु {fp(book_val)}</code>\n"
        if pbv:      fund_rows += f"  P/BV        <code>{pbv:.2f}x</code>\n"
        if div:      fund_rows += f"  Dividend    <code>{div:.2f}%</code>\n"
        if bonus:    fund_rows += f"  Bonus       <code>{bonus:.2f}%</code>\n"
        if mktcap:   fund_rows += f"  Market Cap  <code>{_mill(mktcap)}</code>\n"
        if shares:   fund_rows += f"  Listed Sh.  <code>{shares:,.0f}</code>\n"

        lines.append(
            "\n<blockquote expandable>"
            "<b>📈 Fundamentals</b>\n\n"
            f"{fund_rows.rstrip()}"
            "</blockquote>"
        )

    # Trading data block
    trade_rows = f"  Volume       <code>{vol:,}</code> shares\n"
    if t_npr: trade_rows += f"  Turnover     <code>{_mill(t_npr)}</code>\n"
    if listed: trade_rows += f"  Listed       <i>{esc(listed)}</i>\n"

    lines.append(
        "\n<blockquote expandable>"
        "<b>💹 Trading Data</b>\n\n"
        f"{trade_rows.rstrip()}"
        "</blockquote>"
    )

    # TA signal block
    signal_txt = _signal(ltp, wk52_l, wk52_h, sma_approx)
    # Valuation signal
    val_signal = ""
    if pe > 0:
        if pe < 10:   val_signal = "🟢 Potentially Undervalued (P/E < 10)"
        elif pe < 20: val_signal = "🟡 Fairly Valued (P/E 10–20)"
        elif pe < 30: val_signal = "🟠 Slightly Overvalued (P/E 20–30)"
        else:         val_signal = "🔴 High Valuation (P/E > 30)"

    # Circuit breaker check
    from config import CIRCUIT_LIMIT_PCT
    circuit = ""
    if abs(pc) >= CIRCUIT_LIMIT_PCT * 0.9:
        circuit = f"\n⚡ <b>Near Circuit Limit!</b> ({CIRCUIT_LIMIT_PCT}%)"

    ta_rows = f"  Signal       {signal_txt}\n"
    if val_signal: ta_rows += f"  Valuation    {val_signal}\n"
    ta_rows += f"  Mid Range    <code>रु {fp(sma_approx)}</code>  (avg of day H/L)\n"

    lines.append(
        "\n<blockquote expandable>"
        "<b>🔬 TA &amp; Signals</b>\n\n"
        f"{ta_rows.rstrip()}"
        f"{circuit}"
        "</blockquote>"
    )

    lines += [
        "",
        SEP,
        f"<i>Use /addstock {esc(symbol)} to add to portfolio · /watch {esc(symbol)} for alerts</i>",
        "<i>Data: merolagani.com · DYOR</i>",
    ]
    return "\n".join(lines)
