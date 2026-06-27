"""Trade journal layer — record, analyse, and improve."""
import logging
from datetime import datetime, timezone
from utils.db import _get_pool

log = logging.getLogger(__name__)


async def add_journal_entry(chat_id: str, coin: str, direction: str, entry_price: float,
                            exit_price: float, size_usd: float, emotion: str,
                            mistakes: str, lessons: str) -> int:
    pool = await _get_pool()
    pnl_pct = ((exit_price - entry_price) / entry_price * 100) if direction == "LONG" \
              else ((entry_price - exit_price) / entry_price * 100)
    pnl_usd = size_usd * (pnl_pct / 100)
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO trade_journal
              (chat_id, coin, direction, entry_price, exit_price, size_usd,
               pnl_pct, pnl_usd, emotion, mistakes, lessons, traded_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            RETURNING id""",
            chat_id, coin.upper(), direction.upper(), entry_price, exit_price,
            size_usd, pnl_pct, pnl_usd, emotion, mistakes, lessons,
            datetime.now(timezone.utc).isoformat())
        return row["id"]


async def get_journal_entries(chat_id: str, limit: int = 20) -> list[dict]:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM trade_journal WHERE chat_id=$1 ORDER BY traded_at DESC LIMIT $2",
            chat_id, limit)
    return [dict(r) for r in rows]


async def get_journal_stats(chat_id: str) -> dict:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM trade_journal WHERE chat_id=$1 ORDER BY traded_at DESC",
            chat_id)
    entries = [dict(r) for r in rows]
    if not entries:
        return {}

    wins = [e for e in entries if e["pnl_pct"] > 0]
    losses = [e for e in entries if e["pnl_pct"] <= 0]
    total = len(entries)
    win_rate = len(wins) / total * 100 if total else 0
    avg_win = sum(e["pnl_pct"] for e in wins) / len(wins) if wins else 0
    avg_loss = sum(e["pnl_pct"] for e in losses) / len(losses) if losses else 0
    total_pnl = sum(e["pnl_usd"] for e in entries)

    # Common mistakes
    mistake_counts: dict[str, int] = {}
    for e in entries:
        if e["mistakes"]:
            for m in e["mistakes"].split(","):
                m = m.strip().lower()
                if m:
                    mistake_counts[m] = mistake_counts.get(m, 0) + 1

    top_mistakes = sorted(mistake_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    # Best coins
    coin_pnl: dict[str, float] = {}
    for e in entries:
        coin_pnl[e["coin"]] = coin_pnl.get(e["coin"], 0) + e["pnl_usd"]
    best_coins = sorted(coin_pnl.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "total": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "total_pnl_usd": total_pnl,
        "top_mistakes": top_mistakes,
        "best_coins": best_coins,
    }


def format_journal_stats(stats: dict) -> str:
    if not stats:
        return (
            "📊 <b>Trade Journal</b>\n\n"
            "No trades recorded yet.\n\n"
            "Use /journal to record your first trade."
        )
    wr = stats["win_rate"]
    wr_emoji = "🟢" if wr >= 60 else "🟡" if wr >= 40 else "🔴"
    pnl_emoji = "✅" if stats["total_pnl_usd"] > 0 else "❌"

    text = (
        f"📊 <b>Journal Analysis</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Total trades:</b>  <code>{stats['total']}</code>\n"
        f"<b>Win rate:</b>      <code>{wr:.1f}%</code>  {wr_emoji}\n"
        f"<b>Wins/Losses:</b>  <code>{stats['wins']}W / {stats['losses']}L</code>\n"
        f"<b>Avg win:</b>      <code>+{stats['avg_win_pct']:.2f}%</code>\n"
        f"<b>Avg loss:</b>     <code>{stats['avg_loss_pct']:.2f}%</code>\n"
        f"<b>Total PnL:</b>    <code>${stats['total_pnl_usd']:+,.2f}</code>  {pnl_emoji}\n"
    )
    if stats["top_mistakes"]:
        text += "\n<b>Common mistakes:</b>\n"
        for m, count in stats["top_mistakes"]:
            text += f"  • {m} ({count}x)\n"
    if stats["best_coins"]:
        text += "\n<b>Best coins:</b>\n"
        for coin, pnl in stats["best_coins"]:
            text += f"  • <code>{coin}</code>  ${pnl:+,.2f}\n"
    return text


def format_journal_list(entries: list[dict]) -> str:
    if not entries:
        return "📋 <b>Trade Journal</b>\n\nNo trades recorded yet."
    text = "📋 <b>Recent Trades</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for e in entries[:10]:
        pnl_emoji = "✅" if e["pnl_pct"] > 0 else "❌"
        date = e["traded_at"][:10]
        text += (
            f"{pnl_emoji} <b>#{e['id']}</b>  {e['coin']}  {e['direction']}\n"
            f"   Entry: <code>${e['entry_price']:,.4f}</code> → Exit: <code>${e['exit_price']:,.4f}</code>\n"
            f"   PnL: <code>{e['pnl_pct']:+.2f}%</code>  (${e['pnl_usd']:+,.2f})  <i>{date}</i>\n\n"
        )
    return text
