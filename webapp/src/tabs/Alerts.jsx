import { useState, useEffect, useCallback } from 'react'
import { fetchCoinDetail, fetchCryptoNews, fp, fmcap } from '../api/coingecko'

// ── Storage keys ─────────────────────────────────────────────────────────────
const ALERT_KEY = 'hcg_alerts_v2'
const PORT_KEY  = 'hcg_portfolio_v3'

const loadAlerts    = () => { try { return JSON.parse(localStorage.getItem(ALERT_KEY)) || [] } catch { return [] } }
const saveAlerts    = a => localStorage.setItem(ALERT_KEY, JSON.stringify(a))
const loadPortfolio = () => { try { return JSON.parse(localStorage.getItem(PORT_KEY))  || [] } catch { return [] } }

// ── Signal from price data ────────────────────────────────────────────────────
function calcSignal(md) {
  if (!md) return null
  const chg24 = md.price_change_percentage_24h || 0
  const chg7d  = md.price_change_percentage_7d_in_currency?.usd || 0
  const vol    = md.total_volume?.usd   || 0
  const mcap   = md.market_cap?.usd     || 1
  const vr     = vol / mcap

  let score = 50
  if (chg24 > 10) score += 20; else if (chg24 > 4) score += 10
  else if (chg24 < -10) score -= 20; else if (chg24 < -4) score -= 10
  if (chg7d > 15) score += 12; else if (chg7d > 5) score += 6
  else if (chg7d < -15) score -= 12; else if (chg7d < -5) score -= 6
  if (vr > 0.3) score += 12; else if (vr > 0.1) score += 6; else if (vr < 0.02) score -= 5
  score = Math.max(0, Math.min(100, score))

  if (score >= 68) return { label: 'STRONG BUY',  color: '#00E676', icon: '🚀', score }
  if (score >= 55) return { label: 'BUY',          color: '#00C853', icon: '📈', score }
  if (score >= 45) return { label: 'HOLD',         color: '#F7931A', icon: '➡️', score }
  if (score >= 32) return { label: 'SELL',         color: '#FF3D57', icon: '📉', score }
  return              { label: 'STRONG SELL',  color: '#FF1744', icon: '🔥', score }
}

// ── News sentiment badge ───────────────────────────────────────────────────────
function sentiment(title = '') {
  const t = title.toLowerCase()
  const pos = ['surge','rally','bullish','pump','breakout','gain','high','rise','soar','ath','launch','partnership','adoption']
  const neg = ['crash','drop','bear','dump','ban','hack','fraud','scam','fall','plunge','fear','warning','low','down','sell']
  const p = pos.filter(w => t.includes(w)).length
  const n = neg.filter(w => t.includes(w)).length
  if (p > n) return { label: '🟢 Bullish', color: '#00C853' }
  if (n > p) return { label: '🔴 Bearish', color: '#FF3D57' }
  return             { label: '⚪ Neutral', color: '#808080' }
}

// ── Holding card with signal + news ──────────────────────────────────────────
function HoldingAlert({ holding }) {
  const [detail, setDetail] = useState(null)
  const [news,   setNews]   = useState([])
  const [open,   setOpen]   = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchCoinDetail(holding.coinId).then(d => setDetail(d)).catch(() => {})
  }, [holding.coinId])

  async function loadNews() {
    if (news.length || loading) return
    setLoading(true)
    const articles = await fetchCryptoNews(holding.symbol, 4)
    setNews(articles)
    setLoading(false)
  }

  const md     = detail?.market_data
  const price  = md?.current_price?.usd || 0
  const chg24  = md?.price_change_percentage_24h || 0
  const sig    = calcSignal(md)
  const cost   = holding.buyPrice * holding.amount
  const value  = price * holding.amount
  const pnl    = value - cost
  const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0

  // Alert: trigger if buy signal when holding, or sell signal when holding at loss
  const alertType = sig?.score >= 55 ? 'buy_more'
                  : sig?.score <= 32 ? 'sell'
                  : null

  return (
    <div className="card" style={{ marginBottom: 10, borderLeft: `3px solid ${sig?.color || '#2A2A2A'}` }}>
      {/* Header row */}
      <div className="row" style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {holding.image && (
            <img src={holding.image} width={32} height={32}
              style={{ borderRadius: '50%' }} onError={e => e.target.style.display='none'} />
          )}
          <div>
            <strong style={{ fontSize: 14 }}>{holding.symbol}</strong>
            <div className="muted" style={{ fontSize: 11 }}>{holding.name}</div>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          {sig && (
            <span style={{ background: sig.color + '22', color: sig.color,
              padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>
              {sig.icon} {sig.label}
            </span>
          )}
          <div className={`badge badge-${chg24 >= 0 ? 'green' : 'red'}`} style={{ marginTop: 4, display: 'block' }}>
            {chg24 >= 0 ? '▲' : '▼'} {Math.abs(chg24).toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Price + PnL row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 10 }}>
        {[
          { label: 'Price',    val: price > 0 ? `$${fp(price)}` : '—' },
          { label: 'Value',    val: value > 0 ? fmcap(value) : '—' },
          { label: 'PnL',      val: cost > 0 ? `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%` : '—',
            col: pnlPct >= 0 ? '#00C853' : '#FF3D57' },
        ].map(({ label, val, col }) => (
          <div key={label} style={{ padding: '7px 10px', background: '#141414', borderRadius: 8 }}>
            <div className="muted" style={{ fontSize: 9, marginBottom: 2 }}>{label}</div>
            <div style={{ fontWeight: 700, fontSize: 13, color: col || '#E0E0E0' }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Alert recommendation */}
      {alertType && (
        <div style={{ padding: '8px 12px', borderRadius: 8, marginBottom: 10,
          background: alertType === 'buy_more' ? '#00C85315' : '#FF3D5715',
          border: `1px solid ${alertType === 'buy_more' ? '#00C85340' : '#FF3D5740'}` }}>
          <div style={{ fontSize: 12, fontWeight: 700,
            color: alertType === 'buy_more' ? '#00C853' : '#FF3D57' }}>
            {alertType === 'buy_more'
              ? '📈 Signal: Consider adding more — strong upward momentum'
              : '📉 Signal: Consider taking profit or reducing position'}
          </div>
          {sig && (
            <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{ flex: 1, height: 3, background: '#2A2A2A', borderRadius: 2 }}>
                <div style={{ width: `${sig.score}%`, height: '100%', background: sig.color, borderRadius: 2 }} />
              </div>
              <span className="muted" style={{ fontSize: 10 }}>{sig.score}/100</span>
            </div>
          )}
        </div>
      )}

      {/* News toggle */}
      <button onClick={() => { setOpen(o => !o); if (!open) loadNews() }}
        style={{ background: 'none', border: '1px solid #2A2A2A', borderRadius: 8,
          color: '#A0A0A0', cursor: 'pointer', fontSize: 12, padding: '6px 12px',
          width: '100%', textAlign: 'center' }}>
        {open ? '▲ Hide News' : `📰 Latest News for ${holding.symbol}`}
      </button>

      {open && (
        <div style={{ marginTop: 8 }}>
          {loading && <div className="muted" style={{ fontSize: 12, padding: '8px 0' }}>Loading news…</div>}
          {!loading && news.length === 0 && (
            <div className="muted" style={{ fontSize: 12, padding: '8px 0' }}>No news found.</div>
          )}
          {news.map((art, i) => {
            const s = sentiment(art.title)
            return (
              <a key={i} href={art.url} target="_blank" rel="noreferrer"
                style={{ display: 'block', padding: '8px 0', borderBottom: '1px solid #1E1E1E',
                  textDecoration: 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                  <span style={{ fontSize: 10, color: s.color, fontWeight: 700 }}>{s.label}</span>
                  <span className="muted" style={{ fontSize: 10 }}>
                    {new Date(art.published_on * 1000).toLocaleDateString()}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: '#D0D0D0', lineHeight: 1.5 }}>{art.title}</div>
                <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>
                  {art.source_info?.name || art.source} ↗
                </div>
              </a>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Manual price alert card ───────────────────────────────────────────────────
function PriceAlertCard({ alert, livePrice, onRemove }) {
  const cur = livePrice || null
  const hit = cur ? (alert.dir === 'above' ? cur >= alert.target : cur <= alert.target) : false
  const dist = cur ? Math.abs(((cur - alert.target) / alert.target) * 100).toFixed(2) : null

  return (
    <div className="card" style={{ marginBottom: 8, borderLeft: `3px solid ${hit ? '#F7931A' : '#2A2A2A'}` }}>
      <div className="row">
        <div>
          <strong style={{ fontSize: 13 }}>{alert.symbol}</strong>
          <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
            Alert when {alert.dir} ${fp(alert.target)}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          {hit
            ? <span className="badge badge-orange">🔔 Triggered!</span>
            : cur && <span className="muted" style={{ fontSize: 12 }}>${fp(cur)} now</span>
          }
          {dist && !hit && (
            <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>{dist}% away</div>
          )}
        </div>
      </div>
      <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
        <button onClick={onRemove}
          style={{ background: 'none', border: 'none', color: '#505050', cursor: 'pointer', fontSize: 12 }}>
          Remove
        </button>
      </div>
    </div>
  )
}

// ── Main Alerts tab ───────────────────────────────────────────────────────────
export default function Alerts() {
  const [section,  setSection]  = useState('portfolio') // portfolio | manual
  const [alerts,   setAlerts]   = useState(loadAlerts)
  const [holdings, setHoldings] = useState(loadPortfolio)
  const [prices,   setPrices]   = useState({})
  const [adding,   setAdding]   = useState(false)
  const [form,     setForm]     = useState({ symbol: '', target: '', dir: 'above' })
  const [err,      setErr]      = useState('')

  // Refresh portfolio from localStorage whenever tab is focused
  useEffect(() => {
    setHoldings(loadPortfolio())
  }, [section])

  // Fetch prices for manual alerts
  useEffect(() => {
    if (alerts.length === 0) return
    const syms = [...new Set(alerts.map(a => a.symbol))]
    import('../api/coingecko').then(({ fetchTopCoins }) => {
      fetchTopCoins(250).then(coins => {
        const m = {}
        coins.forEach(c => { m[c.symbol.toUpperCase()] = c.current_price })
        setPrices(m)
      }).catch(() => {})
    })
  }, [alerts.length])

  function addAlert() {
    const sym    = form.symbol.trim().toUpperCase()
    const target = parseFloat(form.target)
    if (!sym || isNaN(target) || target <= 0) { setErr('Enter a valid symbol and price.'); return }
    const updated = [...alerts, { symbol: sym, target, dir: form.dir, createdAt: Date.now() }]
    setAlerts(updated); saveAlerts(updated)
    setForm({ symbol: '', target: '', dir: 'above' }); setAdding(false); setErr('')
  }

  const triggered = alerts.filter(a => {
    const p = prices[a.symbol]
    return p && (a.dir === 'above' ? p >= a.target : p <= a.target)
  }).length

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 14 }}>
        <h2 style={{ margin: 0 }}>🔔 Alerts</h2>
        {triggered > 0 && (
          <span className="badge badge-orange">{triggered} triggered</span>
        )}
      </div>

      <div className="pills">
        <button className={`pill${section === 'portfolio' ? ' active' : ''}`}
          onClick={() => setSection('portfolio')}>
          💼 Portfolio Signals
        </button>
        <button className={`pill${section === 'manual' ? ' active' : ''}`}
          onClick={() => setSection('manual')}>
          🔔 Price Alerts
        </button>
      </div>

      {/* ── Portfolio Signals ── */}
      {section === 'portfolio' && (
        <>
          {holdings.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#606060', padding: '40px 0', lineHeight: 2 }}>
              No holdings in your portfolio yet.<br />
              Add coins in the 💼 Portfolio tab<br />to see buy/sell signals and news here.
            </div>
          ) : (
            <>
              <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
                Live buy/sell signals + latest news for each coin you hold.
              </div>
              {holdings.map((h, i) => <HoldingAlert key={`${h.coinId}-${i}`} holding={h} />)}
            </>
          )}
        </>
      )}

      {/* ── Manual Price Alerts ── */}
      {section === 'manual' && (
        <>
          {alerts.length === 0 && !adding && (
            <div style={{ textAlign: 'center', color: '#606060', padding: '32px 0' }}>
              No price alerts set yet.
            </div>
          )}

          {alerts.map((a, i) => (
            <PriceAlertCard key={i} alert={a} livePrice={prices[a.symbol]}
              onRemove={() => { const u = alerts.filter((_,j)=>j!==i); setAlerts(u); saveAlerts(u) }} />
          ))}

          {adding ? (
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>New Price Alert</div>
              <input placeholder="Symbol (BTC, ETH, SOL…)" value={form.symbol}
                onChange={e => { setForm(f => ({ ...f, symbol: e.target.value })); setErr('') }}
                style={{ marginTop: 10 }} />
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <select value={form.dir} onChange={e => setForm(f => ({ ...f, dir: e.target.value }))}
                  style={{ flex: 1, background: '#1A1A1A', border: '1px solid #2A2A2A',
                    borderRadius: 10, color: '#E0E0E0', padding: '12px', fontSize: 14 }}>
                  <option value="above">Goes above</option>
                  <option value="below">Goes below</option>
                </select>
                <input placeholder="Price USD" type="number" value={form.target}
                  onChange={e => setForm(f => ({ ...f, target: e.target.value }))}
                  style={{ flex: 2 }} />
              </div>
              {err && <div style={{ color: '#FF3D57', fontSize: 12, marginTop: 4 }}>{err}</div>}
              <button className="btn" onClick={addAlert}>Set Alert</button>
              <button onClick={() => { setAdding(false); setErr('') }}
                style={{ background: 'none', border: 'none', color: '#A0A0A0',
                  cursor: 'pointer', width: '100%', marginTop: 8, padding: 8, fontSize: 14 }}>
                Cancel
              </button>
            </div>
          ) : (
            <button className="btn" onClick={() => setAdding(true)}>＋ Add Price Alert</button>
          )}

          <p className="muted" style={{ textAlign: 'center', fontSize: 11, marginTop: 16 }}>
            Alerts are checked live when you open this tab.
          </p>
        </>
      )}
    </div>
  )
}
