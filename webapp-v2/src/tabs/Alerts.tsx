import { useState, useEffect } from 'react'
import { fetchCoinDetail, fetchTopCoins, fetchCryptoNews, fp } from '../api/coingecko'
import { generateSignal } from '../utils/signals'
import { useStore } from '../store'
import { hapticNotify } from '../utils/telegram'
import type { NewsArticle, Coin } from '../types'

const SIG_COLOR = { 'STRONG BUY': '#00E676', 'BUY': '#00C853', 'HOLD': '#F7931A', 'SELL': '#FF3D57', 'STRONG SELL': '#FF1744' }

function HoldingSignalCard({ h }: { h: { coinId: string; symbol: string; name: string; image: string; amount: number; buyPrice: number } }) {
  const [detail, setDetail] = useState<Coin | null>(null)
  const [news, setNews] = useState<NewsArticle[]>([])
  const [newsOpen, setNewsOpen] = useState(false)
  const [newsLoading, setNewsLoading] = useState(false)

  useEffect(() => {
    fetchCoinDetail(h.coinId).then(d => {
      const md = (d as { market_data?: Record<string, unknown> })?.market_data as Record<string, unknown> | undefined
      if (md) {
        setDetail({
          id: h.coinId, symbol: h.symbol, name: h.name, image: h.image,
          current_price: (md.current_price as { usd?: number })?.usd ?? 0,
          market_cap: (md.market_cap as { usd?: number })?.usd ?? 0,
          market_cap_rank: (md.market_cap_rank as number) ?? 0,
          total_volume: (md.total_volume as { usd?: number })?.usd ?? 0,
          price_change_24h: (md.price_change_percentage_24h as number) ?? 0,
          price_change_percentage_24h: (md.price_change_percentage_24h as number) ?? 0,
          price_change_percentage_7d_in_currency: (md.price_change_percentage_7d_in_currency as { usd?: number })?.usd ?? 0,
          sparkline_in_7d: (md.sparkline_in_7d as { price: number[] }) ?? undefined,
          ath: (md.ath as { usd?: number })?.usd ?? 0,
          ath_change_percentage: (md.ath_change_percentage as { usd?: number })?.usd ?? 0,
          circulating_supply: (md.circulating_supply as number) ?? 0,
        })
      }
    }).catch(() => {})
  }, [h.coinId])

  async function loadNews() {
    if (news.length || newsLoading) return
    setNewsLoading(true)
    fetchCryptoNews(h.symbol, 4).then(setNews).catch(() => {}).finally(() => setNewsLoading(false))
  }

  const sig = detail ? generateSignal(detail) : null
  const price  = detail?.current_price ?? 0
  const chg24  = detail?.price_change_percentage_24h ?? 0
  const value  = price * h.amount
  const cost   = h.buyPrice * h.amount
  const pnl    = cost > 0 ? ((value - cost) / cost) * 100 : 0
  const sigColor = sig ? SIG_COLOR[sig.type] : '#2A2A2A'

  return (
    <div className="card" style={{ marginBottom: 10, borderLeft: `3px solid ${sigColor}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        {h.image && <img src={h.image} width={32} height={32} style={{ borderRadius: '50%' }} onError={e => ((e.target as HTMLImageElement).style.display = 'none')} />}
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 14 }}>{h.symbol.toUpperCase()}</strong>
          <div className="muted" style={{ fontSize: 11 }}>{h.name}</div>
        </div>
        {sig && (
          <span style={{ background: sigColor + '22', color: sigColor, padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>
            {sig.type}
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 10 }}>
        {[
          { label: 'Price', val: price > 0 ? `$${fp(price)}` : '—' },
          { label: 'Value', val: value > 0 ? `$${value < 1000 ? value.toFixed(2) : (value / 1000).toFixed(1) + 'K'}` : '—' },
          { label: 'PnL', val: cost > 0 ? `${pnl >= 0 ? '+' : ''}${pnl.toFixed(1)}%` : '—', col: pnl >= 0 ? '#00C853' : '#FF3D57' },
        ].map(({ label, val, col }) => (
          <div key={label} style={{ padding: '7px 10px', background: '#141414', borderRadius: 8 }}>
            <div className="muted" style={{ fontSize: 9, marginBottom: 2 }}>{label}</div>
            <div style={{ fontWeight: 700, fontSize: 12, color: col || '#E0E0E0' }}>{val}</div>
          </div>
        ))}
      </div>

      {sig && sig.score >= 55 && (
        <div style={{ padding: '8px 12px', borderRadius: 8, marginBottom: 10, background: '#00C85315', border: '1px solid #00C85340' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#00C853' }}>📈 Strong momentum — consider adding more</div>
          <div style={{ marginTop: 4, height: 3, background: '#2A2A2A', borderRadius: 2 }}>
            <div style={{ width: `${sig.score}%`, height: '100%', background: sigColor, borderRadius: 2 }} />
          </div>
        </div>
      )}
      {sig && sig.score <= 35 && (
        <div style={{ padding: '8px 12px', borderRadius: 8, marginBottom: 10, background: '#FF3D5715', border: '1px solid #FF3D5740' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#FF3D57' }}>📉 Weakening signal — consider reducing position</div>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className={`badge badge-${chg24 >= 0 ? 'green' : 'red'}`} style={{ fontSize: 10 }}>
          {chg24 >= 0 ? '▲' : '▼'}{Math.abs(chg24).toFixed(2)}% 24h
        </div>
        <button onClick={() => { setNewsOpen(o => !o); if (!newsOpen) loadNews() }}
          style={{ background: 'none', border: '1px solid #2A2A2A', borderRadius: 8, color: '#808080', cursor: 'pointer', fontSize: 11, padding: '5px 10px' }}>
          {newsOpen ? '▲ Hide News' : `📰 News`}
        </button>
      </div>

      {newsOpen && (
        <div style={{ marginTop: 10 }}>
          {newsLoading && <div className="muted" style={{ fontSize: 12, padding: '8px 0' }}>Loading…</div>}
          {!newsLoading && news.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No news found.</div>}
          {news.map((art, i) => (
            <a key={i} href={art.url} target="_blank" rel="noreferrer"
              style={{ display: 'block', textDecoration: 'none', padding: '8px 0', borderBottom: '1px solid #1E1E1E' }}>
              <div style={{ fontSize: 12, color: '#D0D0D0', lineHeight: 1.5 }}>{art.title}</div>
              <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>{art.source_info?.name || art.source} ↗</div>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Alerts() {
  const { alerts, addAlert, removeAlert, triggerAlert, holdings } = useStore()
  const [section, setSection] = useState<'portfolio' | 'price'>('portfolio')
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ symbol: '', target: '', dir: 'above' as 'above' | 'below' })
  const [err, setErr] = useState('')

  useEffect(() => {
    if (alerts.length === 0) return
    fetchTopCoins(250).then(coins => {
      const m: Record<string, number> = {}
      ;(coins as Coin[]).forEach(c => { m[c.symbol.toUpperCase()] = c.current_price })
      setPrices(m)
      alerts.forEach(a => {
        const p = m[a.symbol.toUpperCase()]
        if (p && a.active && ((a.direction === 'above' && p >= a.target) || (a.direction === 'below' && p <= a.target))) {
          triggerAlert(a.id)
          hapticNotify('warning')
        }
      })
    }).catch(() => {})
  }, [alerts.length])

  function addNewAlert() {
    const sym = form.symbol.trim().toUpperCase()
    const target = parseFloat(form.target)
    if (!sym || isNaN(target) || target <= 0) { setErr('Enter valid symbol and price'); return }
    addAlert({ id: `${sym}_${Date.now()}`, symbol: sym, target, direction: form.dir, created: Date.now(), active: true })
    setForm({ symbol: '', target: '', dir: 'above' }); setAdding(false); setErr('')
  }

  const triggered = alerts.filter(a => !a.active).length

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 14 }}>
        <h2 style={{ margin: 0 }}>🔔 Alerts</h2>
        {triggered > 0 && <span className="badge badge-orange">{triggered} triggered</span>}
      </div>

      <div className="pills">
        <button className={`pill${section === 'portfolio' ? ' active' : ''}`} onClick={() => setSection('portfolio')}>
          💼 Portfolio Signals
        </button>
        <button className={`pill${section === 'price' ? ' active' : ''}`} onClick={() => setSection('price')}>
          🔔 Price Alerts
        </button>
      </div>

      {section === 'portfolio' && (
        <>
          {holdings.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#505050', padding: '40px 0', lineHeight: 2 }}>
              No holdings yet.<br />Add coins in 💼 Portfolio to see signals here.
            </div>
          ) : (
            <>
              <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>Live buy/sell signals + news for each holding</div>
              {holdings.map((h, i) => <HoldingSignalCard key={`${h.coinId}-${i}`} h={h} />)}
            </>
          )}
        </>
      )}

      {section === 'price' && (
        <>
          {alerts.length === 0 && !adding && (
            <div style={{ textAlign: 'center', color: '#505050', padding: '32px 0' }}>No price alerts set.</div>
          )}
          {alerts.map(a => {
            const p = prices[a.symbol.toUpperCase()]
            const hit = p ? (a.direction === 'above' ? p >= a.target : p <= a.target) : false
            const dist = p ? Math.abs(((p - a.target) / a.target) * 100).toFixed(1) : null
            return (
              <div key={a.id} className="card" style={{ marginBottom: 8, borderLeft: `3px solid ${hit || !a.active ? '#F7931A' : '#2A2A2A'}` }}>
                <div className="row">
                  <div>
                    <strong style={{ fontSize: 13 }}>{a.symbol}</strong>
                    <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>Alert when {a.direction} ${fp(a.target)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    {!a.active ? <span className="badge badge-orange">🔔 Triggered</span>
                      : p ? <span className="muted" style={{ fontSize: 12 }}>${fp(p)} now</span> : null}
                    {dist && a.active && <div className="muted" style={{ fontSize: 10, marginTop: 2 }}>{dist}% away</div>}
                  </div>
                </div>
                <div style={{ textAlign: 'right', marginTop: 8 }}>
                  <button onClick={() => removeAlert(a.id)} style={{ background: 'none', border: 'none', color: '#404040', cursor: 'pointer', fontSize: 12 }}>Remove</button>
                </div>
              </div>
            )
          })}

          {adding ? (
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>New Price Alert</div>
              <input placeholder="Symbol (BTC, ETH, SOL…)" value={form.symbol} onChange={e => { setForm(f => ({ ...f, symbol: e.target.value })); setErr('') }} style={{ marginTop: 10 }} />
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <select value={form.dir} onChange={e => setForm(f => ({ ...f, dir: e.target.value as 'above' | 'below' }))
                } style={{ flex: 1 }}>
                  <option value="above">Goes above</option>
                  <option value="below">Goes below</option>
                </select>
                <input type="number" placeholder="Price USD" value={form.target} onChange={e => { setForm(f => ({ ...f, target: e.target.value })); setErr('') }} style={{ flex: 2 }} />
              </div>
              {err && <div style={{ color: '#FF3D57', fontSize: 12, marginTop: 4 }}>{err}</div>}
              <button className="btn" onClick={addNewAlert}>Set Alert</button>
              <button onClick={() => setAdding(false)} style={{ background: 'none', border: 'none', color: '#808080', cursor: 'pointer', width: '100%', marginTop: 8, padding: 8, fontSize: 13 }}>Cancel</button>
            </div>
          ) : (
            <button className="btn" onClick={() => setAdding(true)}>＋ Add Price Alert</button>
          )}
        </>
      )}
    </div>
  )
}
