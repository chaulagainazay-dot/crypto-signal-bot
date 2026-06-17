#!/bin/bash
set -e
echo "=== Crypto Signal Agent Setup ==="

# Create virtualenv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env — add your ANTHROPIC_API_KEY and optionally CRYPTOPANIC_API_KEY"
echo "  2. Run: source venv/bin/activate && python main.py"
echo "  3. In Telegram, message your bot and type /start to get your chat ID"
echo "  4. Add your chat ID to .env as TELEGRAM_CHAT_ID"
echo ""
echo "The bot will auto-scan every 15 minutes and send signals to your Telegram."
