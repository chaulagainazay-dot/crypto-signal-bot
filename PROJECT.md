# HCG Live Signal Bot — Project Documentation

## Overview

A private Telegram Mini App (WebApp) for the HCG group, functioning as a personal crypto trading guide and portfolio tracker. Opens full-screen inside Telegram via `@hcglivesignalbot`. Access is restricted — users must request and receive admin approval before using the app.

**Stack:** React 18 + Vite 5 (frontend) · Python aiohttp (static server) · python-telegram-bot 22.5 (bot) · Railway (hosting)

**Theme:** Dark crypto (#0D0D0D background, #F7931A orange accent)

---

## Architecture

```
Railway deployment
├── run_all.py              — starts 3 subprocesses
│   ├── serve_webapp.py     — aiohttp static server on $PORT (8080)
│   │   └── webapp/dist/    — built React app (committed to git)
│   ├── main.py             — @hcglivesignalbot (crypto bot, token 8875660499)
│   └── nepse/main.py       — NEPSE bot (token 8900086901)
│
├── access_control.py       — shared access registry (data/access.json)
└── webapp/src/             — React source
```

### API Data Sources (all free, no keys)

| Source | Used for |
|--------|----------|
| CoinGecko | Prices, market data, trending, search, OHLC |
| CoinCap | Fallback for prices + coin detail |
| Binance | Fallback for OHLC candle data |
| DexScreener | Fallback for trending + DEX token search |
| GeckoTerminal | Contract address / DEX token lookup |
| CryptoCompare | News articles |
| alternative.me | Fear & Greed Index |

All API calls use a `tryOr(primary, ...fallbacks)` waterfall — if CoinGecko rate-limits, the next source is tried silently. Users never see blank screens.

---

## Railway Environment Variables

| Variable | Value / Description |
|----------|---------------------|
| `TELEGRAM_BOT_TOKEN` | Crypto bot token (`8875660499:AAE...`) |
| `TELEGRAM_CHAT_ID` | Admin Telegram user ID (`919874672`) |
| `WEBAPP_URL` | Public Railway URL for the Mini App |
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `EXCHANGE` | Exchange identifier |
| `WATCHLIST` | Comma-separated coin watchlist |

---

## Access Control System

New users see a registration gate when they open the app. The flow:

1. App reads `window.Telegram.WebApp.initDataUnsafe.user` for the Telegram user ID
2. Calls `GET /api/check?user_id=XXX` — returns `{approved, pending}`
3. If not approved: shows registration form (name read-only, reason textarea)
4. On submit: `POST /api/register` → saves to `data/access.json` → notifies admin via Telegram with **Approve / Deny** inline buttons
5. Admin taps Approve → user gains access immediately on next app open

**Bot commands (admin only):**
- `/access` — list all pending/approved users
- `/approve <user_id>` — approve a user
- `/deny <user_id>` — deny a user
- `/revoke <user_id>` — revoke access

All bot menu commands and free-text handling are locked to approved users.

---

## Webapp Tabs

### 🤖 Guide
Personal trading assistant. Four sections (pill nav):

- **📋 Briefing** — Fear & Greed gauge, global market stats (total mcap, volume, BTC/ETH dominance), today's top momentum coins, trending coins from CoinGecko, crypto headlines
- **📰 News** — 20 latest general crypto market articles from CryptoCompare, with bullish/bearish/neutral sentiment badges and article previews
- **📚 Learn** — 8 expandable trading education cards (DCA, stop-loss, market cap vs price, volume, FOMO, BTC dominance, risk management, news impact)
- **🧠 Quiz** — 4 interactive multiple-choice questions to test trading knowledge

### 🎯 Signals
Buy/sell signal scanner. Sources top 150 coins + trending extras not in top 150.

- **Filters:** All · 🚀 Buy · 📉 Sell · 🔥 Trending · 🌱 Small Cap
- Each card shows signal label, score bar (0–100), expandable **WHY** reasons
- Score factors: 24h change, 7d change, volume/mcap ratio, trending bonus, small cap bonus
- Signal labels: STRONG BUY / BUY / HOLD / SELL / STRONG SELL

### 📊 Strategy
6 real trader strategies with full detail:

| Strategy | Inspired by |
|----------|------------|
| DCA (Dollar-Cost Averaging) | Buffett / Bogle |
| Swing Trading | Minervini / Raschke |
| Breakout Trading | O'Neil / Livermore |
| Trend Following | Dennis / Turtle Traders |
| Altcoin Rotation | — |
| RSI Bounce | Wilder / Connors |

Also includes a **Portfolio Growth Calculator** — enter starting capital, monthly contribution, expected APY, and years to see projected value with a bar chart and monthly milestones. Plus an **Allocation Bar** showing recommended top/mid/small cap splits per strategy.

### 💼 Portfolio
Personal holdings tracker. Supports any token (not just top coins).

- **Add holding:** debounced search calls CoinGecko `/search` → select from results → enter amount + buy price
- Stores `coinId` (not just symbol) so any obscure token works
- Live price fetched per holding via `fetchCoinDetail(coinId)`
- Shows: current price, total value, PnL %, 24h change
- localStorage key: `hcg_portfolio_v3`

### 🔍 Research
Deep-dive tool for any coin. Search by name or contract address.

- Price chart (bar graph with buy/sell signal overlay)
- Candlestick OHLC chart
- Full market stats, links, description
- Latest news for the searched coin

### 🔔 Alerts
Two sections (pill nav):

- **💼 Portfolio Signals** — for each coin in your portfolio: live buy/sell signal card, signal score bar, recommendation text ("Consider adding more" / "Consider reducing position"), collapsible latest news section (4 articles from CryptoCompare)
- **🔔 Price Alerts** — manual alerts: set a target price and direction (above/below) for any symbol; shows live current price, distance to target, triggers "🔔 Triggered!" badge when hit

---

## File Structure

```
webapp/src/
├── App.jsx                 — root, tab router, AccessGate wrapper
├── App.css                 — global dark theme, CSS variables, utility classes
├── api/
│   └── coingecko.js        — all API calls with tryOr fallback waterfall
├── components/
│   ├── AccessGate.jsx      — registration gate (checks/submits access)
│   ├── BottomNav.jsx       — 5-tab bottom navigation bar
│   ├── CandlestickChart.jsx— OHLC candle chart (SVG)
│   ├── CoinCard.jsx        — reusable coin price card
│   ├── Sparkline.jsx       — inline price sparkline (SVG)
│   └── Spinner.jsx         — loading spinner
└── tabs/
    ├── Guide.jsx           — Briefing / News / Learn / Quiz
    ├── Signals.jsx         — buy/sell signal scanner
    ├── Strategy.jsx        — 6 strategies + growth calculator
    ├── Portfolio.jsx       — holdings tracker with live search
    ├── Research.jsx        — coin deep-dive + contract lookup
    └── Alerts.jsx          — portfolio signals + price alerts
```

```
(root)/
├── main.py                 — crypto Telegram bot
├── serve_webapp.py         — aiohttp static file server + /api/check + /api/register
├── access_control.py       — access registry (read/write data/access.json)
├── run_all.py              — process supervisor (webapp + crypto bot + NEPSE bot)
├── state_manager.py        — user state persistence
├── scanner.py              — signal scanning logic
├── config.py               — configuration constants
├── Procfile                — Railway: `worker: python run_all.py`
├── requirements.txt        — Python dependencies
├── runtime.txt             — Python version pin
├── nepse/
│   └── main.py             — NEPSE stock signal bot
└── data/
    └── access.json         — runtime access registry (gitignored, auto-created)
```

---

## Deployment

Railway auto-deploys on git push via `railway up`. The `webapp/dist/` folder is **committed to git** (Railway does not run `npm run build` — the Python Procfile has no Node step).

**Deploy workflow:**
```bash
# After any React changes:
cd webapp && npm run build
cd ..
git rm webapp/dist/assets/index-<old-hash>.js
git add webapp/dist/
git commit -m "feat/fix: description"
railway up --detach
```

**Bot commands available:**
`/start` · `/price` · `/alert` · `/dca` · `/addholding` · `/removeholding` · `/token` · `/journal` · `/calc` · `/access` · `/approve` · `/deny` · `/revoke`

---

## Known Issues

- **409 Conflict in logs** — Two bot instances occasionally conflict on `getUpdates`. Pre-existing issue from NEPSE bot running alongside crypto bot on the same Railway service. Non-breaking; the supervisor auto-restarts crashed processes.
- **CoinGecko rate limits** — Free tier limits apply (~30 req/min). Handled by silent fallback chain.
