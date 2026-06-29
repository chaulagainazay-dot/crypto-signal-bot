import { useState, useEffect } from 'react'
import { searchCoins, fetchCoinDetail, fetchOHLC, fetchCryptoNews, fetchByContract, fp, fmcap } from '../api/coingecko'
import { isContractAddress } from '../utils/formatters'
import Spinner from '../components/Spinner'
import type { NewsArticle } from '../types'

function OHLCChart({ data }: { data: number[][] }) {
  if (!data || data.length < 2) return null
  const W = 320, H = 140, PAD = 8
  const highs  = data.map(d => d[2])
  const lows   = data.map(d => d[3])
  const minP   = Math.min(...lows)
  const maxP   = Math.max(...highs)
  const range  = maxP - minP || 1
  const cw     = (W - PAD * 2) / data.length - 2

  function y(p: number) { return H - PAD - ((p - minP) / range) * (H - PAD * 2) }

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
      {data.map((d, i) => {
        const x    = PAD + i * ((W - PAD * 2) / data.length) + cw / 2
        const open = d[1], close = d[4], high = d[2], low = d[3]
        const bull  = close >= open
        const color = bull ? '#00C853' : '#FF3D57'
        const bodyT = y(Math.max(open, close))
        const bodyH = Math.max(2, Math.abs(y(open) - y(close)))
        return (
          <g key={i}>
            <line x1={x} y1={y(high)} x2={x} y2={y(low)} stroke={color} strokeWidth={1} />
            <rect x={x - cw / 2} y={bodyT} width={cw} height={bodyH} fill={color} rx={1} />
          </g>
        )
      })}
    </svg>
  )
}

function newsSentiment(title: string) {
  const t = title.toLowerCase()
  const p = ['surge','rally','bullish','pump','gain','rise','ath','launch','etf','approval'].filter(w => t.includes(w)).length
  const n = ['crash','drop','bear','dump','ban','hack','fraud','fall','plunge','lawsuit'].filter(w => t.includes(w)).length
  if (p > n) return { label: '🟢 Bullish', color: '#00C853' }
  if (n > p) return { label: '🔴 Bearish', color: '#FF3D57' }
  return { label: '⚪ Neutral', color: '#808080' }
}

export default function Research({ initialCoinId }: { initialCoinId?: string | null }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Array<{ id: string; name: string; symbol: string; thumb?: string }>>([])
  const [searching, setSearching] = useState(false)
  const [coinId, setCoinId] = useState(initialCoinId || '')
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [ohlc, setOhlc] = useState<number[][]>([])
  const [news, setNews] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(false)
  const [section, setSection] = useState<'overview' | 'chart' | 'news'>('overview')

  useEffect(() => {
    if (!query.trim() || isContractAddress(query)) { setResults([]); return }
    const t = setTimeout(async () => {
      setSearching(true)
      const r = await searchCoins(query).catch(() => [])
      setResults(r as typeof results)
      setSearching(false)
    }, 400)
    return () => clearTimeout(t)
  }, [query])

  async function loadCoin(id: string) {
    setLoading(true); setDetail(null); setOhlc([]); setNews([])
    const [d, o, n] = await Promise.all([
      fetchCoinDetail(id),
      fetchOHLC(id, 30),
      fetchCryptoNews(id.toUpperCase(), 8),
    ])
    setDetail(d as Record<string, unknown>)
    setOhlc(o)
    setNews(n)
    setLoading(false)
  }

  useEffect(() => { if (coinId) loadCoin(coinId) }, [coinId])

  async function handleSearch() {
    const q = query.trim()
    if (!q) return
    if (isContractAddress(q)) {
      setLoading(true)
      const token = await fetchByContract(q).catch(() => null) as Record<string, unknown> | null
      if (token) setDetail({ _contractResult: true, ...token })
      setLoading(false)
      return
    }
    if (results.length > 0) { setCoinId(results[0].id); setResults([]); setQuery(results[0].name) }
  }

  const md = detail && (detail as { market_data?: Record<string, unknown> }).market_data as Record<string, unknown> | undefined
  const price  = (md?.current_price as { usd?: number })?.usd ?? 0
  const chg24  = (md?.price_change_percentage_24h as number) ?? 0
  const mcap   = (md?.market_cap as { usd?: number })?.usd ?? 0
  const vol    = (md?.total_volume as { usd?: number })?.usd ?? 0
  const ath    = (md?.ath as { usd?: number })?.usd ?? 0
  const symbol = (detail?.symbol as string ?? '').toUpperCase()
  const name   = (detail?.name as string) ?? ''
  const desc   = (detail?.description as { en?: string })?.en ?? ''
  const image  = (detail?.image as { large?: string })?.large ?? ''

  const signal = (() => {
    const vr = vol / (mcap || 1)
    let score = 50
    if (chg24 > 8) score += 18; else if (chg24 > 3) score += 8
    else if (chg24 < -8) score -= 18; else if (chg24 < -3) score -= 8
    if (vr > 0.2) score += 10; else if (vr > 0.08) score += 5
    score = Math.max(0, Math.min(100, score))
    if (score >= 68) return { label: 'BUY', color: '#00C853' }
    if (score >= 55) return { label: 'WATCH', color: '#F7931A' }
    if (score >= 42) return { label: 'HOLD', color: '#FFD700' }
    return { label: 'SELL', color: '#FF3D57' }
  })()

  return (
    <div className="tab-content">
      <h2>🔍 Research</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            placeholder="Search coin or paste contract address…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
          {searching && <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 12, color: '#606060' }}>…</div>}
        </div>
        <button onClick={handleSearch} className="btn" style={{ width: 'auto', padding: '0 16px', marginTop: 0 }}>Go</button>
      </div>

      {results.length > 0 && (
        <div style={{ background: '#141414', borderRadius: 10, marginBottom: 12, border: '1px solid #2A2A2A', maxHeight: 200, overflowY: 'auto' }}>
          {results.map(r => (
            <div key={r.id} onClick={() => { setCoinId(r.id); setQuery(r.name); setResults([]) }}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', cursor: 'pointer', borderBottom: '1px solid #1E1E1E' }}>
              {r.thumb && <img src={r.thumb} width={24} height={24} style={{ borderRadius: '50%' }} />}
              <span style={{ flex: 1, fontSize: 13 }}>{r.name}</span>
              <span className="muted" style={{ fontSize: 11 }}>{r.symbol?.toUpperCase()}</span>
            </div>
          ))}
        </div>
      )}

      {loading && <Spinner text="Loading coin data…" />}

      {detail && !loading && (
        <>
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              {image && <img src={image} width={48} height={48} style={{ borderRadius: '50%' }} />}
              <div style={{ flex: 1 }}>
                <strong style={{ fontSize: 18 }}>{symbol}</strong>
                <div className="muted" style={{ fontSize: 13 }}>{name}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 800, fontSize: 18 }}>{price > 0 ? `$${fp(price)}` : '—'}</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: chg24 >= 0 ? '#00C853' : '#FF3D57' }}>
                  {chg24 >= 0 ? '▲' : '▼'}{Math.abs(chg24).toFixed(2)}%
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
              <span style={{ background: signal.color + '22', color: signal.color, padding: '4px 12px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                {signal.label}
              </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                { label: 'Market Cap',   val: fmcap(mcap) },
                { label: '24h Volume',   val: fmcap(vol) },
                { label: 'All-Time High', val: ath > 0 ? `$${fp(ath)}` : '—' },
                { label: 'ATH Distance', val: ath > 0 ? `${(((price - ath) / ath) * 100).toFixed(1)}%` : '—' },
              ].map(({ label, val }) => (
                <div key={label} style={{ padding: '8px 10px', background: '#141414', borderRadius: 8 }}>
                  <div className="muted" style={{ fontSize: 9, marginBottom: 2 }}>{label}</div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{val}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="pills" style={{ marginBottom: 12 }}>
            {(['overview', 'chart', 'news'] as const).map(s => (
              <button key={s} className={`pill${section === s ? ' active' : ''}`} onClick={() => setSection(s)}>
                {{ overview: '📋 Overview', chart: '📈 Chart', news: '📰 News' }[s]}
              </button>
            ))}
          </div>

          {section === 'overview' && desc && (
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>About</div>
              <p style={{ fontSize: 13, color: '#C0C0C0', lineHeight: 1.7 }}>
                {desc.replace(/<[^>]*>/g, '').slice(0, 500)}{desc.length > 500 ? '…' : ''}
              </p>
            </div>
          )}

          {section === 'chart' && (
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>30-Day Candles</div>
              {ohlc.length > 0 ? <OHLCChart data={ohlc} /> : <div className="muted" style={{ fontSize: 12, padding: '20px 0', textAlign: 'center' }}>No chart data</div>}
            </div>
          )}

          {section === 'news' && (
            <>
              {news.length === 0 && <div className="muted" style={{ textAlign: 'center', padding: '32px 0' }}>No news found for {symbol}.</div>}
              {news.map((art, i) => {
                const s = newsSentiment(art.title)
                return (
                  <a key={i} href={art.url} target="_blank" rel="noreferrer" style={{ display: 'block', textDecoration: 'none', marginBottom: 8 }}>
                    <div className="card" style={{ borderLeft: `3px solid ${s.color}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: s.color }}>{s.label}</span>
                        <span className="muted" style={{ fontSize: 10 }}>{new Date(art.published_on * 1000).toLocaleDateString()}</span>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#E0E0E0', lineHeight: 1.5 }}>{art.title}</div>
                      <div style={{ marginTop: 4, fontSize: 10, color: '#444' }}>{art.source_info?.name || art.source} ↗</div>
                    </div>
                  </a>
                )
              })}
            </>
          )}
        </>
      )}

      {!detail && !loading && (
        <div style={{ textAlign: 'center', color: '#404040', padding: '60px 20px', lineHeight: 2 }}>
          Search any coin by name<br />or paste a contract address<br />for DEX tokens
        </div>
      )}
    </div>
  )
}
