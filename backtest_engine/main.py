#!/usr/bin/env python3
"""
main.py
CLI entry point for the backtest engine.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from tabulate import tabulate
from tqdm import tqdm

from backtest_engine.backtester import Trade, run
from backtest_engine.data_fetcher import fetch_all, get_available_coins
from backtest_engine.indicators import add_indicators
from backtest_engine.metrics import by_coin, by_direction, calculate, monthly
from backtest_engine.report_generator import generate
from backtest_engine.signal_logic import generate_signals


def parse_date(date_str: Optional[str]) -> Optional[int]:
    """Convert YYYY-MM-DD string to epoch milliseconds."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date: {date_str}. Use YYYY-MM-DD.")


def main():
    parser = argparse.ArgumentParser(description="Crypto Signal Bot Backtest Engine")
    parser.add_argument(
        "--coins",
        nargs="+",
        default=get_available_coins(),
        help="Coins to backtest (default: all 10)",
    )
    parser.add_argument(
        "--timeframe",
        default="1h",
        choices=["1h", "4h", "1d"],
        help="Candle interval (default: 1h)",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default=None,
        help="Start date (YYYY-MM-DD). Default: 6 months ago",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=None,
        help="End date (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to save results (default: current dir)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bars",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    progress = not args.no_progress

    all_trades: List[Trade] = []
    per_coin_results: dict = {}

    # Default dates
    end_ms = args.end_date or int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = args.start_date or (end_ms - 180 * 24 * 3600 * 1000)

    print("=" * 65)
    print(" CRYPTO SIGNAL BOT — BACKTEST ENGINE ")
    print("=" * 65)
    print(f" Coins      : {', '.join(args.coins)}")
    print(f" Timeframe  : {args.timeframe}")
    print(f" Date range : {datetime.fromtimestamp(start_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d')} → {datetime.fromtimestamp(end_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d')}")
    print(f" Output dir : {out_dir.resolve()}")
    print("=" * 65)

    for coin in tqdm(args.coins, desc="Coins", disable=not progress):
        symbol = f"{coin}USDT"
        try:
            df = fetch_all(symbol, args.timeframe, start_ms, end_ms, progress=progress)
            if df.empty or len(df) < 200:
                print(f"[SKIP] {symbol}: insufficient data ({len(df)} candles)")
                continue

            df = add_indicators(df)
            df = generate_signals(df)
            trades = run(df, symbol, progress=progress)
            all_trades.extend(trades)
            per_coin_results[coin] = len(trades)

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
            continue

    if not all_trades:
        print("\n[ERROR] No trades generated. Check signal conditions or date range.")
        sys.exit(1)

    # --- Metrics ---
    summary = calculate(all_trades)
    by_coin_data = by_coin(all_trades)
    by_dir_data = by_direction(all_trades)
    monthly_data = monthly(all_trades)

    # --- JSON output ---
    json_path = out_dir / "backtest_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "trades": [t.__dict__ for t in all_trades],
            "by_coin": by_coin_data,
            "by_direction": by_dir_data,
            "monthly": monthly_data,
        }, f, indent=2, default=str)

    # --- HTML report ---
    html_path = out_dir / "backtest_report.html"
    generate(all_trades, str(html_path))

    # --- Console summary ---
    print("\n" + "=" * 65)
    print(" RESULTS SUMMARY ")
    print("=" * 65)
    
    table = [
        ["Total Trades", summary["total_trades"]],
        ["Wins", f"{summary['wins']} ({summary['win_rate']:.1f}%)"],
        ["Losses", f"{summary['losses']} ({summary['loss_rate']:.1f}%)"],
        ["Avg Win", f"{summary['avg_win_pct']:.2f}%"],
        ["Avg Loss", f"{summary['avg_loss_pct']:.2f}%"],
        ["Avg Trade", f"{summary['avg_trade_pct']:.2f}%"],
        ["Profit Factor", f"{summary['profit_factor']:.2f}"],
        ["Max Drawdown", f"{summary['max_drawdown']:.2f}%"],
        ["Sharpe Ratio", f"{summary['sharpe_ratio']:.2f}"],
        ["Expectancy", f"{summary['expectancy']:.2f}%"],
        ["Avg Hold", f"{summary['avg_hold_candles']:.0f} candles"],
        ["Best Trade", f"{summary['best_trade']:.2f}%"],
        ["Worst Trade", f"{summary['worst_trade']:.2f}%"],
        ["Partial Exits", summary["partial_exits"]],
    ]
    print(tabulate(table, headers=["Metric", "Value"], tablefmt="grid"))

    print("\n--- By Coin ---")
    coin_table = []
    for coin in sorted(by_coin_data.keys()):
        m = by_coin_data[coin]
        coin_table.append([coin, m["total_trades"], f"{m['win_rate']:.1f}%", f"{m['profit_factor']:.2f}"])
    print(tabulate(coin_table, headers=["Coin", "Trades", "Win Rate", "Profit Factor"], tablefmt="grid"))

    print("\n--- By Direction ---")
    for direction, m in by_dir_data.items():
        print(f"  {direction}: {m['total_trades']} trades | {m['win_rate']:.1f}% win | PF {m['profit_factor']:.2f}")

    print(f"\n[OK] JSON saved: {json_path}")
    print(f"[OK] HTML saved: {html_path}")
    print("=" * 65)


if __name__ == "__main__":
    main()
