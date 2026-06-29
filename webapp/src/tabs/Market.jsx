import { useState, useEffect, useCallback } from 'react'
import { fetchGlobal, fetchTopCoins, fetchTrending, fmcap, fp } from '../api/coingecko'
import CoinCard from '../components/CoinCard'
import Spinner from '../components/Spinner'

const VIEWS = ['Top', 'Gainers', 'Losers', 'Volume', 'Trending']

export default function Market({ onResearch }) {
  const [view, setView]       = useState('Top')
  const [global, setGlobal]   = useState(null)
  const [coins, setCoins]     = useState([])
  const [trending, setTrend]  = useState([])
  const [loading, setLoading] = useState(true)
  const [lastUp, setLastUp]   = useState(null)

  const [error, setError] = useState('')
  const load = useCallback(() => {
    setLoading(true); setError('')
    Promise.all([fetchGlobal(), fetchTopCoins(100), fetchTrending()])
      .then(([g, c, t]) => { setGlobal(g); setCoins(c); setTrend(t); setLastUp(new Date()) })
      .catch(e => setError('CoinGecko rate-limited. Tap Refresh to retry.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const displayed = () => {
    const sorted = [...coins]
    if (view === 'Gainers') return sorted.sort((a, b) => (b.price_change_percentage_24h || 0) - (a.price_change_percentage_24h || 0)).slice(0, 25)
    if (view === 'Losers')  return sorted.sort((a, b) => (a.price_change_percentage_24h || 0) - (b.price_change_percentage_24h || 0)).slice(0, 25)
    if (view === 'Volume')  return sorted.sort((a, b) => (b.total_volume || 0) - (a.total_volume || 0)).slice(0, 25)
    return coins.slice(0, 25)
  }

  const fgColor = g => {
    if (!g) return '#A0A0A0'
    return g.change >= 0 ? '#00C853' : '#FF3D57'
  }

  return (
    <div className="tab-content">
      {/* Header */}
      <div className="row" style={{ marginBottom: 14 }}>
        <h2 style={{ margin: 0 }}>📈 Market</h2>
        <button onClick={load} style={{
          background: '#1A1A1A', border: '1px solid #2A2A2A',
          color: '#A0A0A0', borderRadius: 8, padding: '5px 12px',
          cursor: 'pointer', fontSize: 12,
        }}>↻ Refresh</button>
      </div>

      {/* Global stats banner */}
      {global && (
        <div className="card" style={{ marginBottom: 14, padding: '12px 16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div className="col">
              <span className="muted">Mkt Cap</span>
              <strong style={{ fontSize: 13 }}>{fmcap(global.mcap)}</strong>
              <span style={{ fontSize: 11, color: fgColor(global), fontWeight: 600 }}>
                {global.change >= 0 ? '▲' : '▼'} {Math.abs(global.change).toFixed(1)}%
              </span>
            </div>
            <div className="col" style={{ alignItems: 'center' }}>
              <span className="muted">24h Vol</span>
              <strong style={{ fontSize: 13 }}>{fmcap(global.vol)}</strong>
            </div>
            <div className="col" style={{ alignItems: 'flex-end' }}>
              <span className="muted">BTC Dom</span>
              <strong style={{ fontSize: 13 }}>{global.btcDom.toFixed(1)}%</strong>
              <span className="muted" style={{ fontSize: 10 }}>ETH {global.ethDom.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      )}

      {/* View pills */}
      <div className="pills">
        {VIEWS.map(v => (
          <button key={v} className={`pill${view === v ? ' active' : ''}`} onClick={() => setView(v)}>{v}</button>
        ))}
      </div>

      {loading && <Spinner text="Loading market data…" />}
      {!loading && error && (
        <div style={{ textAlign: 'center', padding: '32px 16px', color: '#FF3D57' }}>
          ⚠️ {error}
        </div>
      )}

      {/* Trending */}
      {!loading && view === 'Trending' && trending.map((c, i) => (
        <div key={c.id} className="card" onClick={() => onResearch?.(c.id)}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: '#404040', fontSize: 13, width: 22 }}>#{i + 1}</span>
          {c.small && <img src={c.small} width={32} height={32} style={{ borderRadius: '50%' }} />}
          <div style={{ flex: 1 }}>
            <strong>{c.symbol?.toUpperCase()}</strong>
            <div className="muted">{c.name}</div>
          </div>
          <span className="badge badge-orange">🔥 Hot</span>
        </div>
      ))}

      {/* Coin list */}
      {!loading && view !== 'Trending' && displayed().map((c, i) => (
        <CoinCard key={c.id} coin={c} rank={view === 'Top' ? i + 1 : null}
          onClick={() => onResearch?.(c.id)} />
      ))}

      {lastUp && (
        <p className="muted" style={{ textAlign: 'center', marginTop: 8, fontSize: 11 }}>
          Updated {lastUp.toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
