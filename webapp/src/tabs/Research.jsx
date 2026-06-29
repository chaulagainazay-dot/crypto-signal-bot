import { useState } from 'react'
import { fetchCoinDetail, searchCoins, fetchByContract, fetchGTPool, fp, fmcap, isAddress } from '../api/coingecko'
import Spinner from '../components/Spinner'

function DetailView({ data, onBack }) {
  const gt = data._geckoterminal
  const attrs = data._attrs || data

  if (gt) {
    const a = attrs
    const priceUsd = parseFloat(a.price_usd || 0)
    const chg24 = parseFloat(a.price_change_percentage?.h24 || 0)
    return (
      <div className="tab-content">
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#F7931A', cursor: 'pointer', padding: '0 0 12px', fontSize: 14 }}>← Back</button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          {a.image_url && <img src={a.image_url} width={48} height={48} style={{ borderRadius: '50%' }} />}
          <div>
            <h2 style={{ margin: 0 }}>{a.name || a.symbol} <span style={{ color: '#606060', fontWeight: 400, fontSize: 14 }}>({(a.symbol || '').toUpperCase()})</span></h2>
            <div className="muted">via GeckoTerminal · {data._network}</div>
          </div>
        </div>
        <div className="card">
          <div className="row"><span className="muted">Price</span><strong>${fp(priceUsd)}</strong></div>
          <div className="row"><span className="muted">24h Change</span>
            <span className={`badge badge-${chg24 >= 0 ? 'green' : 'red'}`}>{chg24 >= 0 ? '▲' : '▼'} {Math.abs(chg24).toFixed(2)}%</span>
          </div>
          {a.fdv_usd && <div className="row"><span className="muted">FDV</span><span>{fmcap(parseFloat(a.fdv_usd))}</span></div>}
          {a.market_cap_usd && <div className="row"><span className="muted">Market Cap</span><span>{fmcap(parseFloat(a.market_cap_usd))}</span></div>}
          {a.volume_usd?.h24 && <div className="row"><span className="muted">24h Volume</span><span>{fmcap(parseFloat(a.volume_usd.h24))}</span></div>}
        </div>
        {a.gt_score && (
          <div className="card">
            <div className="row"><span className="muted">GT Score</span><span>{parseFloat(a.gt_score).toFixed(1)}/100</span></div>
          </div>
        )}
      </div>
    )
  }

  const chg = data.market_data?.price_change_percentage_24h || 0
  const price = data.market_data?.current_price?.usd || 0
  return (
    <div className="tab-content">
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#F7931A', cursor: 'pointer', padding: '0 0 12px', fontSize: 14 }}>← Back</button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        {data.image?.large && <img src={data.image.large} width={48} height={48} style={{ borderRadius: '50%' }} />}
        <div>
          <h2 style={{ margin: 0 }}>{data.name} <span style={{ color: '#606060', fontWeight: 400, fontSize: 14 }}>({data.symbol?.toUpperCase()})</span></h2>
          <div className="muted">Rank #{data.market_cap_rank}</div>
        </div>
      </div>
      <div className="card">
        <div className="row"><span className="muted">Price</span><strong style={{ fontSize: 22 }}>${fp(price)}</strong></div>
        <div className="row"><span className="muted">24h</span>
          <span className={`badge badge-${chg >= 0 ? 'green' : 'red'}`}>{chg >= 0 ? '▲' : '▼'} {Math.abs(chg).toFixed(2)}%</span>
        </div>
        {data.market_data?.market_cap?.usd && <div className="row"><span className="muted">Market Cap</span><span>{fmcap(data.market_data.market_cap.usd)}</span></div>}
        {data.market_data?.total_volume?.usd && <div className="row"><span className="muted">24h Volume</span><span>{fmcap(data.market_data.total_volume.usd)}</span></div>}
        {data.market_data?.circulating_supply && <div className="row"><span className="muted">Circulating</span><span>{fmcap(data.market_data.circulating_supply)}</span></div>}
        {data.market_data?.ath?.usd && <div className="row"><span className="muted">ATH</span><span>${fp(data.market_data.ath.usd)}</span></div>}
      </div>
      {data.description?.en && (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>About</div>
          <p style={{ fontSize: 13, lineHeight: 1.6, color: '#C0C0C0', margin: 0 }}>
            {data.description.en.replace(/<[^>]*>/g, '').slice(0, 300)}…
          </p>
        </div>
      )}
    </div>
  )
}

export default function Research({ initialCoinId }) {
  const [query, setQuery]   = useState(initialCoinId || '')
  const [results, setRes]   = useState([])
  const [detail, setDetail] = useState(null)
  const [loading, setLoad]  = useState(false)
  const [error,   setErr]   = useState('')

  async function search() {
    if (!query.trim()) return
    setLoad(true); setErr(''); setRes([])
    try {
      if (isAddress(query.trim())) {
        const d = await fetchByContract(query.trim())
        if (d) { setDetail(d); setLoad(false); return }
        setErr('Contract not found on any chain.')
      } else {
        const r = await searchCoins(query.trim())
        if (r.length === 0) setErr('No results found.')
        setRes(r)
      }
    } catch (e) {
      setErr('Search failed. Try again.')
    }
    setLoad(false)
  }

  async function openCoin(id) {
    setLoad(true); setErr('')
    try {
      const d = await fetchCoinDetail(id)
      setDetail(d)
    } catch { setErr('Failed to load details.') }
    setLoad(false)
  }

  if (detail) return <DetailView data={detail} onBack={() => setDetail(null)} />

  return (
    <div className="tab-content">
      <h2>🔍 Research</h2>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          placeholder="Coin name, symbol, or contract address…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          style={{ flex: 1 }}
        />
        <button className="btn" onClick={search} style={{ width: 'auto', padding: '0 18px', flex: 'none' }}>Go</button>
      </div>

      {loading && <Spinner text="Searching…" />}
      {error && <div style={{ color: '#FF3D57', textAlign: 'center', padding: '24px 0' }}>{error}</div>}

      {!loading && results.map(c => (
        <div key={c.id} className="card" style={{ cursor: 'pointer' }} onClick={() => openCoin(c.id)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {c.thumb && <img src={c.thumb} width={32} height={32} style={{ borderRadius: '50%' }} />}
            <div>
              <strong>{c.name}</strong>
              <div className="muted">{c.symbol?.toUpperCase()} {c.market_cap_rank ? `· #${c.market_cap_rank}` : ''}</div>
            </div>
          </div>
        </div>
      ))}

      {!loading && results.length === 0 && !error && (
        <div style={{ color: '#505050', textAlign: 'center', padding: '32px 0', fontSize: 13 }}>
          Type a coin name (Bitcoin), ticker (BTC),<br />or paste a contract address (0x… / base58)
        </div>
      )}
    </div>
  )
}
