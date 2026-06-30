import { useState, useEffect, useMemo } from 'react'
import { fetchTopCoins, fetchTrending } from '../api/coingecko'
import { generateSignal } from '../utils/signals'
import { fp } from '../api/coingecko'
import { SkeletonCard } from '../components/Skeleton'
import { ChipRow, ProgressBar, EmptyState } from '../components/ui'
import type { Signal, Coin, TrendingCoin } from '../types'

type Filter = 'all' | 'buy' | 'sell' | 'trending' | 'small'
const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all',      label: 'All'      },
  { value: 'buy',      label: 'Buy'      },
  { value: 'sell',     label: 'Sell'     },
  { value: 'trending', label: 'Trending' },
  { value: 'small',    label: 'Small Cap'},
]

const SIG_COLOR: Record<Signal['type'], string> = {
  'STRONG BUY': '#22C55E', 'BUY': '#4ADE80', 'HOLD': '#F59E0B',
  'SELL': '#EF4444', 'STRONG SELL': '#DC2626',
}
const SIG_CLASS: Record<Signal['type'], string> = {
  'STRONG BUY': 'badge-buy', 'BUY': 'badge-buy', 'HOLD': 'badge-hold',
  'SELL': 'badge-sell', 'STRONG SELL': 'badge-sell',
}

function SignalCard({ sig }: { sig: Signal }) {
  const [open, setOpen] = useState(false)
  const color = SIG_COLOR[sig.type]
  const chgPos = sig.change24h >= 0

  return (
    <div className="card" style={{ borderLeft: `3px solid ${color}`, marginBottom: 8 }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        {sig.image && (
          <img src={sig.image} className="coin-avatar" style={{ width: 36, height: 36 }}
            onError={e => ((e.target as HTMLImageElement).style.display = 'none')} />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{sig.symbol.toUpperCase()}</div>
          <div className="muted" style={{ fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sig.name}</div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <span className={`badge ${SIG_CLASS[sig.type]}`}>{sig.type}</span>
          <div style={{ fontSize: 12, fontWeight: 600, color: chgPos ? 'var(--green)' : 'var(--red)', marginTop: 4 }}>
            {chgPos ? '+' : ''}{sig.change24h.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div className="stat-grid-4" style={{ marginBottom: 10 }}>
        {[
          { label: 'Price',      value: `$${fp(sig.price)}` },
          { label: 'Score',      value: `${sig.score}/100`  },
          { label: 'Confidence', value: `${sig.confidence}%` },
          { label: '7d',         value: `${sig.change7d >= 0 ? '+' : ''}${sig.change7d.toFixed(1)}%`, color: sig.change7d >= 0 ? 'var(--green)' : 'var(--red)' },
        ].map(({ label, value, color: c }) => (
          <div key={label} className="stat-box">
            <div className="label">{label}</div>
            <div className="value" style={c ? { color: c } : undefined}>{value}</div>
          </div>
        ))}
      </div>

      {/* Score bar */}
      <ProgressBar pct={sig.score} color={color} height={3} />

      {/* Tags */}
      {(sig.isTrending || sig.isSmallCap) && (
        <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
          {sig.isTrending && <span className="badge badge-hot">Trending</span>}
          {sig.isSmallCap && <span className="badge badge-blue">Small Cap</span>}
        </div>
      )}

      {/* Expand why */}
      <button onClick={() => setOpen(o => !o)} style={{
        display: 'flex', alignItems: 'center', gap: 4, marginTop: 10,
        background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer',
        fontSize: 12, fontFamily: 'inherit', padding: 0,
      }}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"
          style={{ transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }}>
          <path d="M3 5l4 4 4-4"/>
        </svg>
        Why this signal?
      </button>

      {open && (
        <div style={{ marginTop: 8, padding: '10px 12px', background: 'var(--surface2)', borderRadius: 8 }}>
          {sig.reasons.map((r, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text2)', padding: '4px 0', borderBottom: i < sig.reasons.length - 1 ? '1px solid var(--border2)' : 'none' }}>
              · {r}
            </div>
          ))}
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
      const sigs = allCoins.map(c => { const s = generateSignal(c); s.isTrending = trendingIds.has(c.id); return s })
      sigs.sort((a, b) => Math.abs(b.score - 50) - Math.abs(a.score - 50))
      setSignals(sigs)
      setLastUpdate(new Date())
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const filtered = useMemo(() => signals.filter(s => {
    if (filter === 'buy')      return s.score >= 58
    if (filter === 'sell')     return s.score <= 42
    if (filter === 'trending') return s.isTrending
    if (filter === 'small')    return s.isSmallCap
    return true
  }), [signals, filter])

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h1 className="page-title">Signals</h1>
          {!loading && <span className="badge badge-blue">{filtered.length}</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {lastUpdate && <span className="muted" style={{ fontSize: 10 }}>{lastUpdate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
          <button onClick={load} className="btn-icon" title="Refresh">
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M13 7.5A5.5 5.5 0 1 1 7.5 2a5.5 5.5 0 0 1 4 1.7"/>
              <path d="M13 2v3.5H9.5"/>
            </svg>
          </button>
        </div>
      </div>

      <ChipRow options={FILTERS} active={filter} onChange={setFilter} />

      {loading && [0,1,2,3].map(i => <SkeletonCard key={i} />)}
      {!loading && filtered.length === 0 && <EmptyState icon="🎯" title="No signals" sub="No signals match this filter right now." />}
      {!loading && filtered.slice(0, 50).map(s => <SignalCard key={s.id} sig={s} />)}
    </div>
  )
}
