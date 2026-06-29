import { useState, useEffect, useCallback } from 'react'
import { searchCoins, fetchCoinDetail, fp, fmcap } from '../api/coingecko'
import { useStore } from '../store'
import { hapticNotify } from '../utils/telegram'
import Spinner from '../components/Spinner'
import type { Holding } from '../types'

function useDebounced(value: string, delay = 400) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

interface LiveData { price: number; chg24: number; mcap: number }

function HoldingCard({ h, live, onRemove }: { h: Holding; live?: LiveData; onRemove: () => void }) {
  const price = live?.price ?? 0
  const chg24 = live?.chg24 ?? 0
  const value = price * h.amount
  const cost  = h.buyPrice * h.amount
  const pnl   = value - cost
  const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0
  const pos   = chg24 >= 0

  return (
    <div className="card" style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        {h.image && <img src={h.image} width={36} height={36} style={{ borderRadius: '50%' }} onError={e => ((e.target as HTMLImageElement).style.display = 'none')} />}
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 14 }}>{h.symbol.toUpperCase()}</strong>
          <div className="muted" style={{ fontSize: 11 }}>{h.name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{price > 0 ? `$${fp(price)}` : '—'}</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: pos ? '#00C853' : '#FF3D57' }}>
            {pos ? '▲' : '▼'}{Math.abs(chg24).toFixed(2)}%
          </div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
        {[
          { label: 'Amount', val: h.amount < 0.001 ? h.amount.toExponential(2) : String(h.amount) },
          { label: 'Buy Price', val: `$${fp(h.buyPrice)}` },
          { label: 'Value', val: value > 0 ? fmcap(value) : '—' },
          { label: 'PnL', val: cost > 0 ? `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%` : '—', col: pnlPct >= 0 ? '#00C853' : '#FF3D57' },
        ].map(({ label, val, col }) => (
          <div key={label} style={{ padding: '7px 10px', background: '#141414', borderRadius: 8 }}>
            <div className="muted" style={{ fontSize: 9, marginBottom: 2 }}>{label}</div>
            <div style={{ fontWeight: 700, fontSize: 12, color: col || '#E0E0E0' }}>{val}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 10, textAlign: 'right' }}>
        <button onClick={onRemove} style={{ background: 'none', border: 'none', color: '#404040', cursor: 'pointer', fontSize: 12 }}>
          Remove
        </button>
      </div>
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
        if (md) setLivePrices(prev => ({
          ...prev,
          [h.coinId]: { price: md.current_price?.usd ?? 0, chg24: md.price_change_percentage_24h ?? 0, mcap: md.market_cap?.usd ?? 0 },
        }))
      } catch { /* silent */ }
    }
  }, [holdings])

  useEffect(() => { if (holdings.length) loadPrices() }, [holdings.length])

  function confirmAdd() {
    if (!selected) return
    const amt = parseFloat(amount)
    const bp  = parseFloat(buyPrice)
    if (isNaN(amt) || amt <= 0) { setErr('Enter a valid amount'); return }
    if (isNaN(bp) || bp <= 0)   { setErr('Enter a valid buy price'); return }

    addHolding({
      id: `${selected.id}_${Date.now()}`,
      coinId: selected.id,
      symbol: selected.symbol,
      name: selected.name,
      image: selected.large || selected.thumb || '',
      amount: amt,
      buyPrice: bp,
      addedAt: Date.now(),
    })
    hapticNotify('success')
    setAdding(false); setSelected(null); setQuery(''); setAmount(''); setBuyPrice(''); setErr('')
  }

  const totalValue = holdings.reduce((sum, h) => sum + (livePrices[h.coinId]?.price ?? 0) * h.amount, 0)
  const totalCost  = holdings.reduce((sum, h) => sum + h.buyPrice * h.amount, 0)
  const totalPnlPct = totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 14 }}>
        <h2 style={{ margin: 0 }}>💼 Portfolio</h2>
        {holdings.length > 0 && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 800, fontSize: 16 }}>{totalValue > 0 ? fmcap(totalValue) : '—'}</div>
            {totalCost > 0 && (
              <div style={{ fontSize: 12, color: totalPnlPct >= 0 ? '#00C853' : '#FF3D57', fontWeight: 600 }}>
                {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(1)}% overall
              </div>
            )}
          </div>
        )}
      </div>

      {holdings.length === 0 && !adding && (
        <div style={{ textAlign: 'center', color: '#505050', padding: '40px 0', lineHeight: 2 }}>
          No holdings yet.<br />Add your first coin below.
        </div>
      )}

      {holdings.map(h => (
        <HoldingCard key={h.id} h={h} live={livePrices[h.coinId]} onRemove={() => { removeHolding(h.id); hapticNotify('warning') }} />
      ))}

      {adding ? (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>Add Holding</div>
          <div style={{ position: 'relative', marginTop: 10 }}>
            <input placeholder="Search any coin…" value={query} onChange={e => { setQuery(e.target.value); setSelected(null); setErr('') }} />
            {searching && <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 12, color: '#606060' }}>…</div>}
          </div>

          {selected && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', background: '#0D2A0D', borderRadius: 10, marginTop: 8, border: '1px solid #1A4A1A' }}>
              {(selected.thumb || selected.large) && <img src={selected.thumb || selected.large} width={28} height={28} style={{ borderRadius: '50%' }} />}
              <span style={{ flex: 1, fontWeight: 700, fontSize: 13 }}>{selected.name} ({selected.symbol?.toUpperCase()})</span>
              <button onClick={() => { setSelected(null); setQuery('') }} style={{ background: 'none', border: 'none', color: '#606060', cursor: 'pointer', fontSize: 16 }}>✕</button>
            </div>
          )}

          {results.length > 0 && !selected && (
            <div style={{ background: '#141414', borderRadius: 10, marginTop: 4, border: '1px solid #2A2A2A', maxHeight: 180, overflowY: 'auto' }}>
              {results.map((r) => (
                <div key={r.id} onClick={() => { setSelected(r); setQuery(r.name); setResults([]) }}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', cursor: 'pointer', borderBottom: '1px solid #1E1E1E' }}>
                  {r.thumb && <img src={r.thumb} width={24} height={24} style={{ borderRadius: '50%' }} />}
                  <span style={{ flex: 1, fontSize: 13 }}>{r.name}</span>
                  <span className="muted" style={{ fontSize: 11 }}>{r.symbol?.toUpperCase()}</span>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 10 }}>
            <div>
              <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Amount</div>
              <input type="number" placeholder="0.5" value={amount} onChange={e => { setAmount(e.target.value); setErr('') }} />
            </div>
            <div>
              <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Buy Price (USD)</div>
              <input type="number" placeholder="45000" value={buyPrice} onChange={e => { setBuyPrice(e.target.value); setErr('') }} />
            </div>
          </div>
          {err && <div style={{ color: '#FF3D57', fontSize: 12, marginTop: 6 }}>{err}</div>}
          <button className="btn" onClick={confirmAdd}>Add to Portfolio</button>
          <button onClick={() => { setAdding(false); setSelected(null); setQuery(''); setResults([]) }}
            style={{ background: 'none', border: 'none', color: '#606060', cursor: 'pointer', width: '100%', marginTop: 8, padding: 8, fontSize: 13 }}>
            Cancel
          </button>
        </div>
      ) : (
        <button className="btn" onClick={() => setAdding(true)}>＋ Add Holding</button>
      )}
    </div>
  )
}
