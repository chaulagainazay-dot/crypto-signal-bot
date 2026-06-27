"""Shared formatting helpers for NEPSE bot."""
from datetime import datetime, timezone, timedelta

SEP  = "━━━━━━━━━━━━━━━━━━"
SEP2 = "──────────────────"

def esc(t) -> str:
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def npr(amount: float) -> str:
    """Format NPR amount: रु 1,23,456.78"""
    if amount == 0: return "रु 0"
    if amount >= 10_000_000: return f"रु {amount/10_000_000:.2f} Cr"
    if amount >= 100_000:    return f"रु {amount/100_000:.2f} L"
    if amount >= 1000:       return f"रु {amount:,.2f}"
    return f"रु {amount:.2f}"

def fp(p: float) -> str:
    """Format price (no currency symbol)."""
    if not p: return "0"
    if p >= 10000: return f"{p:,.0f}"
    if p >= 100:   return f"{p:,.2f}"
    return f"{p:.2f}"

def pct(v: float) -> str:
    """Format percent with sign and arrow."""
    arrow = "▲" if v >= 0 else "▼"
    return f"{arrow} {abs(v):.2f}%"

def npt_now() -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)
    return dt.strftime("%I:%M %p NPT · %a %b %d, %Y")

def npt_date() -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)
    return dt.strftime("%Y-%m-%d")

def is_market_open() -> bool:
    from config import MARKET_OPEN_UTC, MARKET_CLOSE_UTC, MARKET_DAYS
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # Mon=0 ... Sun=6
    if weekday not in MARKET_DAYS:
        return False
    open_min  = MARKET_OPEN_UTC[0] * 60  + MARKET_OPEN_UTC[1]
    close_min = MARKET_CLOSE_UTC[0] * 60 + MARKET_CLOSE_UTC[1]
    cur_min   = now.hour * 60 + now.minute
    return open_min <= cur_min <= close_min

def market_status_badge() -> str:
    return "🟢 <b>OPEN</b>" if is_market_open() else "🔴 <b>CLOSED</b>"

def change_icon(pc: float) -> str:
    if pc > 5:   return "🚀"
    if pc > 2:   return "📈"
    if pc > 0:   return "🟢"
    if pc < -5:  return "💥"
    if pc < -2:  return "📉"
    if pc < 0:   return "🔴"
    return "⚪"

def pnl_icon(v: float) -> str:
    return "🟢" if v >= 0 else "🔴"
