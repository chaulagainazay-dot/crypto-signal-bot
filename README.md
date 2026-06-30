# Crypto Signal Bot

A Telegram crypto signal bot with a full backtest engine, technical analysis, and automated reporting.

## Quick Start (Local)

```bash
# Clone & install
git clone https://github.com/chaulagainazay-dot/crypto-signal-bot.git
cd crypto-signal-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run the main bot (set TELEGRAM_BOT_TOKEN in .env first)
python main.py

# Run the backtest engine
python backtest_engine.py
```

## Docker Deployment

```bash
# Build & run the full bot
docker-compose up --build

# Or just the backtest engine
docker build -t crypto-backtest .
docker run --rm -v $(pwd)/results:/app/results crypto-backtest
```

## Deploy to Heroku

```bash
heroku create your-bot-name
heroku config:set TELEGRAM_BOT_TOKEN=<token>
git push heroku master
```

## Backtest Engine

```bash
# Default: all 5 coins (BTC, ETH, SOL, BNB, XRP) across 1h, 4h, 1d
python backtest_engine.py

# Custom run
python backtest_engine.py --coins BTC ETH --timeframes 1h 4h --candles 2000
```

Outputs:
- `backtest_results.json` — raw trade data + metrics
- `backtest_report.html` — self-contained HTML report with charts

## Project Structure

```
crypto-signal-bot/
├── main.py              # Main bot entry
├── backtest_engine.py   # Historical backtester
├── scanner.py           # Signal scanner
├── layers/              # L1-L5 pipeline layers
│   ├── l1_data.py
│   ├── l2_technical.py
│   ├── l3_signal.py
│   ├── l4_risk.py
│   └── l5_delivery.py
├── utils/               # Helpers & DB
├── webapp/              # Web dashboard
├── backend/             # API backend
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## License
MIT
