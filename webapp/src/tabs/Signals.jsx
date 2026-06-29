import { useState, useEffect } from 'react'
import { fetchTopCoins, fetchTrending, fetchCryptoNews, fp, fmcap } from '../api/coingecko'
import Spinner from '../components/Spinner'

// ─── Signal engine ────────────────────────────────────────────────────────────

function buildSignal(coin, isTrending = false, trendingRank = null) {
  const chg24 = coin.price_change_percentage_24h || 0
  const chg7d  = coin.price_change_percentage_7d  || 0
  const vol    = coin.total_volume   || coin.volume_usd?.h24 || 0
  const mcap   = coin.market_cap     || coin.market_cap_usd  || 1
  const ath    = coin.ath            || 0
  const price  = coin.current_price  || coin.price || parseFloat(coin.price_usd || 0)
  const vr     = vol / mcap
  const reasons = []
  let score = 50

  // — Momentum
  if (chg24 > 15)      { score += 22; reasons.push(`🚀 Up ${chg24.toFixed(1)}% in 24h — strong breakout`) }
  else if (chg24 > 7)  { score += 13; reasons.push(`📈 Up ${chg24.toFixed(1)}% in 24h — bullish momentum`) }
  else if (chg24 > 3)  { score +=  7; reasons.push(`📊 Up ${chg24.toFixed(1)}% in 24h — mild uptrend`) }
  else if (chg24 < -15){ score -= 22; reasons.push(`💥 Down ${Math.abs(chg24).toFixed(1)}% in 24h — heavy selling`) }
  else if (chg24 < -7) { score -= 13; reasons.push(`📉 Down ${Math.abs(chg24).toFixed(1)}% in 24h — bearish momentum`) }
  else if (chg24 < -3) { score -=  7; reasons.push(`⚠️ Down ${Math.abs(chg24).toFixed(1)}% in 24h — mild decline`) }

  // — Weekly trend
  if (chg7d > 20)      { score += 15; reasons.push(`📅 Up ${chg7d.toFixed(1)}% this week — sustained rally`) }
  else if (chg7d > 8)  { score +=  8; reasons.push(`📅 Up ${chg7d.toFixed(1)}% this week — weekly uptrend`) }
  else if (chg7d < -20){ score -= 15; reasons.push(`📅 Down ${Math.abs(chg7d).toFixed(1)}% this week — weekly downtrend`) }
  else if (chg7d < -8) { score -=  8; reasons.push(`📅 Down ${Math.abs(chg7d).toFixed(1)}% this week — losing ground`) }

  // — Volume activity
  if (vr > 0.4)        { score += 15; reasons.push(`🔥 Very high volume (${(vr*100).toFixed(0)}% of mcap) — huge interest`) }
  else if (vr > 0.2)   { score += 10; reasons.push(`📊 High volume (${(vr*100).toFixed(0)}% of mcap) — active trading`) }
  else if (vr > 0.08)  { score +=  5; reasons.push(`📊 Decent volume — steady trading activity`) }
  else if (vr < 0.01)  { score -=  8; reasons.push(`😴 Very low volume — few people trading`) }

  // — Trending bonus
  if (isTrending) {
    score += 12
    const rank = trendingRank ? `#${trendingRank}` : ''
    reasons.push(`🔥 Trending ${rank} on CoinGecko — viral social interest`)
  }

  // — Small/new coin bonus (potential upside)
  const isSmall = mcap < 500_000_000 // under $500M
  const isNew   = mcap < 50_000_000  // under $50M
  if (isNew   && chg24 > 5)  { score += 8;  reasons.push(`🌱 New/small coin — early-stage, high growth potential`) }
  if (isSmall && chg24 > 5)  { score += 5;  reasons.push(`💎 Small-cap coin — room to grow vs large caps`) }

  // — ATH proximity
  if (ath > 0) {
    const athPct = ((price - ath) / ath) * 100
    if (athPct > -10)        { score -= 10; reasons.push(`⚠️ Near all-time high — be cautious buying here`) }
    else if (athPct < -70)   { score +=  8; reasons.push(`💰 ${Math.abs(athPct).toFixed(0)}% below ATH — deeply discounted`) }
    else if (athPct < -40)   { score +=  4; reasons.push(`📉 ${Math.abs(athPct).toFixed(0)}% below ATH — potential recovery target`) }
  }

  score = Math.max(0, Math.min(100, score))

  let label, color, icon, action
  if (score >= 72) { label = 'STRONG BUY';  color = '#00E676'; icon = '🚀'; action = 'Strong buying opportunity' }
  else if (score >= 58) { label = 'BUY';    color = '#00C853'; icon = '📈'; action = 'Consider buying in portions' }
  else if (score >= 42) { label = 'NEUTRAL'; color = '#F7931A'; icon = '➡️'; action = 'Wait for clearer direction' }
  else if (score >= 28) { label = 'SELL';   color = '#FF3D57'; icon = '📉'; action = 'Consider reducing position' }
  else                  { label = 'STRONG SELL'; color = '#FF1744'; icon = '🔥'; action = 'Avoid — heavy selling pressure' }

  return { label, color, icon, score, action, reasons, isTrending, isSmall, isNew }
}

const FILTERS = ['All', '🚀 Buy', '📉 Sell', '🔥 Trending', '🌱 Small Cap']

export default function Signals() {
  const [allCoins,  setAll]     = useState([])
  const [trending,  setTrend]   = useState([])
  const [loading,   setLoading] = useState(true)
  const [filter,    setFilter]  = useState('All')
  const [expanded,  setExpanded]= useState(null)
  const [error,     setError]   = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchTopCoins(150),
      fetchTrending(),
    ]).then(([coins, trend]) => {
      setAll(coins)
      setTrend(trend)
    }).catch(() => setError('Failed to load signals. Pull to refresh.'))
    .finally(() => setLoading(false))
  }, [])

  const trendingIds = new Set(trending.map(t => t.id))
  const trendingRankMap = {}
  trending.forEach((t, i) => { trendingRankMap[t.id] = i + 1 })

  // Build trending-only coins not already in top 150
  const topIds = new Set(allCoins.map(c => c.id))
  const trendingExtra = trending
    .filter(t => !topIds.has(t.id))
    .map(t => ({
      id: t.id,
      name: t.name,
      symbol: t.symbol,
      image: t.small || t.thumb,
      current_price: t.data?.price || 0,
      price_change_percentage_24h: parseFloat(t.data?.price_change_percentage_24h?.usd || 0),
      total_volume: 0,
      market_cap: t.data?.market_cap ? parseFloat(t.data.market_cap.replace(/[^0-9.]/g, '')) || 0 : 0,
      ath: 0,
      _trendingOnly: true,
    }))

  const combined = [...allCoins, ...trendingExtra]

  const withSig = combined.map(c => ({
    ...c,
    sig: buildSignal(c, trendingIds.has(c.id), trendingRankMap[c.id]),
  }))

  const shown = withSig.filter(c => {
    if (filter === '🚀 Buy')      return c.sig.score >= 58
    if (filter === '📉 Sell')     return c.sig.score <= 42
    if (filter === '🔥 Trending') return c.sig.isTrending
    if (filter === '🌱 Small Cap') return c.sig.isSmall
    return true
  })
  .sort((a, b) => {
    if (filter === '📉 Sell') return a.sig.score - b.sig.score
    return b.sig.score - a.sig.score
  })
  .slice(0, 60)

  const buys    = withSig.filter(c => c.sig.score >= 58).length
  const sells   = withSig.filter(c => c.sig.score <= 42).length
  const neutral = withSig.length - buys - sells

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 14 }}>
        <h2 style={{ margin: 0 }}>🎯 Signals</h2>
        <button onClick={() => { setLoading(true); setError(''); Promise.all([fetchTopCoins(150), fetchTrending()]).then(([c,t])=>{setAll(c);setTrend(t)}).catch(()=>setError('Failed')).finally(()=>setLoading(false)) }}
          style={{ background: '#1A1A1A', border: '1px solid #2A2A2A', color: '#A0A0A0', borderRadius: 8, padding: '5px 12px', cursor: 'pointer', fontSize: 12 }}>
          ↻
        </button>
      </div>

      {/* Summary */}
      {!loading && !error && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 14 }}>
          {[
            { n: buys,    label: 'Buy',     color: '#00C853' },
            { n: neutral, label: 'Neutral', color: '#A0A0A0' },
            { n: sells,   label: 'Sell',    color: '#FF3D57' },
          ].map(({ n, label, color }) => (
            <div key={label} className="card" style={{ padding: '10px 12px', textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 800, color }}>{n}</div>
              <div className="muted" style={{ fontSize: 11 }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="pills">
        {FILTERS.map(f => (
          <button key={f} className={`pill${filter === f ? ' active' : ''}`} onClick={() => { setFilter(f); setExpanded(null) }}>{f}</button>
        ))}
      </div>

      {loading && <Spinner text="Analysing signals…" />}
      {error && <div style={{ color: '#FF3D57', textAlign: 'center', padding: 24 }}>{error}</div>}

      {!loading && !error && shown.map((c, idx) => {
        const sig     = c.sig
        const isOpen  = expanded === idx
        const chg24   = c.price_change_percentage_24h || 0

        return (
          <div key={c.id} className="card" style={{ marginBottom: 10 }}
            onClick={() => setExpanded(isOpen ? null : idx)}>

            {/* Tags row */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
              {sig.isTrending && (
                <span style={{ background: '#FF6B0022', color: '#FF9944', fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5 }}>
                  🔥 Trending #{trendingRankMap[c.id]}
                </span>
              )}
              {sig.isNew && (
                <span style={{ background: '#44FF8822', color: '#44FF88', fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5 }}>
                  🌱 Small Cap
                </span>
              )}
              {c._trendingOnly && (
                <span style={{ background: '#8844FF22', color: '#AA88FF', fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 5 }}>
                  ✨ New/Emerging
                </span>
              )}
            </div>

            {/* Main row */}
            <div className="row">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {c.image && <img src={c.image} width={36} height={36} style={{ borderRadius: '50%' }} />}
                <div>
                  <strong style={{ fontSize: 15 }}>{c.symbol?.toUpperCase()}</strong>
                  <div className="muted" style={{ fontSize: 11 }}>{c.name}</div>
                  <div style={{ fontSize: 12, color: '#E0E0E0', marginTop: 1 }}>${fp(c.current_price)}</div>
                </div>
              </div>
              <div className="col" style={{ alignItems: 'flex-end', gap: 5 }}>
                <span style={{
                  background: sig.color + '22', color: sig.color,
                  padding: '4px 10px', borderRadius: 8, fontSize: 12, fontWeight: 800,
                }}>
                  {sig.icon} {sig.label}
                </span>
                <span className={`badge badge-${chg24 >= 0 ? 'green' : 'red'}`}>
                  {chg24 >= 0 ? '▲' : '▼'} {Math.abs(chg24).toFixed(2)}%
                </span>
              </div>
            </div>

            {/* Score bar */}
            <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ flex: 1, height: 4, background: '#2A2A2A', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ width: `${sig.score}%`, height: '100%', background: sig.color, borderRadius: 2 }} />
              </div>
              <span className="muted" style={{ fontSize: 10, whiteSpace: 'nowrap' }}>{sig.score}/100</span>
            </div>

            {/* Action summary */}
            <div style={{ marginTop: 6, fontSize: 12, color: sig.color, fontWeight: 600 }}>
              {sig.action}
            </div>

            {/* Expanded: WHY reasons */}
            {isOpen && sig.reasons.length > 0 && (
              <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid #242424' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#A0A0A0', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Why this signal?
                </div>
                {sig.reasons.map((r, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#C0C0C0', marginBottom: 5, lineHeight: 1.5 }}>
                    {r}
                  </div>
                ))}
                {c.market_cap > 0 && (
                  <div style={{ marginTop: 8, fontSize: 11, color: '#606060' }}>
                    Market cap: {fmcap(c.market_cap)} · Vol: {fmcap(c.total_volume)}
                  </div>
                )}
                <div style={{ marginTop: 8, fontSize: 10, color: '#505050' }}>
                  ⚠️ Not financial advice. Always do your own research.
                </div>
              </div>
            )}

            <div style={{ textAlign: 'center', marginTop: 8 }}>
              <span className="muted" style={{ fontSize: 10 }}>{isOpen ? '▲ less' : '▼ see why'}</span>
            </div>
          </div>
        )
      })}

      {!loading && !error && shown.length === 0 && (
        <div style={{ textAlign: 'center', color: '#606060', padding: '40px 0' }}>
          No signals match this filter right now.
        </div>
      )}
    </div>
  )
}
