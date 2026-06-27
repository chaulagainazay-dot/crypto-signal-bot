"""Trading calculators — position size, RR, profit, DCA, compound, liquidation, funding, fee."""

from utils.fmt import fp


def calc_position_size(account: float, risk_pct: float, entry: float, stop: float) -> str:
    """Calculate position size given account, risk %, entry, stop loss."""
    risk_amount = account * (risk_pct / 100)
    diff = abs(entry - stop)
    if diff == 0:
        return "❌ Entry and stop loss cannot be the same price."
    stop_pct = diff / entry * 100
    position_usd = risk_amount / (diff / entry)
    quantity = position_usd / entry
    return (
        f"📏 <b>Position Size Calculator</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Inputs:</b>\n"
        f"  Account:     <code>${account:,.2f}</code>\n"
        f"  Risk:        <code>{risk_pct}%  →  ${risk_amount:,.2f}</code>\n"
        f"  Entry:       <code>${fp(entry)}</code>\n"
        f"  Stop Loss:   <code>${fp(stop)}</code>\n\n"
        f"<b>Results:</b>\n"
        f"  Stop Distance:  <code>{stop_pct:.2f}%  (${diff:,.4f})</code>\n"
        f"  Position Size:  <code>${position_usd:,.2f}</code>\n"
        f"  Quantity:       <code>{quantity:.6f} coins</code>\n"
        f"  Max Loss:       <code>${risk_amount:,.2f}</code>\n\n"
        f"💡 <i>If price hits your stop, you lose ${risk_amount:,.2f} ({risk_pct}% of account)</i>"
    )


def calc_risk_reward(entry: float, stop: float, tp1: float, tp2: float = None) -> str:
    """Calculate risk:reward ratio."""
    risk = abs(entry - stop)
    reward1 = abs(tp1 - entry)
    if risk == 0:
        return "❌ Entry and stop loss cannot be the same."

    rr1 = reward1 / risk
    result = (
        f"🎯 <b>Risk:Reward Calculator</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Entry:</b>   <code>${fp(entry)}</code>\n"
        f"<b>Stop Loss:</b> <code>${fp(stop)}</code>\n"
        f"<b>TP1:</b>     <code>${fp(tp1)}</code>\n\n"
        f"<b>Risk:</b>   <code>${fp(risk)}</code>\n"
        f"<b>Reward1:</b> <code>${fp(reward1)}</code>\n"
        f"<b>RR Ratio:</b> <code>1:{rr1:.1f}</code>  {'✅' if rr1 >= 2 else '⚠️ Low RR'}\n"
    )
    if tp2:
        reward2 = abs(tp2 - entry)
        rr2 = reward2 / risk
        result += f"<b>TP2:</b>     <code>${fp(tp2)}</code>  →  <code>1:{rr2:.1f}</code>\n"

    result += f"\n<b>Win rate needed to break even:</b> <code>{100/(1+rr1):.1f}%</code>\n"
    result += "\n💡 <i>Minimum 1:2 RR recommended. Aim for 1:3.</i>"
    return result


def calc_profit(entry: float, exit_price: float, quantity: float, leverage: float = 1.0) -> str:
    """Calculate profit/loss from a trade."""
    direction = "LONG" if exit_price > entry else "SHORT"
    if direction == "LONG":
        pct_change = (exit_price - entry) / entry * 100
    else:
        pct_change = (entry - exit_price) / entry * 100

    leveraged_pct = pct_change * leverage
    invested = entry * quantity
    pnl = invested * (leveraged_pct / 100)
    emoji = "✅" if pnl > 0 else "❌"

    return (
        f"💰 <b>Profit Calculator</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Direction:</b>  <code>{direction}</code>\n"
        f"<b>Entry:</b>      <code>${fp(entry)}</code>\n"
        f"<b>Exit:</b>       <code>${fp(exit_price)}</code>\n"
        f"<b>Quantity:</b>   <code>{quantity} coins</code>\n"
        f"<b>Leverage:</b>   <code>{leverage}x</code>\n\n"
        f"<b>Invested:</b>   <code>${invested:,.2f}</code>\n"
        f"<b>Price change:</b> <code>{pct_change:+.2f}%</code>\n"
        f"<b>Leveraged:</b>  <code>{leveraged_pct:+.2f}%</code>\n"
        f"<b>PnL:</b>        <code>${pnl:+,.2f}  {emoji}</code>\n\n"
        f"<b>Final value:</b> <code>${invested + pnl:,.2f}</code>"
    )


def calc_dca(entries: list[tuple[float, float]]) -> str:
    """Calculate DCA average entry. entries = [(price, amount_usd), ...]"""
    if not entries:
        return "❌ No entries provided."
    total_usd = sum(amt for _, amt in entries)
    total_coins = sum(amt / price for price, amt in entries)
    avg_price = total_usd / total_coins

    result = (
        f"📉 <b>DCA Calculator</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
    )
    for i, (price, amt) in enumerate(entries, 1):
        coins = amt / price
        result += f"<b>Entry {i}:</b> <code>${fp(price)}</code> × <code>${amt:,.2f}</code> = <code>{coins:.6f} coins</code>\n"

    result += (
        f"\n<b>Total invested:</b> <code>${total_usd:,.2f}</code>\n"
        f"<b>Total coins:</b>   <code>{total_coins:.6f}</code>\n"
        f"<b>Average price:</b> <code>${fp(avg_price)}</code>\n\n"
        f"💡 <i>If price is above ${fp(avg_price)}, your DCA is profitable.</i>"
    )
    return result


def calc_compound(principal: float, rate_pct: float, periods: int, period_label: str = "month") -> str:
    """Calculate compound interest growth."""
    value = principal
    rows = []
    for i in range(1, min(periods + 1, 13)):
        value *= (1 + rate_pct / 100)
        rows.append((i, value))

    result = (
        f"📈 <b>Compound Growth Calculator</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Principal:</b>   <code>${principal:,.2f}</code>\n"
        f"<b>Rate/period:</b> <code>{rate_pct}%</code>\n"
        f"<b>Periods:</b>     <code>{periods} {period_label}s</code>\n\n"
        f"<b>Growth:</b>\n"
    )
    for period, val in rows:
        gain = val - principal
        result += f"  {period_label.capitalize()} {period}: <code>${val:,.2f}</code>  (+${gain:,.2f})\n"

    if periods > 12:
        value_final = principal * ((1 + rate_pct / 100) ** periods)
        result += f"  ...\n  {period_label.capitalize()} {periods}: <code>${value_final:,.2f}</code>\n"
        gain_final = value_final - principal
        result += f"\n<b>Total gain:</b> <code>${gain_final:,.2f} (+{gain_final/principal*100:.1f}%)</code>\n"

    return result


def calc_liquidation(entry: float, leverage: float, direction: str = "long",
                     maintenance_margin: float = 0.5) -> str:
    """Calculate liquidation price."""
    mm_rate = maintenance_margin / 100
    if direction.lower() == "long":
        liq_price = entry * (1 - (1 / leverage) + mm_rate)
        distance = (entry - liq_price) / entry * 100
        safe_stop = entry * (1 - 0.5 / leverage)
    else:
        liq_price = entry * (1 + (1 / leverage) - mm_rate)
        distance = (liq_price - entry) / entry * 100
        safe_stop = entry * (1 + 0.5 / leverage)

    return (
        f"💀 <b>Liquidation Calculator</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Direction:</b>  <code>{direction.upper()}</code>\n"
        f"<b>Entry:</b>      <code>${fp(entry)}</code>\n"
        f"<b>Leverage:</b>   <code>{leverage}x</code>\n\n"
        f"<b>Liquidation at:</b>  <code>${fp(liq_price)}</code>\n"
        f"<b>Distance:</b>        <code>{distance:.2f}%</code>\n"
        f"<b>Safe stop loss:</b>  <code>${fp(safe_stop)}</code>\n\n"
        f"⚠️ <i>Keep stop loss well above/below liquidation price.\n"
        f"Maintenance margin varies by exchange.</i>"
    )


def calc_funding(position_usd: float, funding_rate: float, periods: int = 3) -> str:
    """Estimate funding fee cost."""
    fee_per_period = position_usd * (funding_rate / 100)
    total = fee_per_period * periods
    daily = fee_per_period * 3  # 3 funding periods per day

    return (
        f"💸 <b>Funding Fee Calculator</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Position size:</b>  <code>${position_usd:,.2f}</code>\n"
        f"<b>Funding rate:</b>   <code>{funding_rate:+.4f}%</code> per 8h\n\n"
        f"<b>Per period (8h):</b> <code>${fee_per_period:+,.4f}</code>\n"
        f"<b>Daily (3x):</b>     <code>${daily:+,.4f}</code>\n"
        f"<b>Weekly:</b>         <code>${daily*7:+,.4f}</code>\n"
        f"<b>Monthly:</b>        <code>${daily*30:+,.4f}</code>\n\n"
        f"<i>{'⚠️ You PAY funding (long in bullish market)' if funding_rate > 0 else '✅ You RECEIVE funding (long in bearish market)'}</i>"
    )


def calc_fee(position_usd: float, exchange: str = "bybit") -> str:
    """Estimate trading fees."""
    fees = {
        "bybit":   {"maker": 0.02, "taker": 0.055},
        "binance": {"maker": 0.02, "taker": 0.04},
        "okx":     {"maker": 0.02, "taker": 0.05},
        "kucoin":  {"maker": 0.02, "taker": 0.06},
    }
    f = fees.get(exchange.lower(), fees["bybit"])
    maker_fee = position_usd * (f["maker"] / 100)
    taker_fee = position_usd * (f["taker"] / 100)
    round_trip_maker = maker_fee * 2
    round_trip_taker = taker_fee * 2

    return (
        f"💳 <b>Fee Calculator — {exchange.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Position:</b> <code>${position_usd:,.2f}</code>\n\n"
        f"<b>Maker fee ({f['maker']}%):</b>\n"
        f"  One way: <code>${maker_fee:,.4f}</code>\n"
        f"  Round trip: <code>${round_trip_maker:,.4f}</code>\n\n"
        f"<b>Taker fee ({f['taker']}%):</b>\n"
        f"  One way: <code>${taker_fee:,.4f}</code>\n"
        f"  Round trip: <code>${round_trip_taker:,.4f}</code>\n\n"
        f"💡 <i>Limit orders = maker fee (cheaper). Market orders = taker fee.</i>"
    )
