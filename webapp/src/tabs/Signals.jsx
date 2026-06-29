import { useState, useEffect } from 'react'
import { fetchTopCoins, fp, fmcap } from '../api/coingecko'
import Spinner from '../components/Spinner'

function getSignal(coin) {
  const chg  = coin.price_change_percentage_24h || 0
  const vol  = coin.total_volume || 0
  const mcap = coin.market_cap || 1
  const vr   = vol / mcap

  if (chg > 10 && vr > 0.2)  return { type: 'STRONG BUY',  color: '#00E676', score: 5, icon: '🚀' }
  if (chg > 4  && vr > 0.08) return { type: 'BUY',         color: '#00C853', score: 4, icon: '📈' }
  if (chg < -10 && vr > 0.2) return { type: 'STRONG SELL', color: '#FF1744', score: 1, icon: '🔥' }
  if (chg < -4 && vr > 0.08) return { type: 'SELL',        color: '#FF3D57', score: 2, icon: '📉' }
  return { type: 'NEUTRAL', color: '#808080', score: 3, icon: '➡️' }
}

const FILTERS = ['All', 'Buy', 'Sell', 'Neutral']

export default function Signals() {
  const [coins,   setCoins]   = useState([])
  const [loading, setLoading] = useState(true)
  const [filter,  setFilter]  = useState('All')

  useEffect(() => {
    fetchTopCoins(100).then(setCoins).catch(console.error).finally(() => setLoading(false))
  }, [])

  const withSig = coins.map(c => ({ ...c, sig: getSignal(c) }))
  const shown = withSig.filter(c => {
    if (filter === 'Buy')     return c.sig.score >= 4
    if (filter === 'Sell')    return c.sig.score <= 2
    if (filter === 'Neutral') return c.sig.score === 3
    return true
  }).slice(0, 40)

  const buys  = withSig.filter(c => c.sig.score >= 4).length
  const sells = withSig.filter(c => c.sig.score <= 2).length

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 14 }}>
        <h2 style={{ margin: 0 }}>🎯 Signals</h2>
        <span className="muted" style={{ fontSize: 11 }}>Top 100 coins</span>
      </div>

      {/* Summary row */}
      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
          <div className="card" style={{ padding: '10px 12px', textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#00C853' }}>{buys}</div>
            <div className="muted" style={{ fontSize: 11 }}>Buy</div>
          </div>
          <div className="card" style={{ padding: '10px 12px', textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#A0A0A0' }}>{100 - buys - sells}</div>
            <div className="muted" style={{ fontSize: 11 }}>Neutral</div>
          </div>
          <div className="card" style={{ padding: '10px 12px', textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#FF3D57' }}>{sells}</div>
            <div className="muted" style={{ fontSize: 11 }}>Sell</div>
          </div>
        </div>
      )}

      <div className="pills">
        {FILTERS.map(f => (
          <button key={f} className={`pill${filter === f ? ' active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
        ))}
      </div>

      {loading && <Spinner text="Analysing signals…" />}

      {!loading && shown.map(c => (
        <div key={c.id} className="card">
          <div className="row">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {c.image && <img src={c.image} width={32} height={32} style={{ borderRadius: '50%' }} />}
              <div>
                <strong>{c.symbol?.toUpperCase()}</strong>
                <div className="muted">${fp(c.current_price)}</div>
              </div>
            </div>
            <div className="col" style={{ alignItems: 'flex-end' }}>
              <span style={{
                background: c.sig.color + '22', color: c.sig.color,
                padding: '3px 10px', borderRadius: 8, fontSize: 11, fontWeight: 800,
              }}>
                {c.sig.icon} {c.sig.type}
              </span>
              <span className={`badge badge-${(c.price_change_percentage_24h || 0) >= 0 ? 'green' : 'red'}`} style={{ marginTop: 4 }}>
                {(c.price_change_percentage_24h || 0) >= 0 ? '▲' : '▼'} {Math.abs(c.price_change_percentage_24h || 0).toFixed(2)}%
              </span>
            </div>
          </div>
          <div className="row" style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid #242424' }}>
            <span className="muted">Vol / MCap</span>
            <span style={{ fontSize: 12, color: '#A0A0A0' }}>
              {((c.total_volume / c.market_cap) * 100).toFixed(2)}%
            </span>
            <span className="muted">{fmcap(c.market_cap)} mcap</span>
          </div>
        </div>
      ))}

      {!loading && shown.length === 0 && (
        <div style={{ textAlign: 'center', color: '#606060', padding: '40px 0' }}>
          No {filter.toLowerCase()} signals right now.
        </div>
      )}
    </div>
  )
}
