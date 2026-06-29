import { useState, useEffect, useMemo } from 'react'
import { fetchTopCoins, fetchTrending } from '../api/coingecko'
import { generateSignal } from '../utils/signals'
import { fp } from '../api/coingecko'
import Spinner from '../components/Spinner'
import { SkeletonCard } from '../components/Skeleton'
import type { Signal, Coin, TrendingCoin } from '../types'

type Filter = 'all' | 'buy' | 'sell' | 'trending' | 'small'

const FILTER_LABELS: Record<Filter, string> = {
  all: '🌐 All', buy: '🚀 Buy', sell: '📉 Sell', trending: '🔥 Trending', small: '🌱 Small Cap',
}

const SIG_COLOR: Record<Signal['type'], string> = {
  'STRONG BUY': '#00E676', 'BUY': '#00C853', 'HOLD': '#F7931A', 'SELL': '#FF3D57', 'STRONG SELL': '#FF1744',
}

function SignalCard({ sig }: { sig: Signal }) {
  const [open, setOpen] = useState(false)
  const color = SIG_COLOR[sig.type]
  return (
    <div className="card" style={{ marginBottom: 10, borderLeft: `3px solid ${color}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        {sig.image && <img src={sig.image} width={34} height={34} style={{ borderRadius: '50%' }} onError={e => ((e.target as HTMLImageElement).style.display = 'none')} />}
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 14 }}>{sig.symbol.toUpperCase()}</strong>
          <div className="muted" style={{ fontSize: 11 }}>{sig.name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ background: color + '22', color, padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>
            {sig.type}
          </span>
          <div className={`badge badge-${sig.change24h >= 0 ? 'green' : 'red'}`} style={{ marginTop: 4, display: 'block', fontSize: 10 }}>
            {sig.change24h >= 0 ? '▲' : '▼'}{Math.abs(sig.change24h).toFixed(2)}%
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
        {[
          { label: 'Price', val: `$${fp(sig.price)}` },
          { label: 'Score', val: `${sig.score}/100` },
          { label: 'Confidence', val: `${sig.confidence}%` },
        ].map(({ label, val }) => (
          <div key={label} style={{ padding: '6px 10px', background: '#141414', borderRadius: 8 }}>
            <div className="muted" style={{ fontSize: 9, marginBottom: 2 }}>{label}</div>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{val}</div>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: 6 }}>
        <div style={{ height: 4, background: '#2A2A2A', borderRadius: 2 }}>
          <div style={{ width: `${sig.score}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.5s' }} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
        {sig.isTrending && <span className="badge badge-orange" style={{ fontSize: 10 }}>🔥 Trending</span>}
        {sig.isSmallCap && <span className="badge" style={{ background: '#1A2A1A', color: '#00C853', fontSize: 10 }}>🌱 Small Cap</span>}
        {sig.change7d !== 0 && (
          <span className="badge" style={{ background: '#1A1A2A', color: '#7C9FF7', fontSize: 10 }}>
            7d: {sig.change7d >= 0 ? '+' : ''}{sig.change7d.toFixed(1)}%
          </span>
        )}
      </div>

      <button onClick={() => setOpen(o => !o)} style={{ background: 'none', border: 'none', color: '#606060', cursor: 'pointer', fontSize: 12, padding: 0 }}>
        {open ? '▲ Hide WHY' : '▼ WHY this signal?'}
      </button>
      {open && (
        <div style={{ marginTop: 8, padding: '10px 12px', background: '#141414', borderRadius: 8 }}>
          {sig.reasons.map((r, i) => <div key={i} style={{ fontSize: 12, color: '#C0C0C0', padding: '3px 0', borderBottom: i < sig.reasons.length - 1 ? '1px solid #1E1E1E' : 'none' }}>• {r}</div>)}
        </div>
      )}
    </div>
  )
}

export default function Signals() {
  const [filter, setFilter] = useState<Filter>('all')
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  async function load() {
    setLoading(true)
    try {
      const [coins, trending] = await Promise.all([fetchTopCoins(150), fetchTrending()])
      const trendingIds = new Set(trending.map((t: TrendingCoin) => t.id))
      const trendingExtra = trending
        .filter((t: TrendingCoin) => !coins.find((c: Coin) => c.id === t.id))
        .map((t: TrendingCoin) => ({
          id: t.id, symbol: t.symbol, name: t.name, image: t.small || '',
          current_price: 0, market_cap: 0, market_cap_rank: 999,
          total_volume: 0, price_change_24h: 0, price_change_percentage_24h: 0,
          ath: 0, ath_change_percentage: 0, circulating_supply: 0,
        } as Coin))

      const allCoins = [...coins, ...trendingExtra]
      const sigs = allCoins.map(c => {
        const s = generateSignal(c)
        s.isTrending = trendingIds.has(c.id)
        return s
      })
      sigs.sort((a, b) => Math.abs(b.score - 50) - Math.abs(a.score - 50))
      setSignals(sigs)
      setLastUpdate(new Date())
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const filtered = useMemo(() => signals.filter(s => {
    if (filter === 'buy')     return s.score >= 58
    if (filter === 'sell')    return s.score <= 42
    if (filter === 'trending') return s.isTrending
    if (filter === 'small')   return s.isSmallCap
    return true
  }), [signals, filter])

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>🎯 Signals</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {lastUpdate && <span className="muted" style={{ fontSize: 10 }}>{lastUpdate.toLocaleTimeString()}</span>}
          <button onClick={load} style={{ background: '#1A1A1A', border: '1px solid #2A2A2A', borderRadius: 8, color: '#A0A0A0', cursor: 'pointer', fontSize: 12, padding: '6px 10px' }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      <div className="pills">
        {(Object.keys(FILTER_LABELS) as Filter[]).map(f => (
          <button key={f} className={`pill${filter === f ? ' active' : ''}`} onClick={() => setFilter(f)}>
            {FILTER_LABELS[f]}
          </button>
        ))}
      </div>

      {loading && [0,1,2,3].map(i => <SkeletonCard key={i} />)}
      {!loading && filtered.length === 0 && <div className="muted" style={{ textAlign: 'center', padding: '40px 0' }}>No signals for this filter.</div>}
      {!loading && filtered.slice(0, 50).map(s => <SignalCard key={s.id} sig={s} />)}
    </div>
  )
}
