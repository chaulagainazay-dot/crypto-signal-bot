# Telegram Mini App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-screen Telegram Mini App (WebApp) for @hcglivesignalbot with 5 tabs — Market, Signals, Portfolio, Research, Alerts — served as static files from the existing Python bot on Railway.

**Architecture:** A React + Vite SPA lives in `webapp/` inside the existing repo. The Python bot serves `webapp/dist/` as static files on port 8080 via aiohttp alongside polling. The Mini App URL is set as the bot's `web_app` button. All market data is fetched directly from CoinGecko/GeckoTerminal APIs in the browser.

**Tech Stack:** React 18, Vite 5, @twa-dev/sdk (Telegram WebApp), aiohttp 3.x (already in requirements.txt), CoinGecko free API, GeckoTerminal free API.

## Global Constraints

- Python 3.9 on Railway (existing runtime)
- aiohttp already in requirements.txt — no new Python deps
- webapp/ is pure frontend — no build step on Railway (pre-build locally, commit dist/)
- Telegram.WebApp theme variables used for all colors
- Dark crypto aesthetic — orange accent (#F7931A), dark bg (#0D0D0D)
- All API calls from browser — CORS allowed on CoinGecko/GeckoTerminal
- PORT env var used for aiohttp server (Railway sets this)
- Bot token: existing TELEGRAM_BOT_TOKEN env var

---

## File Map

**Create:**
- `webapp/index.html` — Vite entry point
- `webapp/package.json` — React + Vite deps
- `webapp/vite.config.js` — build config
- `webapp/src/main.jsx` — React root
- `webapp/src/App.jsx` — bottom nav shell + tab router
- `webapp/src/App.css` — global dark theme
- `webapp/src/api/coingecko.js` — CoinGecko + GeckoTerminal fetch helpers
- `webapp/src/tabs/Market.jsx` — live prices, gainers/losers, global stats
- `webapp/src/tabs/Signals.jsx` — buy/sell signal cards
- `webapp/src/tabs/Portfolio.jsx` — holdings list + P&L
- `webapp/src/tabs/Research.jsx` — coin search + contract address input
- `webapp/src/tabs/Alerts.jsx` — price alert list + add form
- `webapp/src/components/BottomNav.jsx` — 5-tab navigation bar
- `webapp/src/components/CoinCard.jsx` — reusable price card
- `webapp/src/components/Spinner.jsx` — loading spinner
- `webapp/dist/` — pre-built output committed to repo

**Modify:**
- `serve_webapp.py` (new) — aiohttp static file server
- `run_all.py` — add webapp server subprocess
- `main.py` — add WebApp button to /start and main_keyboard()

---

### Task 1: React + Vite scaffold

**Files:**
- Create: `webapp/package.json`
- Create: `webapp/vite.config.js`
- Create: `webapp/index.html`
- Create: `webapp/src/main.jsx`

- [ ] **Step 1: Create webapp/package.json**

```json
{
  "name": "hcg-trading-webapp",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@twa-dev/sdk": "^7.10.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 2: Create webapp/vite.config.js**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
```

- [ ] **Step 3: Create webapp/index.html**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>HCG Live Signal</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create webapp/src/main.jsx**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './App.css'

window.Telegram?.WebApp?.ready()
window.Telegram?.WebApp?.expand()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

- [ ] **Step 5: Install dependencies and verify scaffold builds**

```bash
cd ~/crypto-signal-agent/webapp
npm install
npm run build
# Expected: dist/ folder created with index.html
```

---

### Task 2: Global styles + design tokens

**Files:**
- Create: `webapp/src/App.css`

- [ ] **Step 1: Create webapp/src/App.css**

```css
:root {
  --bg: #0D0D0D;
  --bg2: #1A1A1A;
  --bg3: #242424;
  --accent: #F7931A;
  --accent2: #E8820A;
  --green: #00C853;
  --red: #FF3D57;
  --text: #FFFFFF;
  --text2: #A0A0A0;
  --border: #2A2A2A;
  --nav-h: 64px;
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  overflow: hidden;
  height: 100vh;
}

#root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 16px calc(var(--nav-h) + var(--safe-bottom) + 8px);
  -webkit-overflow-scrolling: touch;
}

.card {
  background: var(--bg2);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
  border: 1px solid var(--border);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}
.badge-green { background: rgba(0,200,83,0.15); color: var(--green); }
.badge-red   { background: rgba(255,61,87,0.15); color: var(--red); }
.badge-orange{ background: rgba(247,147,26,0.15); color: var(--accent); }

.row { display: flex; align-items: center; justify-content: space-between; }
.col { display: flex; flex-direction: column; gap: 2px; }

h2 { font-size: 18px; font-weight: 700; margin-bottom: 14px; }
h3 { font-size: 15px; font-weight: 600; }

.muted { color: var(--text2); font-size: 12px; }

.btn {
  background: var(--accent);
  color: #000;
  border: none;
  border-radius: 10px;
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  width: 100%;
  margin-top: 8px;
}
.btn:active { opacity: 0.8; }

input {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  color: var(--text);
  font-size: 14px;
  width: 100%;
  outline: none;
}
input:focus { border-color: var(--accent); }

.section-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin: 16px 0 8px;
}

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
.skeleton {
  background: var(--bg3);
  border-radius: 8px;
  animation: pulse 1.5s infinite;
}
```

---

### Task 3: API helpers

**Files:**
- Create: `webapp/src/api/coingecko.js`

- [ ] **Step 1: Create webapp/src/api/coingecko.js**

```js
const CG = 'https://api.coingecko.com/api/v3'
const GT = 'https://api.geckoterminal.com/api/v2'

async function get(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(10000) })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function fetchGlobal() {
  const d = await get(`${CG}/global`)
  const m = d.data
  return {
    mcap: m.total_market_cap.usd,
    vol: m.total_volume.usd,
    btcDom: m.market_cap_percentage.btc,
    ethDom: m.market_cap_percentage.eth,
    change: m.market_cap_change_percentage_24h_usd,
    coins: m.active_cryptocurrencies,
  }
}

export async function fetchTopCoins(limit = 50) {
  return get(`${CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=${limit}&page=1&price_change_percentage=24h`)
}

export async function fetchTrending() {
  const d = await get(`${CG}/search/trending`)
  return d.coins.map(c => c.item)
}

export async function fetchCoinDetail(id) {
  return get(`${CG}/coins/${id}?localization=false&tickers=false&community_data=false&developer_data=false`)
}

export async function searchCoins(q) {
  const d = await get(`${CG}/search?query=${encodeURIComponent(q)}`)
  return d.coins.slice(0, 8)
}

const GT_NETS = ['bsc','eth','polygon_pos','arbitrum','base','solana','optimism','avalanche']

export async function fetchByContract(address) {
  const lower = address.toLowerCase()
  for (const net of GT_NETS) {
    try {
      const d = await get(`${GT}/networks/${net}/tokens/${lower}`)
      const a = d?.data?.attributes
      if (a?.price_usd) return { ...a, _network: net, _source: 'geckoterminal' }
    } catch { /* try next */ }
  }
  return null
}

export async function fetchGTPool(network, address) {
  const d = await get(`${GT}/networks/${network}/pools/${address.toLowerCase()}`)
  return d?.data?.attributes
}

export function fp(price) {
  if (!price || price === 0) return '0'
  price = parseFloat(price)
  if (price >= 1000) return price.toLocaleString('en', { maximumFractionDigits: 2 })
  if (price >= 1) return price.toFixed(4)
  if (price >= 0.01) return price.toFixed(6)
  return price.toFixed(8)
}

export function fmcap(v) {
  v = parseFloat(v) || 0
  if (v >= 1e12) return `$${(v/1e12).toFixed(2)}T`
  if (v >= 1e9) return `$${(v/1e9).toFixed(2)}B`
  if (v >= 1e6) return `$${(v/1e6).toFixed(1)}M`
  return `$${v.toLocaleString()}`
}
```

---

### Task 4: Reusable components

**Files:**
- Create: `webapp/src/components/Spinner.jsx`
- Create: `webapp/src/components/CoinCard.jsx`
- Create: `webapp/src/components/BottomNav.jsx`

- [ ] **Step 1: Create webapp/src/components/Spinner.jsx**

```jsx
export default function Spinner() {
  return (
    <div style={{ display:'flex', justifyContent:'center', padding:'40px 0' }}>
      <div style={{
        width: 32, height: 32,
        border: '3px solid #2A2A2A',
        borderTop: '3px solid #F7931A',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
```

- [ ] **Step 2: Create webapp/src/components/CoinCard.jsx**

```jsx
import { fp } from '../api/coingecko'

export default function CoinCard({ coin, onClick }) {
  const chg = coin.price_change_percentage_24h ?? 0
  const isUp = chg >= 0
  return (
    <div className="card" style={{ cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <div className="row">
        <div className="col">
          <div className="row" style={{ gap: 8 }}>
            {coin.image && (
              <img src={coin.image} alt={coin.symbol} width={28} height={28}
                style={{ borderRadius: '50%' }} />
            )}
            <div>
              <h3>{coin.symbol?.toUpperCase()}</h3>
              <span className="muted">{coin.name}</span>
            </div>
          </div>
        </div>
        <div className="col" style={{ alignItems:'flex-end' }}>
          <strong style={{ fontSize: 15 }}>${fp(coin.current_price)}</strong>
          <span className={`badge badge-${isUp ? 'green' : 'red'}`}>
            {isUp ? '▲' : '▼'} {Math.abs(chg).toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create webapp/src/components/BottomNav.jsx**

```jsx
const TABS = [
  { id: 'market',    icon: '📈', label: 'Market'   },
  { id: 'signals',   icon: '🎯', label: 'Signals'  },
  { id: 'portfolio', icon: '💼', label: 'Portfolio' },
  { id: 'research',  icon: '🔍', label: 'Research'  },
  { id: 'alerts',    icon: '🔔', label: 'Alerts'   },
]

export default function BottomNav({ active, onSelect }) {
  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: 0, right: 0,
      height: 'calc(64px + env(safe-area-inset-bottom, 0px))',
      background: '#1A1A1A',
      borderTop: '1px solid #2A2A2A',
      display: 'flex',
      zIndex: 100,
    }}>
      {TABS.map(t => (
        <button key={t.id} onClick={() => onSelect(t.id)} style={{
          flex: 1, background: 'none', border: 'none', cursor: 'pointer',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 2, paddingBottom: 'env(safe-area-inset-bottom,0)',
          color: active === t.id ? '#F7931A' : '#606060',
          transition: 'color 0.15s',
        }}>
          <span style={{ fontSize: 20 }}>{t.icon}</span>
          <span style={{ fontSize: 10, fontWeight: active === t.id ? 700 : 400 }}>{t.label}</span>
        </button>
      ))}
    </nav>
  )
}
```

---

### Task 5: Market tab

**Files:**
- Create: `webapp/src/tabs/Market.jsx`

- [ ] **Step 1: Create webapp/src/tabs/Market.jsx**

```jsx
import { useState, useEffect } from 'react'
import { fetchGlobal, fetchTopCoins, fetchTrending, fmcap, fp } from '../api/coingecko'
import CoinCard from '../components/CoinCard'
import Spinner from '../components/Spinner'

const VIEWS = ['Overview', 'Gainers', 'Losers', 'Trending', 'Volume']

export default function Market({ onResearch }) {
  const [view, setView] = useState('Overview')
  const [global, setGlobal] = useState(null)
  const [coins, setCoins] = useState([])
  const [trending, setTrending] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchGlobal(), fetchTopCoins(100), fetchTrending()])
      .then(([g, c, t]) => { setGlobal(g); setCoins(c); setTrending(t) })
      .finally(() => setLoading(false))
  }, [])

  const displayed = () => {
    if (view === 'Gainers') return [...coins].sort((a,b) => (b.price_change_percentage_24h||0)-(a.price_change_percentage_24h||0)).slice(0,20)
    if (view === 'Losers')  return [...coins].sort((a,b) => (a.price_change_percentage_24h||0)-(b.price_change_percentage_24h||0)).slice(0,20)
    if (view === 'Volume')  return [...coins].sort((a,b) => (b.total_volume||0)-(a.total_volume||0)).slice(0,20)
    return coins.slice(0, 20)
  }

  return (
    <div className="tab-content">
      <h2>📈 Market</h2>

      {/* Pill filter */}
      <div style={{ display:'flex', gap:8, marginBottom:16, overflowX:'auto', paddingBottom:4 }}>
        {VIEWS.map(v => (
          <button key={v} onClick={() => setView(v)} style={{
            padding: '6px 14px', borderRadius: 20, border: 'none', cursor: 'pointer',
            background: view===v ? '#F7931A' : '#1A1A1A',
            color: view===v ? '#000' : '#A0A0A0',
            fontWeight: view===v ? 700 : 400,
            fontSize: 13, whiteSpace: 'nowrap',
          }}>{v}</button>
        ))}
      </div>

      {loading && <Spinner />}

      {/* Global stats card */}
      {!loading && view === 'Overview' && global && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="section-title">Global Market</div>
          <div className="row" style={{ marginTop: 8 }}>
            <div className="col">
              <span className="muted">Market Cap</span>
              <strong>{fmcap(global.mcap)}</strong>
            </div>
            <div className="col" style={{ alignItems:'center' }}>
              <span className="muted">24h Volume</span>
              <strong>{fmcap(global.vol)}</strong>
            </div>
            <div className="col" style={{ alignItems:'flex-end' }}>
              <span className="muted">BTC Dom</span>
              <strong>{global.btcDom.toFixed(1)}%</strong>
            </div>
          </div>
          <div className="row" style={{ marginTop:10 }}>
            <span className="muted">24h Change</span>
            <span className={`badge badge-${global.change>=0?'green':'red'}`}>
              {global.change>=0?'▲':'▼'} {Math.abs(global.change).toFixed(2)}%
            </span>
          </div>
        </div>
      )}

      {/* Trending list */}
      {!loading && view === 'Trending' && (
        <>
          {trending.map((c, i) => (
            <div key={c.id} className="card" onClick={() => onResearch?.(c.id)} style={{ cursor:'pointer' }}>
              <div className="row">
                <div className="row" style={{ gap:10 }}>
                  <span style={{ color:'#606060', width:20 }}>#{i+1}</span>
                  {c.small && <img src={c.small} width={28} height={28} style={{ borderRadius:'50%' }} />}
                  <div>
                    <h3>{c.symbol?.toUpperCase()}</h3>
                    <span className="muted">{c.name}</span>
                  </div>
                </div>
                <span className="badge badge-orange">🔥 Trending</span>
              </div>
            </div>
          ))}
        </>
      )}

      {/* Coin list */}
      {!loading && view !== 'Trending' && displayed().map(c => (
        <CoinCard key={c.id} coin={c} onClick={() => onResearch?.(c.id)} />
      ))}
    </div>
  )
}
```

---

### Task 6: Signals tab

**Files:**
- Create: `webapp/src/tabs/Signals.jsx`

- [ ] **Step 1: Create webapp/src/tabs/Signals.jsx**

```jsx
import { useState, useEffect } from 'react'
import { fetchTopCoins, fp } from '../api/coingecko'
import Spinner from '../components/Spinner'

function signalStrength(coin) {
  const chg = coin.price_change_percentage_24h || 0
  const vol = coin.total_volume || 0
  const mcap = coin.market_cap || 1
  const volRatio = vol / mcap
  if (chg > 8 && volRatio > 0.15) return { type:'STRONG BUY', color:'#00C853', score: 5 }
  if (chg > 4 && volRatio > 0.08) return { type:'BUY',        color:'#4CAF50', score: 4 }
  if (chg < -8 && volRatio > 0.15) return { type:'STRONG SELL',color:'#FF3D57', score: 1 }
  if (chg < -4 && volRatio > 0.08) return { type:'SELL',       color:'#F44336', score: 2 }
  return { type:'NEUTRAL', color:'#A0A0A0', score: 3 }
}

export default function Signals() {
  const [coins, setCoins] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('All')

  useEffect(() => {
    fetchTopCoins(100).then(setCoins).finally(() => setLoading(false))
  }, [])

  const withSignals = coins.map(c => ({ ...c, signal: signalStrength(c) }))
  const filtered = filter === 'All' ? withSignals
    : filter === 'Buy' ? withSignals.filter(c => c.signal.score >= 4)
    : withSignals.filter(c => c.signal.score <= 2)

  return (
    <div className="tab-content">
      <h2>🎯 Signals</h2>
      <div style={{ display:'flex', gap:8, marginBottom:16 }}>
        {['All','Buy','Sell'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding:'6px 16px', borderRadius:20, border:'none', cursor:'pointer',
            background: filter===f ? '#F7931A' : '#1A1A1A',
            color: filter===f ? '#000' : '#A0A0A0',
            fontWeight: filter===f ? 700 : 400, fontSize: 13,
          }}>{f}</button>
        ))}
      </div>
      {loading && <Spinner />}
      {!loading && filtered.slice(0,30).map(c => (
        <div key={c.id} className="card">
          <div className="row">
            <div className="row" style={{ gap:10 }}>
              {c.image && <img src={c.image} width={28} height={28} style={{ borderRadius:'50%' }} />}
              <div>
                <h3>{c.symbol?.toUpperCase()}</h3>
                <span className="muted">${fp(c.current_price)}</span>
              </div>
            </div>
            <div className="col" style={{ alignItems:'flex-end' }}>
              <span style={{
                background: c.signal.color+'22', color: c.signal.color,
                padding:'3px 10px', borderRadius:8, fontSize:11, fontWeight:700,
              }}>{c.signal.type}</span>
              <span className={`badge badge-${(c.price_change_percentage_24h||0)>=0?'green':'red'}`} style={{ marginTop:4 }}>
                {(c.price_change_percentage_24h||0)>=0?'▲':'▼'} {Math.abs(c.price_change_percentage_24h||0).toFixed(2)}%
              </span>
            </div>
          </div>
          <div className="row" style={{ marginTop:10 }}>
            <span className="muted">Vol/MCap ratio</span>
            <span style={{ fontSize:12, color:'#A0A0A0' }}>
              {((c.total_volume/c.market_cap)*100).toFixed(1)}%
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
```

---

### Task 7: Portfolio tab

**Files:**
- Create: `webapp/src/tabs/Portfolio.jsx`

- [ ] **Step 1: Create webapp/src/tabs/Portfolio.jsx**

```jsx
import { useState, useEffect } from 'react'
import { fetchTopCoins, fp, fmcap } from '../api/coingecko'

const STORAGE_KEY = 'hcg_portfolio'

function loadHoldings() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] } catch { return [] }
}
function saveHoldings(h) { localStorage.setItem(STORAGE_KEY, JSON.stringify(h)) }

export default function Portfolio() {
  const [holdings, setHoldings] = useState(loadHoldings)
  const [prices, setPrices] = useState({})
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ symbol:'', amount:'', buyPrice:'' })

  useEffect(() => {
    fetchTopCoins(100).then(coins => {
      const map = {}
      coins.forEach(c => { map[c.symbol.toUpperCase()] = c })
      setPrices(map)
    })
  }, [])

  const totalValue = holdings.reduce((sum, h) => {
    const coin = prices[h.symbol.toUpperCase()]
    return sum + (coin ? coin.current_price * h.amount : 0)
  }, 0)

  const totalCost = holdings.reduce((sum, h) => sum + h.buyPrice * h.amount, 0)
  const totalPnl = totalValue - totalCost
  const pnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0

  function addHolding() {
    if (!form.symbol || !form.amount) return
    const h = { symbol: form.symbol.toUpperCase(), amount: parseFloat(form.amount), buyPrice: parseFloat(form.buyPrice)||0 }
    const updated = [...holdings, h]
    setHoldings(updated); saveHoldings(updated)
    setForm({ symbol:'', amount:'', buyPrice:'' }); setAdding(false)
  }

  function remove(i) {
    const updated = holdings.filter((_,j) => j!==i)
    setHoldings(updated); saveHoldings(updated)
  }

  return (
    <div className="tab-content">
      <h2>💼 Portfolio</h2>

      {/* Summary card */}
      <div className="card" style={{ marginBottom:16, background: '#1A1A1A' }}>
        <div className="section-title">Total Value</div>
        <div style={{ fontSize:28, fontWeight:800, marginTop:6 }}>{fmcap(totalValue)}</div>
        <div style={{ marginTop:6 }}>
          <span className={`badge badge-${totalPnl>=0?'green':'red'}`}>
            {totalPnl>=0?'▲':'▼'} {fmcap(Math.abs(totalPnl))} ({Math.abs(pnlPct).toFixed(2)}%)
          </span>
        </div>
      </div>

      {/* Holdings */}
      {holdings.map((h,i) => {
        const coin = prices[h.symbol]
        const currentVal = coin ? coin.current_price * h.amount : 0
        const costBasis = h.buyPrice * h.amount
        const pnl = currentVal - costBasis
        const pct = costBasis > 0 ? (pnl/costBasis)*100 : 0
        return (
          <div key={i} className="card">
            <div className="row">
              <div>
                <h3>{h.symbol}</h3>
                <span className="muted">{h.amount} coins</span>
              </div>
              <div className="col" style={{ alignItems:'flex-end' }}>
                <strong>{fmcap(currentVal)}</strong>
                <span className={`badge badge-${pnl>=0?'green':'red'}`}>
                  {pnl>=0?'+':''}{pct.toFixed(2)}%
                </span>
              </div>
            </div>
            <div className="row" style={{ marginTop:8 }}>
              <span className="muted">Avg buy: ${fp(h.buyPrice)}</span>
              <button onClick={() => remove(i)} style={{
                background:'none', border:'none', color:'#606060', cursor:'pointer', fontSize:18
              }}>✕</button>
            </div>
          </div>
        )
      })}

      {adding ? (
        <div className="card">
          <div className="section-title">Add Holding</div>
          <input placeholder="Symbol (BTC)" value={form.symbol}
            onChange={e => setForm(f=>({...f,symbol:e.target.value}))} style={{ marginTop:10 }} />
          <input placeholder="Amount" type="number" value={form.amount}
            onChange={e => setForm(f=>({...f,amount:e.target.value}))} style={{ marginTop:8 }} />
          <input placeholder="Buy price (USD)" type="number" value={form.buyPrice}
            onChange={e => setForm(f=>({...f,buyPrice:e.target.value}))} style={{ marginTop:8 }} />
          <button className="btn" onClick={addHolding}>Add</button>
          <button onClick={() => setAdding(false)} style={{
            background:'none', border:'none', color:'#A0A0A0', cursor:'pointer',
            width:'100%', marginTop:8, padding:8
          }}>Cancel</button>
        </div>
      ) : (
        <button className="btn" onClick={() => setAdding(true)}>+ Add Holding</button>
      )}
    </div>
  )
}
```

---

### Task 8: Research tab

**Files:**
- Create: `webapp/src/tabs/Research.jsx`

- [ ] **Step 1: Create webapp/src/tabs/Research.jsx**

```jsx
import { useState, useEffect } from 'react'
import { fetchCoinDetail, searchCoins, fetchByContract, fp, fmcap } from '../api/coingecko'
import Spinner from '../components/Spinner'

function isAddress(s) {
  return /^0x[0-9a-fA-F]{40}$/.test(s) || /^[1-9A-HJ-NP-Za-km-z]{32,88}$/.test(s)
}

function CoinDetail({ data, source }) {
  const md = data.market_data || {}
  const price = source === 'geckoterminal' ? parseFloat(data.price_usd||0)
    : md.current_price?.usd || 0
  const chg24 = source === 'geckoterminal'
    ? parseFloat(data.price_change_percentage?.h24||0)
    : md.price_change_percentage_24h || 0
  const mcap = source === 'geckoterminal'
    ? parseFloat(data.market_cap_usd||data.fdv_usd||0)
    : md.market_cap?.usd || 0
  const vol = source === 'geckoterminal'
    ? parseFloat(data.volume_usd?.h24||0)
    : md.total_volume?.usd || 0
  const name = data.name || data.symbol
  const symbol = (data.symbol||'').toUpperCase()
  const isUp = chg24 >= 0

  return (
    <div className="card">
      <div className="row">
        <div>
          <h3 style={{ fontSize:18 }}>{name} <span className="muted">({symbol})</span></h3>
          {source === 'geckoterminal' && (
            <span className="badge badge-orange" style={{ marginTop:4, display:'inline-block' }}>
              GeckoTerminal · {data._network?.toUpperCase()}
            </span>
          )}
        </div>
        <div className="col" style={{ alignItems:'flex-end' }}>
          <strong style={{ fontSize:20 }}>${fp(price)}</strong>
          <span className={`badge badge-${isUp?'green':'red'}`}>
            {isUp?'▲':'▼'} {Math.abs(chg24).toFixed(2)}%
          </span>
        </div>
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginTop:14 }}>
        {[
          ['Market Cap', fmcap(mcap)],
          ['24h Volume', fmcap(vol)],
          ...(md.ath?.usd ? [['ATH', `$${fp(md.ath.usd)}`]] : []),
          ...(md.price_change_percentage_7d ? [['7d Change', `${md.price_change_percentage_7d.toFixed(2)}%`]] : []),
        ].map(([k,v]) => (
          <div key={k}>
            <span className="muted">{k}</span>
            <div style={{ fontWeight:600, marginTop:2 }}>{v}</div>
          </div>
        ))}
      </div>
      {data.description?.en && (
        <p style={{ marginTop:12, fontSize:12, color:'#A0A0A0', lineHeight:1.5 }}>
          {data.description.en.split('.')[0]}.
        </p>
      )}
    </div>
  )
}

export default function Research({ initialId }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [detail, setDetail] = useState(null)
  const [source, setSource] = useState('coingecko')
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  useEffect(() => {
    if (initialId) loadDetail(initialId)
  }, [initialId])

  async function handleSearch() {
    if (!query.trim()) return
    setLoading(true); setDetail(null); setSearched(true)
    try {
      if (isAddress(query.trim())) {
        const r = await fetchByContract(query.trim())
        if (r) { setDetail(r); setSource('geckoterminal'); setResults([]) }
        else setResults([])
      } else {
        const r = await searchCoins(query.trim())
        setResults(r)
      }
    } finally { setLoading(false) }
  }

  async function loadDetail(id) {
    setLoading(true); setResults([])
    try {
      const d = await fetchCoinDetail(id)
      setDetail(d); setSource('coingecko')
    } finally { setLoading(false) }
  }

  return (
    <div className="tab-content">
      <h2>🔍 Research</h2>
      <div style={{ display:'flex', gap:8, marginBottom:16 }}>
        <input
          placeholder="BTC, ethereum, or 0x contract..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key==='Enter' && handleSearch()}
        />
        <button onClick={handleSearch} style={{
          background:'#F7931A', border:'none', borderRadius:10,
          padding:'0 16px', color:'#000', fontWeight:700, cursor:'pointer', flexShrink:0
        }}>Go</button>
      </div>

      {loading && <Spinner />}

      {detail && !loading && <CoinDetail data={detail} source={source} />}

      {!loading && !detail && results.map(c => (
        <div key={c.id} className="card" onClick={() => loadDetail(c.id)} style={{ cursor:'pointer' }}>
          <div className="row">
            <div className="row" style={{ gap:10 }}>
              {c.thumb && <img src={c.thumb} width={28} height={28} style={{ borderRadius:'50%' }} />}
              <div>
                <h3>{c.symbol?.toUpperCase()}</h3>
                <span className="muted">{c.name}</span>
              </div>
            </div>
            <span className="muted">#{c.market_cap_rank || '?'}</span>
          </div>
        </div>
      ))}

      {!loading && searched && !detail && results.length === 0 && (
        <div style={{ textAlign:'center', color:'#606060', padding:'40px 0' }}>
          No results found. Try a different name or contract address.
        </div>
      )}
    </div>
  )
}
```

---

### Task 9: Alerts tab

**Files:**
- Create: `webapp/src/tabs/Alerts.jsx`

- [ ] **Step 1: Create webapp/src/tabs/Alerts.jsx**

```jsx
import { useState, useEffect } from 'react'
import { fetchTopCoins, fp } from '../api/coingecko'

const STORAGE_KEY = 'hcg_alerts'

function loadAlerts() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] } catch { return [] }
}
function saveAlerts(a) { localStorage.setItem(STORAGE_KEY, JSON.stringify(a)) }

export default function Alerts() {
  const [alerts, setAlerts] = useState(loadAlerts)
  const [prices, setPrices] = useState({})
  const [form, setForm] = useState({ symbol:'', target:'', direction:'above' })
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    fetchTopCoins(100).then(coins => {
      const map = {}
      coins.forEach(c => { map[c.symbol.toUpperCase()] = c.current_price })
      setPrices(map)
    })
  }, [])

  function addAlert() {
    if (!form.symbol || !form.target) return
    const a = { symbol: form.symbol.toUpperCase(), target: parseFloat(form.target), direction: form.direction, created: Date.now() }
    const updated = [...alerts, a]
    setAlerts(updated); saveAlerts(updated)
    setForm({ symbol:'', target:'', direction:'above' }); setAdding(false)
  }

  function remove(i) {
    const updated = alerts.filter((_,j) => j!==i)
    setAlerts(updated); saveAlerts(updated)
  }

  return (
    <div className="tab-content">
      <h2>🔔 Alerts</h2>
      <p className="muted" style={{ marginBottom:16 }}>
        Set price targets. Alerts are stored locally — use the bot's /alert command for push notifications.
      </p>

      {alerts.map((a,i) => {
        const current = prices[a.symbol] || 0
        const hit = a.direction==='above' ? current >= a.target : current <= a.target
        return (
          <div key={i} className="card">
            <div className="row">
              <div>
                <h3>{a.symbol}</h3>
                <span className="muted">
                  {a.direction === 'above' ? '▲ Above' : '▼ Below'} ${fp(a.target)}
                </span>
              </div>
              <div className="col" style={{ alignItems:'flex-end' }}>
                {hit
                  ? <span className="badge badge-orange">🔔 HIT</span>
                  : <span className="badge" style={{ background:'#242424', color:'#606060' }}>Watching</span>
                }
                {current > 0 && <span className="muted" style={{ marginTop:4 }}>Now: ${fp(current)}</span>}
              </div>
            </div>
            <button onClick={() => remove(i)} style={{
              marginTop:8, background:'none', border:'1px solid #2A2A2A',
              color:'#606060', borderRadius:8, padding:'4px 12px', cursor:'pointer', fontSize:12,
            }}>Remove</button>
          </div>
        )
      })}

      {adding ? (
        <div className="card">
          <div className="section-title">New Alert</div>
          <input placeholder="Symbol (BTC)" value={form.symbol}
            onChange={e => setForm(f=>({...f,symbol:e.target.value}))} style={{ marginTop:10 }} />
          <div style={{ display:'flex', gap:8, marginTop:8 }}>
            <select value={form.direction} onChange={e => setForm(f=>({...f,direction:e.target.value}))}
              style={{ background:'#242424', border:'1px solid #2A2A2A', borderRadius:10,
                padding:'12px 14px', color:'#fff', fontSize:14, flex:1 }}>
              <option value="above">▲ Above</option>
              <option value="below">▼ Below</option>
            </select>
            <input placeholder="Target $" type="number" value={form.target}
              onChange={e => setForm(f=>({...f,target:e.target.value}))}
              style={{ flex:2 }} />
          </div>
          <button className="btn" onClick={addAlert}>Set Alert</button>
          <button onClick={() => setAdding(false)} style={{
            background:'none', border:'none', color:'#A0A0A0',
            cursor:'pointer', width:'100%', marginTop:8, padding:8
          }}>Cancel</button>
        </div>
      ) : (
        <button className="btn" onClick={() => setAdding(true)}>+ New Alert</button>
      )}
    </div>
  )
}
```

---

### Task 10: App shell (main App.jsx)

**Files:**
- Create: `webapp/src/App.jsx`

- [ ] **Step 1: Create webapp/src/App.jsx**

```jsx
import { useState } from 'react'
import BottomNav from './components/BottomNav'
import Market from './tabs/Market'
import Signals from './tabs/Signals'
import Portfolio from './tabs/Portfolio'
import Research from './tabs/Research'
import Alerts from './tabs/Alerts'

export default function App() {
  const [tab, setTab] = useState('market')
  const [researchId, setResearchId] = useState(null)

  function goResearch(id) {
    setResearchId(id)
    setTab('research')
  }

  function handleTabChange(t) {
    if (t !== 'research') setResearchId(null)
    setTab(t)
  }

  return (
    <>
      {tab === 'market'    && <Market onResearch={goResearch} />}
      {tab === 'signals'   && <Signals />}
      {tab === 'portfolio' && <Portfolio />}
      {tab === 'research'  && <Research initialId={researchId} />}
      {tab === 'alerts'    && <Alerts />}
      <BottomNav active={tab} onSelect={handleTabChange} />
    </>
  )
}
```

- [ ] **Step 2: Build the app**

```bash
cd ~/crypto-signal-agent/webapp
npm run build
# Expected: dist/ with index.html + assets/
ls dist/
```

- [ ] **Step 3: Commit dist/**

```bash
cd ~/crypto-signal-agent
git add webapp/
git commit -m "feat: add Telegram Mini App React webapp"
```

---

### Task 11: Python static file server

**Files:**
- Create: `serve_webapp.py`
- Modify: `run_all.py`

- [ ] **Step 1: Create serve_webapp.py**

```python
"""Serve the webapp/dist/ static files on PORT (default 8080)."""
import asyncio
import logging
import os
from aiohttp import web

log = logging.getLogger(__name__)
PORT = int(os.getenv("PORT", 8080))
DIST = os.path.join(os.path.dirname(__file__), "webapp", "dist")


async def main():
    app = web.Application()
    app.router.add_static("/", DIST, show_index=True, follow_symlinks=True)

    # SPA fallback — serve index.html for any unknown path
    async def fallback(request):
        return web.FileResponse(os.path.join(DIST, "index.html"))
    app.router.add_route("GET", "/{path_info:.*}", fallback)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("WebApp serving on port %d from %s", PORT, DIST)
    await asyncio.Event().wait()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

- [ ] **Step 2: Update run_all.py to launch serve_webapp.py**

Open `run_all.py` and add `serve_webapp.py` to the processes list alongside the existing bots. The exact edit depends on the current content — add `"python serve_webapp.py"` as an additional subprocess using the same restart pattern already there.

- [ ] **Step 3: Verify locally**

```bash
cd ~/crypto-signal-agent
python serve_webapp.py &
curl -s http://localhost:8080/ | head -5
# Expected: <!doctype html>...
kill %1
```

---

### Task 12: Wire WebApp button into bot

**Files:**
- Modify: `main.py` (cmd_start, main_keyboard)

- [ ] **Step 1: Add WEBAPP_URL config to config.py**

```python
# In config.py, add:
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
```

- [ ] **Step 2: Update main_keyboard() to include Open App button**

In `main.py`, import `WebAppInfo` and add the launch button:

```python
from telegram import WebAppInfo

def main_keyboard() -> InlineKeyboardMarkup:
    import config as _cfg
    rows = [
        [("📈 Market", "market"),          ("🎯 Signals", "signals_menu")],
        [("📚 Learn Trading", "learn"),    ("💼 Portfolio", "portfolio")],
        [("📰 Research", "research"),      ("🧮 Tools", "tools_menu")],
        [("🔔 Alerts", "alerts"),          ("🤖 AI Coach", "coach_menu")],
        [("📊 Journal", "journal"),        ("🏆 Challenges", "challenges")],
        [("👤 Profile", "profile"),        ("⚙️ Settings", "settings")],
    ]
    buttons = []
    for row in rows:
        buttons.append([InlineKeyboardButton(t, callback_data=d) for t, d in row])
    if _cfg.WEBAPP_URL:
        buttons.insert(0, [InlineKeyboardButton(
            "🚀 Open Trading App",
            web_app=WebAppInfo(url=_cfg.WEBAPP_URL)
        )])
    return InlineKeyboardMarkup(buttons)
```

- [ ] **Step 3: Update /start to also show the WebApp button**

In `cmd_start`, add the same WebApp button to the reply markup when WEBAPP_URL is set.

- [ ] **Step 4: Set WEBAPP_URL in Railway**

In Railway dashboard → crypto-signal-bot service → Variables:
```
WEBAPP_URL = https://<your-railway-webapp-domain>
```

- [ ] **Step 5: Commit and deploy**

```bash
cd ~/crypto-signal-agent
git add main.py config.py run_all.py serve_webapp.py
git commit -m "feat: wire Telegram Mini App button into bot"
git push
railway up --detach
```

---

## Deployment Notes

Railway serves both the Telegram bot (polling) and the static webapp (HTTP) from the same dyno. The `Procfile` runs `run_all.py` which spawns both `python main.py` and `python serve_webapp.py`. Railway will assign the `PORT` env var automatically to the HTTP process.

The `WEBAPP_URL` must be an `https://` URL for Telegram to accept it as a WebApp. Railway provides a public HTTPS domain automatically.
