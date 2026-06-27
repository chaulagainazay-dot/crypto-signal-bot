"""Price alert management for NEPSE stocks."""
import logging
from layers.nepse_data import fetch_prices_bulk
from utils.fmt import esc, fp, SEP

log = logging.getLogger(__name__)


def parse_alert_command(text: str) -> dict:
    """Parse /alert NABIL above 1500  or  /alert NICA below 700"""
    parts = text.strip().split()
    if len(parts) < 4:
        return None
    try:
        symbol    = parts[1].upper()
        condition = parts[2].lower()
        price     = float(parts[3].replace(",", ""))
        if condition not in ("above", "below"):
            return None
        return {"symbol": symbol, "condition": condition, "target_price": price}
    except (ValueError, IndexError):
        return None


def format_alerts_list(alerts: list) -> str:
    if not alerts:
        return (
            "🔔 <b>My Price Alerts</b>\n"
            f"{SEP}\n\n"
            "No active alerts.\n\n"
            "<b>Set an alert:</b>\n"
            "<code>/alert NABIL above 1500</code>\n"
            "<code>/alert NICA below 700</code>"
        )
    lines = ["🔔 <b>My Price Alerts</b>", SEP, ""]
    for a in alerts:
        cond = "▲ above" if a["condition"] == "above" else "▼ below"
        lines.append(
            f"<code>#{a['id']}</code>  <b>{esc(a['symbol'])}</b>  {cond}  <code>रु {fp(a['target_price'])}</code>"
        )
    lines += ["", f"<i>Remove: /delalert &lt;id&gt;</i>"]
    return "\n".join(lines)


async def check_alerts(bot, all_alerts: list):
    """Check all active alerts against live prices, fire notifications."""
    if not all_alerts:
        return
    from utils.db import trigger_alert

    symbols = list({a["symbol"].upper() for a in all_alerts})
    prices  = await fetch_prices_bulk(symbols)
    if not prices:
        return

    for alert in all_alerts:
        sym   = alert["symbol"].upper()
        ltp   = prices.get(sym, 0)
        if not ltp:
            continue
        target = alert["target_price"]
        cond   = alert["condition"]
        fired  = False

        if cond == "above" and ltp >= target:
            fired = True
            msg = (
                f"🔔 <b>Price Alert Triggered!</b>\n"
                f"<b>{esc(sym)}</b> is now <b>above रु {fp(target)}</b>\n"
                f"Current LTP: <code>रु {fp(ltp)}</code>"
            )
        elif cond == "below" and ltp <= target:
            fired = True
            msg = (
                f"🔔 <b>Price Alert Triggered!</b>\n"
                f"<b>{esc(sym)}</b> is now <b>below रु {fp(target)}</b>\n"
                f"Current LTP: <code>रु {fp(ltp)}</code>"
            )

        if fired:
            await trigger_alert(alert["id"])
            try:
                await bot.send_message(
                    chat_id=alert["user_id"],
                    text=msg,
                    parse_mode="HTML",
                )
            except Exception as e:
                log.warning("Alert send error: %s", e)
