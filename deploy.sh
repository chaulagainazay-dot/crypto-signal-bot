#!/usr/bin/env bash
set -e

echo "🚀 Crypto Signal Bot Deployment Script"

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }

# Build images
echo "🔨 Building Docker images..."
docker-compose build

# Run backtest first to verify everything works
echo "📊 Running backtest engine..."
docker-compose run --rm backtest

# If .env exists, start the bot
echo "🤖 Starting bot service..."
if [ -f .env ]; then
    docker-compose up -d bot
    echo "✅ Bot deployed. Check logs: docker-compose logs -f bot"
else
    echo "⚠️  .env file not found. Bot not started (needs TELEGRAM_BOT_TOKEN)."
    echo "   Create .env from .env.example and run: docker-compose up -d bot"
fi

echo "🎉 Deployment complete!"
