import { useState, useEffect } from 'react'
import { fetchTopCoins, fp } from '../api/coingecko'

const KEY = 'hcg_alerts_v2'
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || [] } catch { return [] } }
const save = a => localStorage.setItem(KEY, JSON.stringify(a))

const EMPTY = { symbol: '', target: '', dir: 'above' }

export default function Alerts() {
  const [alerts,  setAlerts]  = useState(load)
  const [prices,  setPrices]  = useState({})
  const [adding,  setAdding]  = useState(false)
  const [form,    setForm]    = useState(EMPTY)
  const [err,     setErr]     = useState('')

  useEffect(() => {
    fetchTopCoins(200).then(coins => {
      const m = {}
      coins.forEach(c => { m[c.symbol.toUpperCase()] = c.current_price })
      setPrices(m)
    }).catch(console.error)
  }, [])

  function add() {
    if (!form.symbol || !form.target) return
    const sym = form.symbol.toUpperCase()
    const target = parseFloat(form.target)
    if (isNaN(target) || target <= 0) { setErr('Enter a valid price.'); return }
    const updated = [...alerts, { symbol: sym, target, dir: form.dir, createdAt: Date.now() }]
    setAlerts(updated); save(updated)
    setForm(EMPTY); setAdding(false); setErr('')
  }

  function remove(i) {
    const updated = alerts.filter((_, j) => j !== i)
    setAlerts(updated); save(updated)
  }

  const currentPrice = sym => prices[sym] || null
  const triggered = a => {
    const p = currentPrice(a.symbol)
    if (!p) return false
    return a.dir === 'above' ? p >= a.target : p <= a.target
  }

  return (
    <div className="tab-content">
      <h2>🔔 Price Alerts</h2>

      {alerts.length === 0 && !adding && (
        <div style={{ textAlign: 'center', color: '#606060', padding: '32px 0' }}>
          No alerts set.<br />Add one below.
        </div>
      )}

      {alerts.map((a, i) => {
        const cur = currentPrice(a.symbol)
        const hit = triggered(a)
        return (
          <div key={i} className="card" style={{ borderLeft: `3px solid ${hit ? '#F7931A' : '#2A2A2A'}` }}>
            <div className="row">
              <div>
                <strong>{a.symbol}</strong>
                <div className="muted" style={{ marginTop: 3 }}>
                  Alert when price goes {a.dir} ${fp(a.target)}
                </div>
              </div>
              <div className="col" style={{ alignItems: 'flex-end' }}>
                {hit && <span className="badge badge-orange">🔔 Triggered</span>}
                {!hit && cur && (
                  <span className="muted">${fp(cur)} now</span>
                )}
              </div>
            </div>
            {cur && (
              <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid #242424', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 12, color: '#606060' }}>
                  Distance: {Math.abs(((cur - a.target) / a.target) * 100).toFixed(2)}% away
                </div>
                <button onClick={() => remove(i)} style={{
                  background: 'none', border: 'none', color: '#505050',
                  cursor: 'pointer', fontSize: 13, padding: 0,
                }}>Remove</button>
              </div>
            )}
          </div>
        )
      })}

      {adding ? (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>New Alert</div>
          <input placeholder="Symbol (BTC, ETH…)" value={form.symbol}
            onChange={e => { setForm(f => ({ ...f, symbol: e.target.value })); setErr('') }}
            style={{ marginTop: 10 }} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <select value={form.dir} onChange={e => setForm(f => ({ ...f, dir: e.target.value }))}
              style={{
                flex: 1, background: '#1A1A1A', border: '1px solid #2A2A2A', borderRadius: 10,
                color: '#E0E0E0', padding: '12px', fontSize: 14,
              }}>
              <option value="above">Goes above</option>
              <option value="below">Goes below</option>
            </select>
            <input placeholder="Price USD" type="number" value={form.target}
              onChange={e => setForm(f => ({ ...f, target: e.target.value }))}
              style={{ flex: 2 }} />
          </div>
          {err && <div style={{ color: '#FF3D57', fontSize: 12, marginTop: 4 }}>{err}</div>}
          <button className="btn" onClick={add}>Set Alert</button>
          <button onClick={() => { setAdding(false); setErr('') }} style={{
            background: 'none', border: 'none', color: '#A0A0A0',
            cursor: 'pointer', width: '100%', marginTop: 8, padding: 8, fontSize: 14,
          }}>Cancel</button>
        </div>
      ) : (
        <button className="btn" onClick={() => setAdding(true)}>＋ Add Alert</button>
      )}

      <p className="muted" style={{ textAlign: 'center', fontSize: 11, marginTop: 16 }}>
        Alerts are checked when you open this tab. Enable notifications in your phone settings for real-time alerts.
      </p>
    </div>
  )
}
