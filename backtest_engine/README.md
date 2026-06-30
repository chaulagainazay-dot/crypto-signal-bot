# Crypto Signal Bot — Backtest Engine

A production-ready backtesting engine for the crypto signal bot. Fetches real historical OHLCV data from Binance's free public API, calculates technical indicators, and runs a walk-forward candle-by-candle simulation to compute actual P&L.

## Features

- **Real Data**: Fetches from Binance public klines API (no API key required)
- **SQLite Cache**: Avoids re-fetching data on repeated runs
- **10 Coins**: BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOT, DOGE
- **Indicators**: RSI(14), MACD(12/26/9), EMA(21/200), ATR(14), ADX(14), Volume SMA(20)
- **Signal Logic**: Matches current bot strategy (LONG/SHORT with volume confirmation)
- **Partial Exits**: TP1 = 50% position, TP2 = remaining 50%
- **Risk Metrics**: Profit factor, Sharpe ratio, max drawdown, expectancy
- **Rich Reports**: JSON + self-contained HTML with charts

## Installation

```bash
git clone https://github.com/chaulagainazay-dot/crypto-signal-bot.git
cd crypto-signal-bot/backtest_engine
pip install -r requirements.txt
```

## Usage

### Basic Backtest (all coins, default 6 months, 1h)
```bash
python main.py
```

### Specific Coins + Timeframe
```bash
python main.py --coins BTC ETH SOL --timeframe 4h
```

### Custom Date Range
```bash
python main.py --start-date 2024-01-01 --end-date 2025-06-30 --timeframe 1d
```

### Custom Output Directory
```bash
python main.py --output-dir ./results --coins BTC ETH
```

## Output Files

| File | Description |
|------|-------------|
| `backtest_results.json` | All trade data, summary metrics, breakdowns by coin/direction/month |
| `backtest_report.html` | Self-contained HTML report with equity curve, drawdown, distribution, monthly returns, win rate by coin, and trade table |
| `backtest_cache.db` | SQLite cache of fetched OHLCV data (speeds up re-runs) |

## Interpreting Results

- **Profit Factor > 1.0**: Profitable strategy (gross wins / gross losses)
- **Sharpe Ratio > 1.0**: Good risk-adjusted returns
- **Expectancy > 0**: Positive expected value per trade
- **Win Rate**: Percentage of winning trades (not the only metric that matters!)
- **Max Drawdown**: Largest peak-to-trough decline — critical for position sizing

## Example Output

```
+---------------+-------------+
| Metric        | Value       |
+---------------+-------------+
| Total Trades  | 47          |
| Wins          | 28 (59.6%)  |
| Losses        | 19 (40.4%)  |
| Avg Win       | 2.84%       |
| Avg Loss      | -1.12%      |
| Profit Factor | 2.14        |
| Sharpe Ratio  | 1.87        |
| Expectancy    | 1.24%       |
+---------------+-------------+
```

## Architecture

```
backtest_engine/
├── __init__.py
├── data_fetcher.py      # Binance API + SQLite cache
├── indicators.py        # TA calculations (ta library)
├── signal_logic.py      # Signal generation rules
├── backtester.py        # Walk-forward simulation
├── metrics.py           # Performance calculations
├── report_generator.py  # HTML + matplotlib charts
└── main.py              # CLI entry point
```

## License
MIT
