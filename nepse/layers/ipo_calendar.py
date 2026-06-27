"""IPO / FPO / Rights issue calendar."""
from layers.nepse_data import fetch_ipo_list
from utils.fmt import esc, SEP, npt_now


async def build_ipo_calendar() -> str:
    items = await fetch_ipo_list()

    lines = [
        "📅 <b>IPO / FPO / Rights Calendar</b>",
        SEP,
        f"<i>{npt_now()}</i>",
        "",
    ]

    if not items:
        lines.append("No active IPO/FPO issues at this time.")
        lines += ["", SEP, "<i>Data: merolagani.com</i>"]
        return "\n".join(lines)

    for item in items:
        # Try common field names from merolagani
        name      = esc(item.get("companyName") or item.get("name") or item.get("n") or "Unknown")
        symbol    = esc(item.get("symbol") or item.get("s") or "")
        type_     = esc(item.get("shareType") or item.get("type") or item.get("t") or "IPO")
        open_date = esc(item.get("openDate") or item.get("od") or "")
        close_date= esc(item.get("closeDate") or item.get("cd") or "")
        price     = item.get("issuePrice") or item.get("ip") or item.get("price") or 0
        units     = item.get("totalUnits") or item.get("units") or 0
        status    = esc(item.get("status") or "Open")

        row  = f"🏢 <b>{name}</b>"
        if symbol: row += f"  (<code>{symbol}</code>)"
        row += f"  [{type_}]\n"
        row += f"  Status  <b>{status}</b>\n"
        if open_date:  row += f"  Open    <code>{open_date}</code>\n"
        if close_date: row += f"  Close   <code>{close_date}</code>\n"
        if price:      row += f"  Price   <code>रु {price}</code>\n"
        if units:      row += f"  Units   <code>{int(float(units)):,}</code>\n"

        lines.append(row)

    lines += ["", SEP, "<i>Data: merolagani.com · Always verify with official SEBON notices</i>"]
    return "\n".join(lines)
