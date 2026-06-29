import { useState, useEffect, useRef } from 'react'
import { searchCoins, fetchCoinDetail, fp, fmcap } from '../api/coingecko'

const KEY = 'hcg_portfolio_v3'
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || [] } catch { return [] } }
const save = h => localStorage.setItem(KEY, JSON.stringify(h))

// holding shape: { coinId, symbol, name, image, amount, buyPrice }

function useDebouncedSearch(query, delay = 400) {
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const timer = useRef(null)

  useEffect(() => {
    if (!query || query.length < 2) { setResults([]); return }
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      setSearching(true)
      try {
        const r = await searchCoins(query)
        setResults(r.slice(0, 6))
      } catch { setResults([]) }
      setSearching(false)
    }, delay)
    return () => clearTimeout(timer.current)
  }, [query])

  return { results, searching }
}

export default function Portfolio() {
  const [holdings, setHoldings] = useState(load)
  const [livePrices, setLive]   = useState({}) // coinId → price
  const [adding,  setAdding]    = useState(false)
  const [query,   setQuery]     = useState('')
  const [picked,  setPicked]    = useState(null) // { coinId, symbol, name, image }
  const [amount,  setAmount]    = useState('')
  const [buyPx,   setBuyPx]     = useState('')
  const [err,     setErr]       = useState('')
  const [priceLoading, setPL]   = useState(false)

  const { results, searching } = useDebouncedSearch(picked ? '' : query)

  // Fetch live prices for all held coins
  useEffect(() => {
    if (holdings.length === 0) return
    const ids = [...new Set(holdings.map(h => h.coinId))]
    Promise.all(ids.map(id => fetchCoinDetail(id).catch(() => null)))
      .then(details => {
        const m = {}
        details.forEach(d => { if (d) m[d.id] = d.market_data?.current_price?.usd || 0 })
        setLive(m)
      })
  }, [holdings.length])

  const totalValue = holdings.reduce((s, h) => s + (livePrices[h.coinId] || 0) * h.amount, 0)
  const totalCost  = holdings.reduce((s, h) => s + h.buyPrice * h.amount, 0)
  const totalPnl   = totalValue - totalCost
  const pnlPct     = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0

  function pickCoin(coin) {
    setPicked({ coinId: coin.id, symbol: coin.symbol?.toUpperCase(), name: coin.name, image: coin.thumb || coin.large })
    setQuery(coin.name)
    setErr('')
  }

  async function autofillPrice(coinId) {
    if (buyPx) return
    setPL(true)
    try {
      const d = await fetchCoinDetail(coinId)
      const p = d?.market_data?.current_price?.usd
      if (p) setBuyPx(String(p))
    } catch {}
    setPL(false)
  }

  function add() {
    if (!picked)             { setErr('Select a coin from the list.'); return }
    if (!amount || isNaN(parseFloat(amount))) { setErr('Enter a valid amount.'); return }

    const h = {
      coinId:   picked.coinId,
      symbol:   picked.symbol,
      name:     picked.name,
      image:    picked.image,
      amount:   parseFloat(amount),
      buyPrice: parseFloat(buyPx) || 0,
    }
    const updated = [...holdings, h]
    setHoldings(updated); save(updated)
    // prime live price immediately
    fetchCoinDetail(h.coinId).then(d => {
      setLive(prev => ({ ...prev, [h.coinId]: d?.market_data?.current_price?.usd || 0 }))
    }).catch(() => {})
    // reset form
    setAdding(false); setPicked(null); setQuery(''); setAmount(''); setBuyPx(''); setErr('')
  }

  function remove(i) {
    const updated = holdings.filter((_, j) => j !== i)
    setHoldings(updated); save(updated)
  }

  return (
    <div className="tab-content">
      <h2>💼 Portfolio</h2>

      {/* Summary card */}
      <div className="card" style={{ marginBottom: 16, background: 'linear-gradient(135deg, #1A1A1A, #242424)' }}>
        <div className="muted" style={{ marginBottom: 4 }}>Total Value</div>
        <div style={{ fontSize: 32, fontWeight: 900 }}>{totalValue > 0 ? fmcap(totalValue) : '$0'}</div>
        {totalCost > 0 && (
          <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: totalPnl >= 0 ? '#00C853' : '#FF3D57', fontWeight: 700 }}>
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
          No holdings yet.<br />Add any coin or token below.
        </div>
      )}

      {holdings.map((h, i) => {
        const cur  = livePrices[h.coinId] || 0
        const val  = cur * h.amount
        const cost = h.buyPrice * h.amount
        const pnl  = val - cost
        const pct  = cost > 0 ? (pnl / cost) * 100 : 0
        return (
          <div key={i} className="card">
            <div className="row">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {h.image && <img src={h.image} width={36} height={36} style={{ borderRadius: '50%' }} onError={e => e.target.style.display='none'} />}
                <div>
                  <strong>{h.symbol}</strong>
                  <div className="muted" style={{ fontSize: 11 }}>{h.name}</div>
                  <div className="muted" style={{ fontSize: 11 }}>{h.amount} tokens</div>
                </div>
              </div>
              <div className="col" style={{ alignItems: 'flex-end' }}>
                <strong>{cur > 0 ? fmcap(val) : '—'}</strong>
                {cost > 0 && cur > 0 && (
                  <span className={`badge badge-${pnl >= 0 ? 'green' : 'red'}`}>
                    {pnl >= 0 ? '+' : ''}{pct.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #242424', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="muted">{cur > 0 ? `$${fp(cur)}` : 'Loading…'}</span>
              {h.buyPrice > 0 && <span className="muted">Avg: ${fp(h.buyPrice)}</span>}
              <button onClick={() => remove(i)} style={{ background: 'none', border: 'none', color: '#505050', cursor: 'pointer', fontSize: 15, padding: 0 }}>✕</button>
            </div>
          </div>
        )
      })}

      {/* Add form */}
      {adding ? (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>Add Any Token</div>

          {/* Search input */}
          <div style={{ position: 'relative', marginTop: 10 }}>
            <input
              placeholder="Search: Bitcoin, ravedao, PEPE…"
              value={query}
              onChange={e => { setQuery(e.target.value); setPicked(null); setErr('') }}
              autoComplete="off"
            />
            {searching && (
              <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#A0A0A0', fontSize: 12 }}>…</span>
            )}
          </div>

          {/* Dropdown results */}
          {!picked && results.length > 0 && (
            <div style={{ background: '#141414', border: '1px solid #2A2A2A', borderRadius: 10, overflow: 'hidden', marginTop: 4 }}>
              {results.map(c => (
                <div key={c.id} onClick={() => { pickCoin(c); autofillPrice(c.id) }}
                  style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid #1E1E1E' }}>
                  {c.thumb && <img src={c.thumb} width={28} height={28} style={{ borderRadius: '50%' }} />}
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{c.name}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{c.symbol?.toUpperCase()}{c.market_cap_rank ? ` · #${c.market_cap_rank}` : ' · small cap'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Selected coin badge */}
          {picked && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, padding: '8px 12px', background: '#1A2A1A', borderRadius: 8 }}>
              {picked.image && <img src={picked.image} width={24} height={24} style={{ borderRadius: '50%' }} onError={e => e.target.style.display='none'} />}
              <span style={{ fontSize: 13, fontWeight: 600, color: '#00C853' }}>✓ {picked.name} ({picked.symbol})</span>
              <button onClick={() => { setPicked(null); setQuery('') }} style={{ background: 'none', border: 'none', color: '#606060', cursor: 'pointer', marginLeft: 'auto', fontSize: 13 }}>✕</button>
            </div>
          )}

          {err && <div style={{ color: '#FF3D57', fontSize: 12, marginTop: 6 }}>{err}</div>}

          <input placeholder="Amount (e.g. 1000)" type="number" value={amount}
            onChange={e => setAmount(e.target.value)} style={{ marginTop: 10 }} />

          <div style={{ position: 'relative', marginTop: 8 }}>
            <input placeholder="Avg buy price USD (optional)" type="number" value={buyPx}
              onChange={e => setBuyPx(e.target.value)} />
            {priceLoading && (
              <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#A0A0A0', fontSize: 11 }}>fetching…</span>
            )}
          </div>
          <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>Leave blank to auto-fill current price</div>

          <button className="btn" onClick={add} style={{ marginTop: 12 }}>Add to Portfolio</button>
          <button onClick={() => { setAdding(false); setPicked(null); setQuery(''); setAmount(''); setBuyPx(''); setErr('') }}
            style={{ background: 'none', border: 'none', color: '#A0A0A0', cursor: 'pointer', width: '100%', marginTop: 8, padding: 8, fontSize: 14 }}>
            Cancel
          </button>
        </div>
      ) : (
        <button className="btn" onClick={() => setAdding(true)}>＋ Add Any Token</button>
      )}
    </div>
  )
}
