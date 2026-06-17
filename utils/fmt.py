"""
Shared formatting utilities — single source of truth for all message styles.
Every message in the bot uses these helpers to ensure consistent, clean output.
"""
from datetime import datetime, timezone, timedelta


# ── Time helpers ──────────────────────────────────────────────────────────────

def npt_now(fmt: str = "%I:%M %p NPT · %a %b %d") -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime(fmt)

def npt_time() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime("%I:%M %p NPT")

def npt_date() -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)).strftime("%b %d, %Y")


# ── Number formatters ─────────────────────────────────────────────────────────

def fp(price: float) -> str:
    """Format price with smart decimal places."""
    if price >= 100_000: return f"${price:,.0f}"
    if price >= 10_000:  return f"${price:,.0f}"
    if price >= 1_000:   return f"${price:,.1f}"
    if price >= 100:     return f"${price:,.2f}"
    if price >= 1:       return f"${price:,.3f}"
    if price >= 0.01:    return f"${price:.4f}"
    return f"${price:.6f}"

def fpn(price: float) -> str:
    """Same as fp but no $ sign."""
    return fp(price).lstrip("$")

def pct(v: float, sign: bool = True) -> str:
    """Format percentage, e.g. +2.34%"""
    return f"{v:+.2f}%" if sign else f"{v:.2f}%"

def mill(n: float) -> str:
    """Format large numbers: 1.23B, 456.7M, 12.3K"""
    if n >= 1e12: return f"${n/1e12:.2f}T"
    if n >= 1e9:  return f"${n/1e9:.2f}B"
    if n >= 1e6:  return f"${n/1e6:.1f}M"
    if n >= 1e3:  return f"${n/1e3:.0f}K"
    return f"${n:.0f}"

def mill_raw(n: float) -> str:
    """mill without $ sign."""
    return mill(n).lstrip("$")


# ── Status icons ──────────────────────────────────────────────────────────────

def trend_icon(v: float, threshold: float = 0) -> str:
    return "🟢" if v > threshold else ("🔴" if v < threshold else "⚪")

def pct_icon(v: float) -> str:
    return "🟢" if v >= 0 else "🔴"

def score_grade(s: float) -> str:
    """0-100 score → grade string."""
    if s >= 80: return "🟢 A+"
    if s >= 70: return "🟢 A"
    if s >= 60: return "🟡 B"
    if s >= 50: return "🟠 C"
    return "🔴 D"

def signal_outcome_icon(outcome: str) -> str:
    return {"pending": "⏳", "tp1": "🎯", "tp2": "✅", "sl": "❌", "expired": "💨"}.get(outcome, "⏳")


# ── Layout helpers ────────────────────────────────────────────────────────────

SEP  = "━━━━━━━━━━━━━━━━━━"
SEP2 = "──────────────────"

def header(emoji: str, title: str) -> str:
    return f"{emoji} *{title}*\n{SEP}"

def subheader(title: str) -> str:
    return f"*{title}*\n{SEP2}"

def row(label: str, value: str, icon: str = "") -> str:
    """Aligned data row: `Label   value  icon`"""
    pad = max(1, 12 - len(label))
    return f"`{label}{'·' * pad}{value}`  {icon}".rstrip()

def kv(key: str, val: str) -> str:
    """Bold key + code value: *Key:* `val`"""
    return f"*{key}:* `{val}`"

def bullet(text: str) -> str:
    return f"  • {text}"

def note(text: str) -> str:
    return f"_{text}_"

def footer(text: str = "DYOR · Paper trade first · Max 2% risk per trade") -> str:
    return f"{SEP}\n_{text}_"
