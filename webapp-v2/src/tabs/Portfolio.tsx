import { useState, useEffect, useCallback } from 'react'
import { searchCoins, fetchCoinDetail, fp, fmcap } from '../api/coingecko'
import { useStore } from '../store'
import { hapticNotify } from '../utils/telegram'
import { Spinner, EmptyState, ProgressBar } from '../components/ui'
import type { Holding } from '../types'

function useDebounced(value: string, delay = 400) {
  const [d, setD] = useState(value)
  useEffect(() => { const t = setTimeout(() => setD(value), delay); return () => clearTimeout(t) }, [value, delay])
  return d
}

interface LiveData { price: number; chg24: number; mcap: number }

function HoldingCard({ h, live, onRemove }: { h: Holding; live?: LiveData; onRemove: () => void }) {
  const price  = live?.price ?? 0
  const chg24  = live?.chg24 ?? 0
  const value  = price * h.amount
  const cost   = h.buyPrice * h.amount
  const pnl    = value - cost
  const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0
  const up     = chg24 >= 0
  const profiting = pnlPct >= 0

  return (
    <div className="card" style={{ marginBottom: 8 }}>
      {/* Top row: coin identity + price */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        {h.image && <img src={h.image} className="coin-avatar" onError={e => ((e.target as HTMLImageElement).style.display = 'none')} />}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{h.symbol.toUpperCase()}</div>
          <div className="muted" style={{ fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: 700, fontSize: 15 }}>{price > 0 ? `$${fp(price)}` : '—'}</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: up ? 'var(--green)' : 'var(--red)' }}>
            {up ? '+' : ''}{chg24.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="stat-grid-4">
        {[
          { label: 'Amount',    value: h.amount < 0.001 ? h.amount.toExponential(2) : String(h.amount) },
          { label: 'Avg Buy',   value: `$${fp(h.buyPrice)}` },
          { label: 'Value',     value: value > 0 ? fmcap(value) : '—' },
          { label: 'PnL',       value: cost > 0 ? `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%` : '—', color: profiting ? 'var(--green)' : 'var(--red)' },
        ].map(({ label, value: v, color }) => (
          <div key={label} className="stat-box">
            <div className="label">{label}</div>
            <div className="value" style={color ? { color } : undefined}>{v}</div>
          </div>
        ))}
      </div>

      {cost > 0 && (
        <div style={{ marginTop: 10 }}>
          <ProgressBar pct={Math.min(100, Math.max(0, 50 + pnlPct / 2))} color={profiting ? 'var(--green)' : 'var(--red)'} height={3} />
        </div>
      )}

      <button onClick={onRemove} style={{
        marginTop: 10, background: 'none', border: 'none', color: 'var(--text3)',
        cursor: 'pointer', fontSize: 11, fontFamily: 'inherit', padding: 0,
      }}>
        Remove holding
      </button>
    </div>
  )
}

export default function Portfolio() {
  const { holdings, addHolding, removeHolding } = useStore()
  const [adding, setAdding] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Array<{ id: string; name: string; symbol: string; thumb?: string; large?: string }>>([])
  const [searching, setSearching] = useState(false)
  const [selected, setSelected] = useState<typeof results[0] | null>(null)
  const [amount, setAmount] = useState('')
  const [buyPrice, setBuyPrice] = useState('')
  const [livePrices, setLivePrices] = useState<Record<string, LiveData>>({})
  const [err, setErr] = useState('')

  const debouncedQ = useDebounced(query)

  useEffect(() => {
    if (!debouncedQ.trim() || selected) { setResults([]); return }
    setSearching(true)
    searchCoins(debouncedQ).then(r => setResults(r as typeof results)).catch(() => {}).finally(() => setSearching(false))
  }, [debouncedQ])

  const loadPrices = useCallback(async () => {
    for (const h of holdings) {
      try {
        const d = await fetchCoinDetail(h.coinId) as { market_data?: { current_price?: { usd: number }; price_change_percentage_24h?: number; market_cap?: { usd: number } } }
        const md = d?.market_data
        if (md) setLivePrices(prev => ({ ...prev, [h.coinId]: { price: md.current_price?.usd ?? 0, chg24: md.price_change_percentage_24h ?? 0, mcap: md.market_cap?.usd ?? 0 } }))
      } catch { /* silent */ }
    }
  }, [holdings])

  useEffect(() => { if (holdings.length) loadPrices() }, [holdings.length])

  function confirmAdd() {
    if (!selected) return
    const amt = parseFloat(amount)
    const bp  = parseFloat(buyPrice)
    if (isNaN(amt) || amt <= 0) { setErr('Enter a valid amount'); return }
    if (isNaN(bp)  || bp  <= 0) { setErr('Enter a valid buy price'); return }
    addHolding({ id: `${selected.id}_${Date.now()}`, coinId: selected.id, symbol: selected.symbol, name: selected.name, image: selected.large || selected.thumb || '', amount: amt, buyPrice: bp, addedAt: Date.now() })
    hapticNotify('success')
    setAdding(false); setSelected(null); setQuery(''); setAmount(''); setBuyPrice(''); setErr('')
  }

  const totalValue   = holdings.reduce((s, h) => s + (livePrices[h.coinId]?.price ?? 0) * h.amount, 0)
  const totalCost    = holdings.reduce((s, h) => s + h.buyPrice * h.amount, 0)
  const totalPnlPct  = totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0
  const totalPnlAbs  = totalValue - totalCost

  return (
    <div className="tab-content">
      {/* Header */}
      <div className="row" style={{ marginBottom: holdings.length > 0 ? 12 : 16 }}>
        <h1 className="page-title">Portfolio</h1>
        {!adding && (
          <button className="btn-icon" onClick={() => setAdding(true)} title="Add holding" style={{ width: 'auto', padding: '0 14px', fontSize: 13, fontWeight: 600, gap: 6, display: 'flex', alignItems: 'center' }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M7 2v10M2 7h10"/></svg>
            Add
          </button>
        )}
      </div>

      {/* Summary strip */}
      {holdings.length > 0 && totalCost > 0 && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="stat-grid-4">
            <div className="stat-box">
              <div className="label">Invested</div>
              <div className="value">{fmcap(totalCost)}</div>
            </div>
            <div className="stat-box">
              <div className="label">Value</div>
              <div className="value">{totalValue > 0 ? fmcap(totalValue) : '—'}</div>
            </div>
            <div className="stat-box">
              <div className="label">P&amp;L</div>
              <div className="value" style={{ color: totalPnlPct >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(1)}%
              </div>
            </div>
            <div className="stat-box">
              <div className="label">Net</div>
              <div className="value" style={{ color: totalPnlAbs >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {totalPnlAbs >= 0 ? '+' : ''}${Math.abs(totalPnlAbs) > 1000 ? fmcap(Math.abs(totalPnlAbs)) : Math.abs(totalPnlAbs).toFixed(0)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {holdings.length === 0 && !adding && (
        <EmptyState icon="💼" title="No holdings yet" sub="Track your crypto portfolio with real-time P&L."
          action={<button className="btn" onClick={() => setAdding(true)}>Add your first coin</button>} />
      )}

      {/* Holdings list */}
      {holdings.map(h => (
        <HoldingCard key={h.id} h={h} live={livePrices[h.coinId]} onRemove={() => { removeHolding(h.id); hapticNotify('warning') }} />
      ))}

      {/* Add form */}
      {adding && (
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14 }}>Add Holding</div>

          <div style={{ position: 'relative', marginBottom: 10 }}>
            <input placeholder="Search coin by name…" value={query} onChange={e => { setQuery(e.target.value); setSelected(null); setErr('') }} />
            {searching && <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 12, color: 'var(--text3)' }}>…</div>}
          </div>

          {selected && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: 'rgba(34,197,94,0.06)', borderRadius: 10, marginBottom: 10, border: '1px solid rgba(34,197,94,0.2)' }}>
              {(selected.thumb || selected.large) && <img src={selected.thumb || selected.large} style={{ width: 28, height: 28, borderRadius: '50%' }} />}
              <span style={{ flex: 1, fontWeight: 700, fontSize: 13 }}>{selected.name} ({selected.symbol?.toUpperCase()})</span>
              <button onClick={() => { setSelected(null); setQuery('') }} style={{ background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer', fontSize: 16 }}>✕</button>
            </div>
          )}

          {results.length > 0 && !selected && (
            <div style={{ background: 'var(--surface2)', borderRadius: 10, marginBottom: 10, border: '1px solid var(--border)', maxHeight: 180, overflowY: 'auto' }}>
              {results.map(r => (
                <div key={r.id} onClick={() => { setSelected(r); setQuery(r.name); setResults([]) }}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', cursor: 'pointer', borderBottom: '1px solid var(--border2)' }}>
                  {r.thumb && <img src={r.thumb} style={{ width: 24, height: 24, borderRadius: '50%' }} />}
                  <span style={{ flex: 1, fontSize: 13 }}>{r.name}</span>
                  <span className="muted" style={{ fontSize: 11 }}>{r.symbol?.toUpperCase()}</span>
                </div>
              ))}
            </div>
          )}

          <div className="stat-grid-2" style={{ marginBottom: 10 }}>
            <div>
              <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Amount</div>
              <input type="number" placeholder="0.5" value={amount} onChange={e => { setAmount(e.target.value); setErr('') }} />
            </div>
            <div>
              <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Buy Price (USD)</div>
              <input type="number" placeholder="45000" value={buyPrice} onChange={e => { setBuyPrice(e.target.value); setErr('') }} />
            </div>
          </div>

          {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 8 }}>{err}</div>}
          <button className="btn" onClick={confirmAdd} style={{ marginBottom: 8 }}>Add to Portfolio</button>
          <button className="btn-ghost" onClick={() => { setAdding(false); setSelected(null); setQuery(''); setResults([]) }}>Cancel</button>
        </div>
      )}

      {holdings.length > 0 && !adding && (
        <button className="btn" style={{ marginTop: 8 }} onClick={() => setAdding(true)}>+ Add Holding</button>
      )}
    </div>
  )
}
