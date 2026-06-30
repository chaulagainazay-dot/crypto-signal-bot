import { useState, useEffect } from 'react'
import { searchCoins, fetchCoinDetail, fetchOHLC, fetchCryptoNews, fetchByContract, fp, fmcap } from '../api/coingecko'
import { isContractAddress } from '../utils/formatters'
import { Spinner, ChipRow, EmptyState, ProgressBar, Tag } from '../components/ui'
import type { NewsArticle } from '../types'

type Section = 'overview' | 'chart' | 'news'
const SECTIONS: { value: Section; label: string }[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'chart',    label: 'Chart'    },
  { value: 'news',     label: 'News'     },
]

function OHLCChart({ data }: { data: number[][] }) {
  if (!data || data.length < 2) return null
  const W = 320, H = 140, PAD = 8
  const highs = data.map(d => d[2]), lows = data.map(d => d[3])
  const minP = Math.min(...lows), maxP = Math.max(...highs)
  const range = maxP - minP || 1
  const cw = (W - PAD * 2) / data.length - 2
  function y(p: number) { return H - PAD - ((p - minP) / range) * (H - PAD * 2) }
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
      {data.map((d, i) => {
        const x = PAD + i * ((W - PAD * 2) / data.length) + cw / 2
        const [, open, high, low, close] = d
        const bull  = close >= open
        const color = bull ? '#22C55E' : '#EF4444'
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
  if (p > n) return { cls: 'badge-buy', label: 'Bullish', color: 'var(--green)' }
  if (n > p) return { cls: 'badge-sell', label: 'Bearish', color: 'var(--red)' }
  return { cls: 'badge-hold', label: 'Neutral', color: 'var(--text2)' }
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
  const [section, setSection] = useState<Section>('overview')

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
    const [d, o, n] = await Promise.all([fetchCoinDetail(id), fetchOHLC(id, 30), fetchCryptoNews(id.toUpperCase(), 8)])
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

  const md     = detail && (detail as { market_data?: Record<string, unknown> }).market_data as Record<string, unknown> | undefined
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
    if (score >= 68) return { label: 'BUY', color: 'var(--green)', cls: 'badge-buy' }
    if (score >= 55) return { label: 'WATCH', color: 'var(--accent)', cls: 'badge-hold' }
    if (score >= 42) return { label: 'HOLD', color: '#EAB308', cls: 'badge-hold' }
    return { label: 'SELL', color: 'var(--red)', cls: 'badge-sell' }
  })()

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 16 }}>
        <h1 className="page-title">Research</h1>
      </div>

      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            placeholder="Coin name or contract address…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
          />
          {searching && <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 12, color: 'var(--text3)' }}>…</div>}
        </div>
        <button className="btn" onClick={handleSearch} style={{ width: 'auto', padding: '0 18px', marginTop: 0 }}>Go</button>
      </div>

      {/* Search dropdown */}
      {results.length > 0 && (
        <div style={{ background: 'var(--surface2)', borderRadius: 10, marginBottom: 12, border: '1px solid var(--border)', maxHeight: 200, overflowY: 'auto' }}>
          {results.map(r => (
            <div key={r.id} onClick={() => { setCoinId(r.id); setQuery(r.name); setResults([]) }}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', cursor: 'pointer', borderBottom: '1px solid var(--border2)' }}>
              {r.thumb && <img src={r.thumb} style={{ width: 24, height: 24, borderRadius: '50%' }} />}
              <span style={{ flex: 1, fontSize: 13 }}>{r.name}</span>
              <span className="muted" style={{ fontSize: 11 }}>{r.symbol?.toUpperCase()}</span>
            </div>
          ))}
        </div>
      )}

      {loading && <Spinner />}

      {!detail && !loading && (
        <EmptyState icon="🔍" title="Search any coin"
          sub={"Enter a name to get price, chart, and news.\nOr paste a contract address for DEX tokens."} />
      )}

      {detail && !loading && (
        <>
          {/* Coin header card */}
          <div className="card" style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              {image && <img src={image} style={{ width: 48, height: 48, borderRadius: '50%' }} />}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 800, fontSize: 18 }}>{symbol}</div>
                <div className="muted" style={{ fontSize: 13 }}>{name}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 800, fontSize: 18 }}>{price > 0 ? `$${fp(price)}` : '—'}</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: chg24 >= 0 ? 'var(--green)' : 'var(--red)' }}>
                  {chg24 >= 0 ? '+' : ''}{chg24.toFixed(2)}%
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <span className={`badge ${signal.cls}`}>{signal.label}</span>
              {ath > 0 && price > 0 && (
                <span className="badge badge-blue">
                  {((price / ath) * 100).toFixed(0)}% of ATH
                </span>
              )}
            </div>

            <div className="stat-grid-2">
              {[
                { label: 'Market Cap',    value: fmcap(mcap) },
                { label: '24h Volume',    value: fmcap(vol)  },
                { label: 'All-Time High', value: ath > 0 ? `$${fp(ath)}` : '—' },
                { label: 'ATH Distance',  value: ath > 0 ? `${(((price - ath) / ath) * 100).toFixed(1)}%` : '—', color: 'var(--red)' },
              ].map(({ label, value, color }) => (
                <div key={label} className="stat-box">
                  <div className="label">{label}</div>
                  <div className="value" style={color ? { color } : undefined}>{value}</div>
                </div>
              ))}
            </div>

            {/* Vol/Cap ratio bar */}
            {mcap > 0 && vol > 0 && (
              <div style={{ marginTop: 12 }}>
                <div className="row" style={{ marginBottom: 4 }}>
                  <span style={{ fontSize: 10, color: 'var(--text3)' }}>Volume / Market Cap</span>
                  <span style={{ fontSize: 10, color: 'var(--text2)' }}>{((vol / mcap) * 100).toFixed(1)}%</span>
                </div>
                <ProgressBar pct={(vol / mcap) * 100} color="var(--accent)" height={3} />
              </div>
            )}
          </div>

          <ChipRow options={SECTIONS} active={section} onChange={setSection} />

          {section === 'overview' && desc && (
            <div className="card">
              <div className="section-label">About {name}</div>
              <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.7 }}>
                {desc.replace(/<[^>]*>/g, '').slice(0, 500)}{desc.length > 500 ? '…' : ''}
              </p>
            </div>
          )}

          {section === 'chart' && (
            <div className="card">
              <div className="section-label">30-Day Candles</div>
              {ohlc.length > 0 ? <OHLCChart data={ohlc} /> : <EmptyState icon="📈" title="No chart data" />}
            </div>
          )}

          {section === 'news' && (
            <>
              {news.length === 0 && <EmptyState icon="📰" title={`No news for ${symbol}`} />}
              {news.map((art, i) => {
                const s = newsSentiment(art.title)
                return (
                  <a key={i} href={art.url} target="_blank" rel="noreferrer" className="news-card">
                    <div className="card" style={{ borderLeft: `3px solid ${s.color}`, marginBottom: 8 }}>
                      <div className="row" style={{ marginBottom: 6 }}>
                        <span className={`badge ${s.cls}`}>{s.label}</span>
                        <span className="muted" style={{ fontSize: 10 }}>{new Date(art.published_on * 1000).toLocaleDateString()}</span>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.5 }}>{art.title}</div>
                      <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text3)' }}>{art.source_info?.name || art.source} ↗</div>
                    </div>
                  </a>
                )
              })}
            </>
          )}
        </>
      )}
    </div>
  )
}
