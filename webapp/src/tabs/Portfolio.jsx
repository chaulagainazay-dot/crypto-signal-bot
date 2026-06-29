import { useState, useEffect } from 'react'
import { fetchTopCoins, fp, fmcap } from '../api/coingecko'

const KEY = 'hcg_portfolio_v2'
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || [] } catch { return [] } }
const save = h => localStorage.setItem(KEY, JSON.stringify(h))

const EMPTY_FORM = { symbol: '', amount: '', buyPrice: '' }

export default function Portfolio() {
  const [holdings, setHoldings] = useState(load)
  const [prices,   setPrices]   = useState({})
  const [adding,   setAdding]   = useState(false)
  const [form,     setForm]     = useState(EMPTY_FORM)
  const [priceErr, setPriceErr] = useState('')

  useEffect(() => {
    fetchTopCoins(200).then(coins => {
      const m = {}
      coins.forEach(c => { m[c.symbol.toUpperCase()] = { price: c.current_price, image: c.image, name: c.name } })
      setPrices(m)
    }).catch(console.error)
  }, [])

  const totalValue = holdings.reduce((s, h) => s + (prices[h.symbol]?.price || 0) * h.amount, 0)
  const totalCost  = holdings.reduce((s, h) => s + h.buyPrice * h.amount, 0)
  const totalPnl   = totalValue - totalCost
  const pnlPct     = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0

  function add() {
    if (!form.symbol || !form.amount) return
    const sym = form.symbol.toUpperCase()
    if (!prices[sym]) { setPriceErr(`${sym} not found`); return }
    const h = { symbol: sym, amount: parseFloat(form.amount), buyPrice: parseFloat(form.buyPrice) || 0 }
    const updated = [...holdings, h]
    setHoldings(updated); save(updated)
    setForm(EMPTY_FORM); setAdding(false); setPriceErr('')
  }

  function remove(i) {
    const updated = holdings.filter((_, j) => j !== i)
    setHoldings(updated); save(updated)
  }

  const pnlColor = pnl => pnl >= 0 ? '#00C853' : '#FF3D57'

  return (
    <div className="tab-content">
      <h2>💼 Portfolio</h2>

      {/* Summary */}
      <div className="card" style={{ marginBottom: 16, background: 'linear-gradient(135deg, #1A1A1A, #242424)' }}>
        <div className="muted" style={{ marginBottom: 4 }}>Total Value</div>
        <div style={{ fontSize: 32, fontWeight: 900 }}>{fmcap(totalValue)}</div>
        {totalCost > 0 && (
          <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: pnlColor(totalPnl), fontWeight: 700 }}>
              {totalPnl >= 0 ? '+' : ''}{fmcap(totalPnl)}
            </span>
            <span className={`badge badge-${totalPnl >= 0 ? 'green' : 'red'}`}>
              {totalPnl >= 0 ? '▲' : '▼'} {Math.abs(pnlPct).toFixed(2)}%
            </span>
          </div>
        )}
        {totalCost > 0 && <div className="muted" style={{ marginTop: 4, fontSize: 11 }}>Cost basis: {fmcap(totalCost)}</div>}
      </div>

      {/* Holdings */}
      {holdings.length === 0 && !adding && (
        <div style={{ textAlign: 'center', color: '#606060', padding: '32px 0' }}>
          No holdings yet.<br />Add your first coin below.
        </div>
      )}

      {holdings.map((h, i) => {
        const info  = prices[h.symbol]
        const cur   = info?.price || 0
        const val   = cur * h.amount
        const cost  = h.buyPrice * h.amount
        const pnl   = val - cost
        const pct   = cost > 0 ? (pnl / cost) * 100 : 0
        return (
          <div key={i} className="card">
            <div className="row">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {info?.image && <img src={info.image} width={32} height={32} style={{ borderRadius: '50%' }} />}
                <div>
                  <strong>{h.symbol}</strong>
                  <div className="muted">{h.amount} coins</div>
                </div>
              </div>
              <div className="col" style={{ alignItems: 'flex-end' }}>
                <strong>{fmcap(val)}</strong>
                {cost > 0 && (
                  <span className={`badge badge-${pnl >= 0 ? 'green' : 'red'}`}>
                    {pnl >= 0 ? '+' : ''}{pct.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
            <div className="row" style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #242424' }}>
              <span className="muted">Current: ${fp(cur)}</span>
              {h.buyPrice > 0 && <span className="muted">Avg buy: ${fp(h.buyPrice)}</span>}
              <button onClick={() => remove(i)} style={{
                background: 'none', border: 'none', color: '#505050', cursor: 'pointer', fontSize: 16, padding: 0,
              }}>✕</button>
            </div>
          </div>
        )
      })}

      {/* Add form */}
      {adding ? (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>Add Holding</div>
          <input placeholder="Symbol (BTC, ETH…)" value={form.symbol}
            onChange={e => { setForm(f => ({ ...f, symbol: e.target.value })); setPriceErr('') }}
            style={{ marginTop: 10 }} />
          {priceErr && <div style={{ color: '#FF3D57', fontSize: 12, marginTop: 4 }}>{priceErr}</div>}
          <input placeholder="Amount (e.g. 0.5)" type="number" value={form.amount}
            onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} style={{ marginTop: 8 }} />
          <input placeholder="Avg buy price USD (optional)" type="number" value={form.buyPrice}
            onChange={e => setForm(f => ({ ...f, buyPrice: e.target.value }))} style={{ marginTop: 8 }} />
          <button className="btn" onClick={add}>Add</button>
          <button onClick={() => { setAdding(false); setPriceErr('') }} style={{
            background: 'none', border: 'none', color: '#A0A0A0',
            cursor: 'pointer', width: '100%', marginTop: 8, padding: 8, fontSize: 14,
          }}>Cancel</button>
        </div>
      ) : (
        <button className="btn" onClick={() => setAdding(true)}>＋ Add Holding</button>
      )}
    </div>
  )
}
