"""Trading education content — beginner to advanced."""

LESSONS = {
    # ── BEGINNER ──────────────────────────────────────────────────────────────
    "what_is_trading": {
        "title": "📖 What is Trading?",
        "body": (
            "📖 <b>What is Trading?</b>\n\n"
            "Trading is buying and selling assets (crypto, stocks, forex) to make profit from price movements.\n\n"
            "<b>Two main styles:</b>\n"
            "• <b>Buy low, sell high</b> — profit when price rises\n"
            "• <b>Short selling</b> — profit when price falls\n\n"
            "<b>Types of traders:</b>\n"
            "• <b>Scalper</b> — holds seconds to minutes\n"
            "• <b>Day Trader</b> — opens and closes same day\n"
            "• <b>Swing Trader</b> — holds days to weeks\n"
            "• <b>Position Trader</b> — holds weeks to months\n\n"
            "<b>Key rule:</b> Never risk more than you can afford to lose.\n\n"
            "💡 <i>Start small. Learn the market before trading real money.</i>"
        ),
    },
    "spot_trading": {
        "title": "💱 Spot Trading",
        "body": (
            "💱 <b>Spot Trading</b>\n\n"
            "Spot trading means buying the actual asset at current market price.\n\n"
            "<b>How it works:</b>\n"
            "• You pay now, receive the asset now\n"
            "• You OWN the crypto (not just a contract)\n"
            "• No expiry date — hold as long as you want\n"
            "• Maximum loss = what you invested (no liquidation)\n\n"
            "<b>Example:</b>\n"
            "BTC price = $60,000\n"
            "You buy 0.1 BTC → spend $6,000\n"
            "BTC rises to $70,000\n"
            "You sell → receive $7,000 → profit $1,000 ✅\n\n"
            "<b>Best for:</b> Beginners, long-term holders, low-risk traders\n\n"
            "💡 <i>Spot trading on Binance, Bybit, OKX is safest for beginners.</i>"
        ),
    },
    "futures_trading": {
        "title": "📊 Futures Trading",
        "body": (
            "📊 <b>Futures Trading</b>\n\n"
            "Futures are contracts to buy/sell an asset at a set price in the future. In crypto, most are perpetual (no expiry).\n\n"
            "<b>Key difference from spot:</b>\n"
            "• You don't own the actual crypto\n"
            "• You can go LONG (bet price rises) or SHORT (bet price falls)\n"
            "• Uses leverage — amplifies profits AND losses\n\n"
            "<b>Perpetual futures:</b>\n"
            "• No expiry date\n"
            "• Funding rate paid every 8 hours\n"
            "• Liquidation risk if price moves against you\n\n"
            "<b>Example:</b>\n"
            "BTC = $60,000. You open 10x Long with $1,000\n"
            "→ Controls $10,000 worth of BTC\n"
            "BTC rises 5% → you profit 50% = +$500 ✅\n"
            "BTC falls 10% → you lose 100% = -$1,000 ❌ (liquidated)\n\n"
            "⚠️ <b>High risk. Only trade futures after mastering spot.</b>"
        ),
    },
    "margin_trading": {
        "title": "💸 Margin Trading",
        "body": (
            "💸 <b>Margin Trading</b>\n\n"
            "Margin trading means borrowing money from an exchange to trade larger positions.\n\n"
            "<b>How it works:</b>\n"
            "• You deposit $1,000 as collateral\n"
            "• Borrow $4,000 from exchange (5x margin)\n"
            "• Trade with $5,000 total\n\n"
            "<b>Margin vs Futures:</b>\n"
            "• Margin: You actually borrow and hold the asset\n"
            "• Futures: You trade a contract (no real asset)\n\n"
            "<b>Risks:</b>\n"
            "• Margin call — must add more collateral or get liquidated\n"
            "• Interest charges on borrowed funds\n"
            "• Liquidation price is real — you can lose everything\n\n"
            "⚠️ <b>Margin trading is even riskier than futures for beginners.</b>\n\n"
            "💡 <i>Always keep your margin ratio above 150% to avoid liquidation.</i>"
        ),
    },
    "leverage_explained": {
        "title": "⚡ Leverage Explained",
        "body": (
            "⚡ <b>Leverage Explained</b>\n\n"
            "Leverage lets you control a larger position with less money.\n\n"
            "<b>How leverage multiplies:</b>\n"
            "• 1x = no leverage (spot trade)\n"
            "• 5x = $1,000 controls $5,000 position\n"
            "• 10x = $1,000 controls $10,000 position\n"
            "• 100x = $1,000 controls $100,000 position\n\n"
            "<b>The math:</b>\n"
            "Profit = (Price change %) × Leverage\n"
            "Liquidation at ≈ 1/Leverage price move against you\n\n"
            "<b>Examples:</b>\n"
            "10x Long, BTC drops 10% → Liquidated ❌\n"
            "10x Long, BTC rises 10% → +100% profit ✅\n\n"
            "<b>Recommended leverage by experience:</b>\n"
            "🟢 Beginner: 1x–3x maximum\n"
            "🟡 Intermediate: 3x–10x\n"
            "🔴 Expert only: 10x–25x\n\n"
            "💀 <b>Never use 50x–100x. Even a 1% move = liquidation.</b>"
        ),
    },

    # ── INTERMEDIATE ──────────────────────────────────────────────────────────
    "support_resistance": {
        "title": "📐 Support & Resistance",
        "body": (
            "📐 <b>Support & Resistance</b>\n\n"
            "<b>Support</b> — a price level where buyers step in and push price UP.\n"
            "Think of it as a floor beneath price.\n\n"
            "<b>Resistance</b> — a price level where sellers push price DOWN.\n"
            "Think of it as a ceiling above price.\n\n"
            "<b>Why they form:</b>\n"
            "• Previous highs/lows with many trades\n"
            "• Round numbers ($60,000, $100,000)\n"
            "• Areas where price reversed multiple times\n\n"
            "<b>How to use them:</b>\n"
            "• BUY near support (low risk, high reward)\n"
            "• SELL near resistance (take profit zone)\n"
            "• Breakout above resistance = new support\n"
            "• Breakdown below support = new resistance\n\n"
            "<b>Key rule:</b> The more times a level is tested, the stronger it is.\n\n"
            "💡 <i>Draw S&R on daily chart first, then zoom to hourly for entries.</i>"
        ),
    },
    "trendlines": {
        "title": "📈 Trendlines",
        "body": (
            "📈 <b>Trendlines</b>\n\n"
            "Trendlines show the direction and strength of price movement.\n\n"
            "<b>Types:</b>\n"
            "• <b>Uptrend</b> — higher highs, higher lows → draw line under lows\n"
            "• <b>Downtrend</b> — lower highs, lower lows → draw line over highs\n"
            "• <b>Sideways</b> — price bouncing in range → draw support + resistance\n\n"
            "<b>Drawing rules:</b>\n"
            "• Need at least 2 points to draw a line\n"
            "• 3rd point that holds confirms the trendline\n"
            "• Use candle bodies, not wicks for most accurate lines\n\n"
            "<b>Trading strategy:</b>\n"
            "• Buy when price touches uptrend line (bounce)\n"
            "• Sell when price breaks below trendline (trend change)\n"
            "• Breakout above downtrend = buy signal\n\n"
            "💡 <i>Trendlines on weekly/daily charts are strongest.</i>"
        ),
    },
    "market_structure": {
        "title": "🏗 Market Structure",
        "body": (
            "🏗 <b>Market Structure</b>\n\n"
            "Market structure describes how price moves over time — the pattern of highs and lows.\n\n"
            "<b>Bullish structure:</b>\n"
            "HH (Higher High) → HL (Higher Low) → HH → HL\n"
            "Price making higher highs and higher lows = uptrend ✅\n\n"
            "<b>Bearish structure:</b>\n"
            "LH (Lower High) → LL (Lower Low) → LH → LL\n"
            "Price making lower highs and lower lows = downtrend ❌\n\n"
            "<b>Break of Structure (BOS):</b>\n"
            "• When price breaks above previous HH = bullish BOS\n"
            "• When price breaks below previous LL = bearish BOS\n"
            "• Change of Character (CHoCH) = first sign of trend reversal\n\n"
            "<b>How to trade it:</b>\n"
            "• Only LONG in bullish structure\n"
            "• Only SHORT in bearish structure\n"
            "• Wait for CHoCH before changing bias\n\n"
            "💡 <i>Always know the higher timeframe structure before trading lower TF.</i>"
        ),
    },
    "volume_analysis": {
        "title": "📊 Volume Analysis",
        "body": (
            "📊 <b>Volume Analysis</b>\n\n"
            "Volume = number of coins traded. It confirms or denies price moves.\n\n"
            "<b>Key volume principles:</b>\n"
            "• Price up + Volume up = strong uptrend ✅\n"
            "• Price up + Volume down = weak move, may reverse ⚠️\n"
            "• Price down + Volume up = strong selling ❌\n"
            "• Price down + Volume down = weak selling, may bounce ⚠️\n\n"
            "<b>Volume signals:</b>\n"
            "• <b>Volume spike</b> — sudden 3-5x normal = institution entry\n"
            "• <b>Breakout + volume</b> = confirmed breakout\n"
            "• <b>Breakout + no volume</b> = fake breakout, likely reversal\n\n"
            "<b>Tools:</b>\n"
            "• Volume bars (bottom of chart)\n"
            "• Volume Profile (shows most traded price levels)\n"
            "• OBV (On Balance Volume) — cumulative volume indicator\n\n"
            "💡 <i>Always check volume when a price breaks support or resistance.</i>"
        ),
    },
    "candlestick_patterns": {
        "title": "🕯 Candlestick Patterns",
        "body": (
            "🕯 <b>Candlestick Patterns</b>\n\n"
            "Candlesticks show open, high, low, close for each time period.\n\n"
            "<b>Basic candle structure:</b>\n"
            "• Green/White = price closed HIGHER (bullish)\n"
            "• Red/Black = price closed LOWER (bearish)\n"
            "• Body = open to close range\n"
            "• Wick = high/low beyond body\n\n"
            "<b>Key patterns:</b>\n\n"
            "🟢 <b>Bullish patterns</b>\n"
            "• Hammer — long lower wick, small body at top\n"
            "• Bullish Engulfing — big green candle engulfs red\n"
            "• Morning Star — 3-candle reversal at bottom\n"
            "• Doji at support — indecision = potential reversal\n\n"
            "🔴 <b>Bearish patterns</b>\n"
            "• Shooting Star — long upper wick, small body at bottom\n"
            "• Bearish Engulfing — big red candle engulfs green\n"
            "• Evening Star — 3-candle reversal at top\n\n"
            "💡 <i>Patterns are more reliable on higher timeframes (4H, Daily).</i>"
        ),
    },

    # ── ADVANCED ──────────────────────────────────────────────────────────────
    "smart_money": {
        "title": "💡 Smart Money Concept (SMC)",
        "body": (
            "💡 <b>Smart Money Concept (SMC)</b>\n\n"
            "SMC is a trading approach that tracks institutional (smart money) activity to trade alongside banks and hedge funds.\n\n"
            "<b>Core ideas:</b>\n"
            "• Institutions manipulate price to fill large orders\n"
            "• They hunt stop losses before moving in the real direction\n"
            "• Understanding their behaviour lets you stop being the victim\n\n"
            "<b>Key SMC concepts:</b>\n"
            "• <b>Order Blocks (OB)</b> — last candle before a big move = institutional order zone\n"
            "• <b>Fair Value Gap (FVG)</b> — imbalance in price that gets filled later\n"
            "• <b>Liquidity</b> — stop losses clustered at highs/lows = target for institutions\n"
            "• <b>BOS/CHoCH</b> — break of structure signals\n"
            "• <b>Premium/Discount zones</b> — sell premium (above 50% retracement), buy discount\n\n"
            "<b>SMC trade setup:</b>\n"
            "1. Identify higher TF structure (bullish/bearish)\n"
            "2. Wait for liquidity grab (stop hunt)\n"
            "3. Look for CHoCH on lower TF\n"
            "4. Enter at Order Block or FVG\n"
            "5. Target next liquidity pool\n\n"
            "💡 <i>ICT (Inner Circle Trader) created the SMC methodology.</i>"
        ),
    },
    "ict_concepts": {
        "title": "🎓 ICT Concepts",
        "body": (
            "🎓 <b>ICT (Inner Circle Trader) Concepts</b>\n\n"
            "ICT is a comprehensive trading methodology by Michael Huddleston focusing on price delivery and institutional mechanics.\n\n"
            "<b>Core ICT concepts:</b>\n\n"
            "• <b>Killzones</b> — best trading times\n"
            "  – London: 3–5 AM EST\n"
            "  – New York: 9–11 AM EST\n"
            "  – Asian: 8 PM–11 PM EST\n\n"
            "• <b>Power of 3 (PO3)</b>\n"
            "  – Accumulation → Manipulation → Distribution\n"
            "  – Asian range forms, London breaks it (fake), NY moves real direction\n\n"
            "• <b>Optimal Trade Entry (OTE)</b>\n"
            "  – 61.8%–79% Fibonacci retracement = ideal entry zone\n\n"
            "• <b>Market Maker Model</b>\n"
            "  – Seek buy side liquidity → smart money sells there\n"
            "  – Seek sell side liquidity → smart money buys there\n\n"
            "• <b>IPDA (Interbank Price Delivery Algorithm)</b>\n"
            "  – Price is delivered by algorithm, not random\n"
            "  – Looks back 20, 40, 60 trading days for draw on liquidity\n\n"
            "💡 <i>Study ICT on YouTube — Michael Huddleston has free content.</i>"
        ),
    },
    "wyckoff": {
        "title": "📉 Wyckoff Method",
        "body": (
            "📉 <b>Wyckoff Method</b>\n\n"
            "Developed in 1930s, the Wyckoff Method identifies market cycles and institutional activity.\n\n"
            "<b>The 4 market phases:</b>\n\n"
            "1️⃣ <b>Accumulation</b> — institutions quietly buy at low prices\n"
            "   • Range-bound market, flat movement\n"
            "   • Volume decreasing on down moves\n"
            "   • Spring (false breakdown) then markup\n\n"
            "2️⃣ <b>Markup</b> — price trends up as institutions hold\n"
            "   • Clear uptrend, higher highs/lows\n"
            "   • Volume confirms upward moves\n\n"
            "3️⃣ <b>Distribution</b> — institutions sell to retail at high prices\n"
            "   • Range-bound again at high prices\n"
            "   • Upthrust (false breakout) then markdown\n\n"
            "4️⃣ <b>Markdown</b> — price falls as retail panic sells\n\n"
            "<b>Key Wyckoff events:</b>\n"
            "• PS (Preliminary Support/Supply)\n"
            "• SC (Selling Climax) / BC (Buying Climax)\n"
            "• Spring / Upthrust\n"
            "• SOS (Sign of Strength)\n\n"
            "💡 <i>Wyckoff is most powerful on weekly/monthly charts.</i>"
        ),
    },
    "elliott_wave": {
        "title": "🌊 Elliott Wave Theory",
        "body": (
            "🌊 <b>Elliott Wave Theory</b>\n\n"
            "Elliott Wave theory says markets move in predictable wave patterns driven by investor psychology.\n\n"
            "<b>Impulse wave (5 waves):</b>\n"
            "Wave 1 ↑ Wave 2 ↓ Wave 3 ↑ Wave 4 ↓ Wave 5 ↑\n\n"
            "<b>Corrective wave (3 waves):</b>\n"
            "Wave A ↓ Wave B ↑ Wave C ↓\n\n"
            "<b>Key rules:</b>\n"
            "• Wave 2 cannot retrace more than 100% of Wave 1\n"
            "• Wave 3 is always the longest impulse wave\n"
            "• Wave 4 cannot overlap Wave 1 (in stocks; can in crypto)\n\n"
            "<b>Fibonacci relationships:</b>\n"
            "• Wave 2 retraces 50%–61.8% of Wave 1\n"
            "• Wave 3 is 1.618x–2.618x of Wave 1\n"
            "• Wave 4 retraces 38.2% of Wave 3\n"
            "• Wave 5 = Wave 1 in length\n\n"
            "⚠️ <b>Elliott Wave is subjective — two analysts can see different counts.</b>\n\n"
            "💡 <i>Use EW to set big picture targets, not for precise entries.</i>"
        ),
    },
    "order_blocks": {
        "title": "🟦 Order Blocks",
        "body": (
            "🟦 <b>Order Blocks</b>\n\n"
            "Order blocks are price zones where institutional orders were placed before a significant move.\n\n"
            "<b>Bullish Order Block (BOB):</b>\n"
            "• Last DOWN candle before a strong UP move\n"
            "• Institutions loaded buy orders here\n"
            "• Price often returns to this zone before continuing up\n\n"
            "<b>Bearish Order Block (SOB):</b>\n"
            "• Last UP candle before a strong DOWN move\n"
            "• Institutions placed sell orders here\n"
            "• Price returns to distribute more\n\n"
            "<b>How to trade order blocks:</b>\n"
            "1. Identify a strong impulsive move\n"
            "2. Mark the last opposite candle before the move\n"
            "3. Wait for price to return to that zone\n"
            "4. Look for confirmation (CHoCH, rejection wick)\n"
            "5. Enter with stop below/above the block\n\n"
            "<b>Higher timeframe OBs are more powerful</b>\n\n"
            "💡 <i>Combine OBs with FVGs for high-probability entries.</i>"
        ),
    },
    "fair_value_gap": {
        "title": "⚡ Fair Value Gap (FVG)",
        "body": (
            "⚡ <b>Fair Value Gap (FVG)</b>\n\n"
            "A Fair Value Gap is a 3-candle imbalance where price moved so fast that it left an unfilled gap between wicks.\n\n"
            "<b>How to identify:</b>\n"
            "• Look at 3 consecutive candles\n"
            "• Bullish FVG: Candle 3 low > Candle 1 high (gap between them)\n"
            "• Bearish FVG: Candle 3 high < Candle 1 low (gap between them)\n\n"
            "<b>Why FVGs matter:</b>\n"
            "• Price tends to return and fill these gaps\n"
            "• Represents inefficiency in the market\n"
            "• Acts as support/resistance when price returns\n\n"
            "<b>Trading FVGs:</b>\n"
            "• Bullish FVG = buy zone when price returns\n"
            "• Bearish FVG = sell zone when price returns\n"
            "• Best FVGs are on higher TFs (4H, Daily)\n"
            "• Look for FVGs within Order Blocks for confluence\n\n"
            "💡 <i>FVGs often align with 50% retracement of the move that created them.</i>"
        ),
    },
    "liquidity": {
        "title": "💧 Liquidity",
        "body": (
            "💧 <b>Liquidity in Trading</b>\n\n"
            "Liquidity refers to clusters of stop-loss orders and pending orders that institutions target.\n\n"
            "<b>Where liquidity pools are:</b>\n"
            "• Above previous swing highs (buy-side liquidity)\n"
            "• Below previous swing lows (sell-side liquidity)\n"
            "• Equal highs / equal lows\n"
            "• Round numbers ($50K, $60K, $100K)\n"
            "• Trendline touch points\n\n"
            "<b>How institutions use liquidity:</b>\n"
            "1. Price hunts stop losses above/below key levels\n"
            "2. Retail traders get stopped out\n"
            "3. Institutions fill their large orders at this level\n"
            "4. Price reverses and moves the REAL direction\n\n"
            "<b>Trading liquidity sweeps:</b>\n"
            "• Wait for price to take out a key high/low\n"
            "• Look for rejection (wick beyond the level)\n"
            "• Enter opposite direction after confirmation\n"
            "• Target the next liquidity pool\n\n"
            "💡 <i>The market moves from liquidity to liquidity.</i>"
        ),
    },
    "market_maker_model": {
        "title": "🏦 Market Maker Model",
        "body": (
            "🏦 <b>Market Maker Model</b>\n\n"
            "The Market Maker Model (from ICT) describes how banks and institutions manipulate price to accumulate and distribute positions.\n\n"
            "<b>Buy Program:</b>\n"
            "1. Create downward move to sweep sell-side liquidity\n"
            "2. Absorb sell stops (fill buy orders at discount)\n"
            "3. Leave FVG/OB as evidence\n"
            "4. Run price up to buy-side liquidity\n"
            "5. Distribute at premium (sell to latecomers)\n\n"
            "<b>Sell Program:</b>\n"
            "1. Create upward move to sweep buy-side liquidity\n"
            "2. Absorb buy stops (fill sell orders at premium)\n"
            "3. Leave FVG/OB as evidence\n"
            "4. Run price down to sell-side liquidity\n"
            "5. Cover shorts at discount\n\n"
            "<b>How to use it:</b>\n"
            "• Identify the current draw on liquidity (where is price going?)\n"
            "• Look for manipulation (stop hunt) before real move\n"
            "• Enter after manipulation in direction of real move\n\n"
            "💡 <i>Ask: 'Where are the stops? Price will go there first.'</i>"
        ),
    },

    # ── PSYCHOLOGY ────────────────────────────────────────────────────────────
    "fear_psychology": {
        "title": "😨 Trading Fear",
        "body": (
            "😨 <b>Trading Fear</b>\n\n"
            "Fear is one of the most destructive emotions in trading. It causes missed opportunities and panic selling.\n\n"
            "<b>Types of trading fear:</b>\n"
            "• <b>Fear of losing</b> — won't take valid setups\n"
            "• <b>Fear of missing out (FOMO)</b> — enters bad trades\n"
            "• <b>Fear of being wrong</b> — won't cut losses\n"
            "• <b>Fear after a loss</b> — too cautious to trade\n\n"
            "<b>Signs you're trading from fear:</b>\n"
            "• Moving stop loss to avoid being stopped out\n"
            "• Taking profit too early\n"
            "• Avoiding trades despite valid setups\n"
            "• Checking price every few minutes\n\n"
            "<b>How to overcome it:</b>\n"
            "✅ Pre-plan every trade before entering\n"
            "✅ Use position sizes you're comfortable losing\n"
            "✅ Set and forget — stop watching every tick\n"
            "✅ Accept that losses are part of trading\n"
            "✅ Focus on process, not outcome\n\n"
            "💡 <i>'The goal is not to be right. The goal is to make money.'</i>"
        ),
    },
    "greed_psychology": {
        "title": "💰 Trading Greed",
        "body": (
            "💰 <b>Trading Greed</b>\n\n"
            "Greed causes traders to take more risk than planned, hold winners too long, and overtrade.\n\n"
            "<b>Signs of trading greed:</b>\n"
            "• Moving take profit up hoping for more\n"
            "• Adding to winning positions recklessly\n"
            "• Trading too many positions at once\n"
            "• Using too much leverage\n"
            "• Doubling position after a win ('let it ride')\n\n"
            "<b>The greed cycle:</b>\n"
            "Small win → Feel confident → Risk more → Bigger loss → Try to recover fast → Even bigger loss ❌\n\n"
            "<b>How to control greed:</b>\n"
            "✅ Set profit targets BEFORE entering\n"
            "✅ Never move your TP higher after entering\n"
            "✅ Use a max daily profit limit (stop trading after hitting it)\n"
            "✅ Keep a journal — see how greed costs you\n"
            "✅ Follow position sizing rules strictly\n\n"
            "💡 <i>Professionals take consistent profits. Amateurs chase big wins.</i>"
        ),
    },
    "revenge_trading": {
        "title": "💢 Revenge Trading",
        "body": (
            "💢 <b>Revenge Trading</b>\n\n"
            "Revenge trading is when you take impulsive trades to 'win back' money after a loss. It almost always makes things worse.\n\n"
            "<b>How it happens:</b>\n"
            "1. Take a loss\n"
            "2. Feel angry or embarrassed\n"
            "3. Enter a trade immediately without proper analysis\n"
            "4. Use larger size to 'recover faster'\n"
            "5. Lose more\n"
            "6. Repeat → Account blown ❌\n\n"
            "<b>Warning signs:</b>\n"
            "• Entering a trade within 5 minutes of a loss\n"
            "• Doubling or tripling your usual size\n"
            "• Trading outside your normal setup criteria\n"
            "• Feeling emotional while trading\n\n"
            "<b>Prevention rules:</b>\n"
            "✅ Rule: If you hit daily loss limit, STOP trading\n"
            "✅ Take a 30-minute break after any loss\n"
            "✅ Write down what you feel before entering next trade\n"
            "✅ Daily loss limit = 3% of account. Never exceed it.\n\n"
            "💡 <i>The market will still be there tomorrow. Your capital won't be if you revenge trade.</i>"
        ),
    },
    "discipline": {
        "title": "⚔️ Trading Discipline",
        "body": (
            "⚔️ <b>Trading Discipline</b>\n\n"
            "Discipline is following your trading plan even when emotions say otherwise.\n\n"
            "<b>What discipline looks like:</b>\n"
            "• Only taking setups that match your criteria exactly\n"
            "• Not trading during news events if that's your rule\n"
            "• Stopping after hitting daily loss limit\n"
            "• Keeping position size consistent\n"
            "• Recording every trade in your journal\n\n"
            "<b>How to build discipline:</b>\n"
            "1. Write a clear trading plan (entry rules, exit rules, size rules)\n"
            "2. Review it before every session\n"
            "3. Track every deviation from the plan\n"
            "4. Treat your trading like a business, not gambling\n\n"
            "<b>Daily routine of a disciplined trader:</b>\n"
            "🌅 Morning: review market, identify setups\n"
            "📋 Before trade: check if it meets ALL criteria\n"
            "📊 During trade: don't move stops/targets\n"
            "📝 After session: journal wins, losses, and emotions\n\n"
            "💡 <i>Consistency over 100 trades matters more than any single trade.</i>"
        ),
    },
    "risk_management": {
        "title": "🛡 Risk Management",
        "body": (
            "🛡 <b>Risk Management</b>\n\n"
            "Risk management is how you protect your capital. It's the most important skill in trading.\n\n"
            "<b>The 1% rule:</b>\n"
            "Never risk more than 1–2% of account per trade.\n"
            "$10,000 account → max risk $100–$200 per trade\n\n"
            "<b>Position sizing formula:</b>\n"
            "Position Size = (Account × Risk %) ÷ (Entry - Stop Loss)\n\n"
            "<b>Example:</b>\n"
            "Account: $10,000 | Risk: 1% = $100\n"
            "Entry: $60,000 | Stop: $58,000 (gap = $2,000)\n"
            "Position Size = $100 ÷ $2,000 = 0.05 BTC\n\n"
            "<b>Daily/Weekly limits:</b>\n"
            "• Max daily loss: 3% of account\n"
            "• Max weekly loss: 6% of account\n"
            "• If hit → stop trading that period\n\n"
            "<b>Risk:Reward minimum:</b>\n"
            "• Minimum 1:2 (risk $100, target $200)\n"
            "• Aim for 1:3 or better\n\n"
            "💡 <i>With 1:2 RR, you only need to win 34% of trades to profit.</i>"
        ),
    },
    "position_sizing": {
        "title": "📏 Position Sizing",
        "body": (
            "📏 <b>Position Sizing</b>\n\n"
            "Position sizing determines HOW MUCH to trade. Wrong sizing = account blown.\n\n"
            "<b>The formula:</b>\n"
            "Position Size ($) = (Account Balance × Risk %) ÷ Stop Loss %\n\n"
            "<b>Step by step:</b>\n"
            "1. Decide risk: 1% of account\n"
            "2. Calculate stop loss distance in %\n"
            "3. Divide: risk amount ÷ stop loss %\n\n"
            "<b>Example:</b>\n"
            "Account: $5,000 | Risk: 1% = $50\n"
            "Entry: $100 | Stop: $95 (5% away)\n"
            "Position = $50 ÷ 0.05 = $1,000 (1,000/100 = 10 coins)\n\n"
            "<b>Rules for different account sizes:</b>\n"
            "🟢 Under $1,000: risk 1% per trade max\n"
            "🟡 $1,000–$10,000: risk 1–2% per trade\n"
            "🔴 Over $10,000: risk 0.5–1% per trade\n\n"
            "⚠️ <b>Never risk more than 2% per trade no matter what.</b>\n\n"
            "💡 <i>Use the Position Size Calculator in ⚙️ Tools to calculate automatically.</i>"
        ),
    },
}

QUIZ_QUESTIONS = [
    {
        "q": "What does RSI above 70 indicate?",
        "options": ["Oversold", "Overbought", "Neutral", "Strong trend"],
        "answer": 1,
        "explanation": "RSI above 70 = overbought. Price may be due for a pullback."
    },
    {
        "q": "What is the minimum Risk:Reward ratio recommended?",
        "options": ["1:0.5", "1:1", "1:2", "1:5"],
        "answer": 2,
        "explanation": "Minimum 1:2 means risking $1 to potentially make $2."
    },
    {
        "q": "What happens when price breaks above resistance?",
        "options": ["Price falls", "Resistance becomes support", "Support is created above", "Nothing changes"],
        "answer": 1,
        "explanation": "When resistance is broken, it flips and becomes new support."
    },
    {
        "q": "With 10x leverage, price needs to move how much against you to get liquidated?",
        "options": ["10%", "20%", "5%", "~10%"],
        "answer": 3,
        "explanation": "10x leverage = ~10% adverse move = liquidation (depending on fees/exchange)."
    },
    {
        "q": "What does MACD crossover signal?",
        "options": ["Volume surge", "Potential trend change", "Support level", "Market cap"],
        "answer": 1,
        "explanation": "MACD line crossing signal line indicates potential trend change."
    },
    {
        "q": "What is a Fair Value Gap (FVG)?",
        "options": ["Price difference between exchanges", "3-candle imbalance in price", "Gap in trading hours", "Funding rate gap"],
        "answer": 1,
        "explanation": "FVG = 3 candles where candle 1 and 3 wicks don't overlap — price tends to fill this gap."
    },
    {
        "q": "What percentage of account should you risk per trade (safe rule)?",
        "options": ["5-10%", "10-20%", "1-2%", "0.1%"],
        "answer": 2,
        "explanation": "1-2% per trade. At 1%, you can lose 100 trades in a row before account is gone."
    },
    {
        "q": "What is revenge trading?",
        "options": ["Trading profitably after a win", "Taking impulsive trades to recover losses", "Copying another trader", "Short selling"],
        "answer": 1,
        "explanation": "Revenge trading = emotional trading after losses, almost always leads to more losses."
    },
    {
        "q": "What is an Order Block?",
        "options": ["A large limit order on order book", "Last candle before a big institutional move", "A trading halt", "Blocked exchange account"],
        "answer": 1,
        "explanation": "Order block = the last opposite candle before a strong impulsive move, where institutions placed orders."
    },
    {
        "q": "What does 'Higher High, Higher Low' indicate?",
        "options": ["Downtrend", "Sideways market", "Uptrend / Bullish structure", "Reversal pattern"],
        "answer": 2,
        "explanation": "HH + HL = bullish market structure. Always trade with the structure."
    },
]
