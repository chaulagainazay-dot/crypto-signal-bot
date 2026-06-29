import { useState, useEffect } from 'react'
import {
  fetchCoinDetail, fetchOHLC, fetchCryptoNews, searchCoins,
  fetchByContract, fp, fmcap, isAddress, computeSignal,
} from '../api/coingecko'
import Spinner from '../components/Spinner'
import CandlestickChart from '../components/CandlestickChart'

// ─── helpers ────────────────────────────────────────────────────────────────

function pct(v) {
  const n = parseFloat(v) || 0
  return (
    <span className={`badge badge-${n >= 0 ? 'green' : 'red'}`}>
      {n >= 0 ? '▲' : '▼'} {Math.abs(n).toFixed(2)}%
    </span>
  )
}

function Row({ label, value, sub }) {
  return (
    <div className="row" style={{ padding: '8px 0', borderBottom: '1px solid #1E1E1E' }}>
      <span className="muted" style={{ fontSize: 13 }}>{label}</span>
      <div style={{ textAlign: 'right' }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>{value}</span>
        {sub && <div className="muted" style={{ fontSize: 11 }}>{sub}</div>}
      </div>
    </div>
  )
}

const OHLC_DAYS = [
  { label: '1d', days: 1 },
  { label: '7d', days: 7 },
  { label: '14d', days: 14 },
  { label: '30d', days: 30 },
]

const TOP_EXCHANGES = [
  'Binance', 'Coinbase', 'Kraken', 'OKX', 'Bybit', 'KuCoin', 'Gate.io', 'Huobi',
]

function timeAgo(ts) {
  const s = Math.floor((Date.now() / 1000) - ts)
  if (s < 60)   return `${s}s ago`
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  if (s < 86400) return `${Math.floor(s/3600)}h ago`
  return `${Math.floor(s/86400)}d ago`
}

// ─── News section ────────────────────────────────────────────────────────────

function NewsSection({ symbol }) {
  const [news,    setNews]    = useState([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExp]    = useState(null)

  useEffect(() => {
    fetchCryptoNews(symbol).then(setNews).catch(() => {}).finally(() => setLoading(false))
  }, [symbol])

  if (loading) return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="section-title" style={{ marginTop: 0 }}>📰 Latest News</div>
      <div className="muted" style={{ fontSize: 13, padding: '8px 0' }}>Loading news…</div>
    </div>
  )

  if (news.length === 0) return null

  const SENTIMENT = art => {
    const t = (art.title + ' ' + (art.body || '')).toLowerCase()
    const pos = ['surge', 'bullish', 'rally', 'gain', 'pump', 'launch', 'partnership', 'adoption', 'record', 'high', 'growth', 'buy']
    const neg = ['crash', 'bearish', 'plunge', 'hack', 'scam', 'ban', 'drop', 'fear', 'sell', 'loss', 'warning', 'risk']
    const ps = pos.filter(w => t.includes(w)).length
    const ns = neg.filter(w => t.includes(w)).length
    if (ps > ns) return { label: '🟢 Bullish', color: '#00C853' }
    if (ns > ps) return { label: '🔴 Bearish', color: '#FF3D57' }
    return { label: '⚪ Neutral', color: '#A0A0A0' }
  }

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="section-title" style={{ marginTop: 0 }}>📰 Latest News</div>
      {news.map((art, i) => {
        const sent = SENTIMENT(art)
        const isOpen = expanded === i
        return (
          <div key={i} style={{ borderBottom: '1px solid #1E1E1E', paddingBottom: 10, marginBottom: 10 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              {art.imageurl && (
                <img src={art.imageurl} alt="" width={48} height={48}
                  style={{ borderRadius: 6, objectFit: 'cover', flexShrink: 0 }} />
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.4, marginBottom: 4 }}>
                  {art.title}
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 10, color: sent.color, fontWeight: 700 }}>{sent.label}</span>
                  <span className="muted" style={{ fontSize: 10 }}>{art.source_info?.name || art.source}</span>
                  <span className="muted" style={{ fontSize: 10 }}>{timeAgo(art.published_on)}</span>
                </div>
              </div>
            </div>

            {isOpen && art.body && (
              <p style={{ marginTop: 8, fontSize: 12, color: '#C0C0C0', lineHeight: 1.6 }}>
                {art.body.slice(0, 300)}…
              </p>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
              <button onClick={() => setExp(isOpen ? null : i)} style={{
                background: 'none', border: 'none', color: '#F7931A',
                cursor: 'pointer', fontSize: 11, padding: 0,
              }}>
                {isOpen ? '▲ Less' : '▼ Read more'}
              </button>
              <a href={art.url} target="_blank" rel="noreferrer" style={{
                color: '#6090FF', fontSize: 11, textDecoration: 'none',
              }}>↗ Full article</a>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Beginner tips ────────────────────────────────────────────────────────────

function BeginnerTips() {
  const [open, setOpen] = useState(false)
  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: '3px solid #F7931A' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        background: 'none', border: 'none', color: '#F7931A',
        cursor: 'pointer', fontWeight: 700, fontSize: 14, padding: 0, width: '100%', textAlign: 'left',
      }}>
        💡 Beginner Trading Tips {open ? '▲' : '▼'}
      </button>
      {open && (
        <ul style={{ margin: '12px 0 0', padding: '0 0 0 16px', color: '#C0C0C0', fontSize: 13, lineHeight: 1.8 }}>
          <li><strong>Never invest more than you can afford to lose.</strong></li>
          <li><strong>DCA (Dollar-Cost Average)</strong> — buy small amounts regularly, not all at once.</li>
          <li>Set a <strong>stop-loss at 10–15%</strong> below your entry to limit losses.</li>
          <li>Green candle = price went UP that period. Red candle = price went DOWN.</li>
          <li>Long wick below a candle = buyers pushed price back up — bullish sign.</li>
          <li>High volume + price rise = strong move. Low volume rise = weak, may reverse.</li>
          <li><strong>Market cap matters more than price</strong> — a $0.001 coin can still be overpriced.</li>
          <li>Never buy based on hype alone. Check the project's website and use case.</li>
        </ul>
      )}
    </div>
  )
}

// ─── GeckoTerminal fallback detail view ──────────────────────────────────────

function GTDetailView({ data, onBack }) {
  const { _attrs: a, _network: net } = data
  const price = parseFloat(a.price_usd || 0)
  const chg24 = parseFloat(a.price_change_percentage?.h24 || 0)
  const vol24 = parseFloat(a.volume_usd?.h24 || 0)
  const fdv   = parseFloat(a.fdv_usd || 0)
  const mcap  = parseFloat(a.market_cap_usd || 0)

  const sig = (() => {
    const vr = vol24 / (mcap || fdv || 1)
    if (chg24 > 10 && vr > 0.2) return { label: 'STRONG BUY',  color: '#00E676', icon: '🚀', score: 80, advice: 'Strong upward momentum. Volume is high.' }
    if (chg24 > 4  && vr > 0.1) return { label: 'BUY',         color: '#00C853', icon: '📈', score: 65, advice: 'Positive trend. Consider a small position.' }
    if (chg24 < -10 && vr > 0.2) return { label: 'STRONG SELL', color: '#FF1744', icon: '🔥', score: 15, advice: 'Heavy selling. Avoid buying now.' }
    if (chg24 < -4 && vr > 0.1) return { label: 'SELL',        color: '#FF3D57', icon: '📉', score: 30, advice: 'Downward pressure. Be careful.' }
    return { label: 'NEUTRAL', color: '#F7931A', icon: '➡️', score: 50, advice: 'Mixed signals. Wait for clearer direction.' }
  })()

  const sym = (a.symbol || 'TOKEN').toUpperCase()

  return (
    <div className="tab-content">
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#F7931A', cursor: 'pointer', padding: '0 0 12px', fontSize: 14 }}>← Back</button>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        {a.image_url && <img src={a.image_url} width={48} height={48} style={{ borderRadius: '50%' }} />}
        <div>
          <h2 style={{ margin: 0 }}>{a.name} <span style={{ color: '#606060', fontWeight: 400, fontSize: 14 }}>({sym})</span></h2>
          <div className="muted">via GeckoTerminal · {net}</div>
        </div>
      </div>
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 28, fontWeight: 900 }}>${fp(price)}</div>
        <div style={{ marginTop: 4, display: 'flex', gap: 8 }}>{pct(chg24)} <span className="muted" style={{ fontSize: 12 }}>24h</span></div>
      </div>
      <div className="card" style={{ marginBottom: 12, borderLeft: `3px solid ${sig.color}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 24 }}>{sig.icon}</span>
          <span style={{ fontWeight: 800, color: sig.color, fontSize: 18 }}>{sig.label}</span>
          <div style={{ flex: 1, height: 6, background: '#2A2A2A', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{ width: `${sig.score}%`, height: '100%', background: sig.color, borderRadius: 3 }} />
          </div>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: '#C0C0C0', lineHeight: 1.5 }}>{sig.advice}</p>
        <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>⚠️ Not financial advice. Always DYOR.</div>
      </div>
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>Key Metrics</div>
        {vol24 > 0 && <Row label="24h Volume" value={fmcap(vol24)} />}
        {fdv   > 0 && <Row label="FDV"        value={fmcap(fdv)} />}
        {mcap  > 0 && <Row label="Market Cap" value={fmcap(mcap)} />}
      </div>
      <NewsSection symbol={sym} />
      <BeginnerTips />
    </div>
  )
}

// ─── Full CoinGecko detail view ───────────────────────────────────────────────

function CoinDetailView({ data, onBack }) {
  const [chartDays,    setChartDays]    = useState(7)
  const [candles,      setCandles]      = useState([])
  const [chartLoading, setChartLoading] = useState(true)

  const md    = data.market_data
  const price = md?.current_price?.usd || 0
  const chg24 = md?.price_change_percentage_24h || 0
  const chg7d = md?.price_change_percentage_7d  || 0
  const chg30 = md?.price_change_percentage_30d || 0
  const ath   = md?.ath?.usd || 0
  const atl   = md?.atl?.usd || 0
  const athPct = md?.ath_change_percentage?.usd || 0
  const mcap  = md?.market_cap?.usd || 0
  const vol24 = md?.total_volume?.usd || 0
  const supply = md?.circulating_supply || 0
  const maxSup = md?.max_supply
  const fdv    = md?.fully_diluted_valuation?.usd || 0

  const sig = computeSignal(md)

  const tickers = (data.tickers || [])
    .filter(t => TOP_EXCHANGES.includes(t.market?.name) && t.converted_last?.usd)

  const uniqueTickers = tickers
    .filter((t, i, arr) => arr.findIndex(x => x.market?.name === t.market?.name) === i)
    .slice(0, 5)

  const buyZoneLow  = price * 0.93
  const buyZoneHigh = price * 0.99

  const website = data.links?.homepage?.[0]
  const explorer = data.links?.blockchain_site?.[0]
  const reddit   = data.links?.subreddit_url
  const twitter  = data.links?.twitter_screen_name

  const desc = data.description?.en
    ?.replace(/<[^>]*>/g, '')
    ?.replace(/\s+/g, ' ')
    ?.trim()
    ?.slice(0, 400)

  async function loadChart(days) {
    setChartDays(days); setChartLoading(true)
    try {
      const d = await fetchOHLC(data.id, days)
      setCandles(d)
    } catch { setCandles([]) }
    setChartLoading(false)
  }

  useEffect(() => { loadChart(chartDays) }, [])

  return (
    <div className="tab-content">
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#F7931A', cursor: 'pointer', padding: '0 0 12px', fontSize: 14 }}>← Back</button>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        {data.image?.large && <img src={data.image.large} width={52} height={52} style={{ borderRadius: '50%' }} />}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>{data.name}</h2>
            <span style={{ color: '#606060', fontWeight: 400, fontSize: 13 }}>{data.symbol?.toUpperCase()}</span>
          </div>
          {data.market_cap_rank && <div className="muted">Rank #{data.market_cap_rank}</div>}
        </div>
      </div>

      {/* Price + changes */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 30, fontWeight: 900, marginBottom: 8 }}>${fp(price)}</div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{pct(chg24)}<span className="muted" style={{ fontSize: 11 }}>24h</span></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{pct(chg7d)}<span className="muted" style={{ fontSize: 11 }}>7d</span></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{pct(chg30)}<span className="muted" style={{ fontSize: 11 }}>30d</span></div>
        </div>
      </div>

      {/* BUY / SELL SIGNAL */}
      {sig && (
        <div className="card" style={{ marginBottom: 12, borderLeft: `4px solid ${sig.color}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <span style={{ fontSize: 26 }}>{sig.icon}</span>
            <div>
              <div style={{ fontWeight: 800, color: sig.color, fontSize: 18 }}>{sig.label}</div>
              <div className="muted" style={{ fontSize: 11 }}>Signal strength: {sig.score}/100</div>
            </div>
            <div style={{ flex: 1, height: 6, background: '#2A2A2A', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${sig.score}%`, height: '100%', background: sig.color, borderRadius: 3 }} />
            </div>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: '#C0C0C0', lineHeight: 1.6 }}>{sig.advice}</p>
          <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>⚠️ Not financial advice. Always DYOR.</div>
        </div>
      )}

      {/* Candlestick chart */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>📊 Price Chart</span>
          <div style={{ display: 'flex', gap: 4 }}>
            {OHLC_DAYS.map(d => (
              <button key={d.days} onClick={() => loadChart(d.days)} style={{
                background: chartDays === d.days ? '#F7931A' : '#2A2A2A',
                color: chartDays === d.days ? '#000' : '#A0A0A0',
                border: 'none', borderRadius: 6, padding: '3px 8px',
                cursor: 'pointer', fontSize: 11, fontWeight: 700,
              }}>{d.label}</button>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
          <span style={{ fontSize: 10, color: '#00C853' }}>▬ Bullish candle (price went up)</span>
          <span style={{ fontSize: 10, color: '#FF3D57' }}>▬ Bearish candle (price went down)</span>
        </div>

        {chartLoading
          ? <div style={{ height: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="muted" style={{ fontSize: 12 }}>Loading chart…</span>
            </div>
          : candles.length > 0
            ? <CandlestickChart candles={candles} signal={sig} />
            : <div className="muted" style={{ textAlign: 'center', padding: 16, fontSize: 12 }}>Chart unavailable</div>
        }
      </div>

      {/* Where to buy */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>🏦 Where to Buy</div>
        {uniqueTickers.length > 0 ? (
          uniqueTickers.map(t => (
            <div key={t.market?.name} className="row" style={{ padding: '7px 0', borderBottom: '1px solid #1E1E1E' }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{t.market?.name}</span>
              <span style={{ fontSize: 13, color: '#A0A0A0' }}>${fp(t.converted_last?.usd)}</span>
            </div>
          ))
        ) : (
          <div className="muted" style={{ fontSize: 13 }}>Binance · Coinbase · Kraken · OKX · Bybit</div>
        )}
        <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>
          💡 For beginners: Binance and Coinbase are easiest to start with.
        </div>
      </div>

      {/* Price levels */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>📍 Price Levels</div>
        <Row label="Current Price"     value={`$${fp(price)}`} />
        <Row label="🔴 Resistance (ATH)" value={`$${fp(ath)}`}  sub="All-time high — strong selling zone" />
        <Row label="🟢 Support (ATL)"    value={`$${fp(atl)}`}  sub="All-time low — strong buying zone" />
        <Row label="📉 Below ATH"         value={`${Math.abs(athPct).toFixed(1)}% below peak`} />
        <div style={{ marginTop: 10, padding: '10px 12px', background: '#1A2A1A', borderRadius: 8 }}>
          <div style={{ fontSize: 12, color: '#00C853', fontWeight: 700, marginBottom: 4 }}>💡 DCA Buy Zone Suggestion</div>
          <div className="muted" style={{ fontSize: 12 }}>
            Consider spreading buys between{' '}
            <strong style={{ color: '#E0E0E0' }}>${fp(buyZoneLow)}</strong>–<strong style={{ color: '#E0E0E0' }}>${fp(buyZoneHigh)}</strong>{' '}
            in small portions over time.
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>📊 Key Metrics</div>
        <Row label="Market Cap"         value={fmcap(mcap)}   sub="Total value of all coins in circulation" />
        <Row label="24h Volume"         value={fmcap(vol24)}  sub="How much was traded today" />
        {fdv > 0 && <Row label="Fully Diluted Value" value={fmcap(fdv)} sub="If all coins were circulating" />}
        <Row label="Circulating Supply" value={fmcap(supply)} sub="Coins currently in the market" />
        {maxSup && <Row label="Max Supply" value={fmcap(maxSup)} sub="Total coins that will ever exist" />}
        {mcap > 0 && vol24 > 0 && (
          <Row label="Vol / MCap" value={`${((vol24/mcap)*100).toFixed(2)}%`} sub=">10% means lots of trading activity" />
        )}
      </div>

      {/* About */}
      {desc && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="section-title" style={{ marginTop: 0 }}>📖 About {data.name}</div>
          <p style={{ margin: 0, fontSize: 13, color: '#C0C0C0', lineHeight: 1.7 }}>{desc}…</p>
        </div>
      )}

      {/* News */}
      <NewsSection symbol={data.symbol?.toUpperCase()} />

      {/* Links */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>🔗 Links</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          {website  && <a href={website}  target="_blank" rel="noreferrer" style={linkStyle}>🌐 Website</a>}
          {explorer && <a href={explorer} target="_blank" rel="noreferrer" style={linkStyle}>🔍 Explorer</a>}
          {reddit   && <a href={reddit}   target="_blank" rel="noreferrer" style={linkStyle}>📣 Reddit</a>}
          {twitter  && <a href={`https://x.com/${twitter}`} target="_blank" rel="noreferrer" style={linkStyle}>🐦 Twitter</a>}
          <a href={`https://www.coingecko.com/en/coins/${data.id}`} target="_blank" rel="noreferrer" style={linkStyle}>📰 CoinGecko</a>
          <a href={`https://coinmarketcap.com/currencies/${data.id}`} target="_blank" rel="noreferrer" style={{ ...linkStyle, background: '#1A2030' }}>📊 CMC</a>
        </div>
      </div>

      <BeginnerTips />
    </div>
  )
}

const linkStyle = {
  background: '#1A1A2A', color: '#A0C0FF',
  padding: '6px 12px', borderRadius: 8,
  fontSize: 12, textDecoration: 'none', fontWeight: 600,
}

// ─── Search screen ─────────────────────────────────────────────────────────

export default function Research({ initialCoinId }) {
  const [query,   setQuery]   = useState(initialCoinId || '')
  const [results, setRes]     = useState([])
  const [detail,  setDetail]  = useState(null)
  const [loading, setLoad]    = useState(false)
  const [error,   setErr]     = useState('')

  async function search() {
    if (!query.trim()) return
    setLoad(true); setErr(''); setRes([])
    try {
      if (isAddress(query.trim())) {
        const d = await fetchByContract(query.trim())
        if (d) { setDetail(d); setLoad(false); return }
        setErr('Contract not found on any supported chain.')
      } else {
        const r = await searchCoins(query.trim())
        if (r.length === 0) setErr('No results. Try the full name (e.g. "Bitcoin").')
        setRes(r)
      }
    } catch { setErr('Search failed. Check your connection.') }
    setLoad(false)
  }

  async function openCoin(id) {
    setLoad(true); setErr('')
    try {
      const d = await fetchCoinDetail(id)
      setDetail(d)
    } catch { setErr('Failed to load. Try again.') }
    setLoad(false)
  }

  if (detail) {
    if (detail._geckoterminal) return <GTDetailView data={detail} onBack={() => setDetail(null)} />
    return <CoinDetailView data={detail} onBack={() => setDetail(null)} />
  }

  const POPULAR = [
    { id: 'bitcoin',     name: 'Bitcoin',  sym: 'BTC', thumb: 'https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png' },
    { id: 'ethereum',    name: 'Ethereum', sym: 'ETH', thumb: 'https://assets.coingecko.com/coins/images/279/thumb/ethereum.png' },
    { id: 'solana',      name: 'Solana',   sym: 'SOL', thumb: 'https://assets.coingecko.com/coins/images/4128/thumb/solana.png' },
    { id: 'binancecoin', name: 'BNB',      sym: 'BNB', thumb: 'https://assets.coingecko.com/coins/images/825/thumb/bnb-icon2_2x.png' },
    { id: 'ripple',      name: 'XRP',      sym: 'XRP', thumb: 'https://assets.coingecko.com/coins/images/44/thumb/xrp-symbol-white-128.png' },
  ]

  return (
    <div className="tab-content">
      <h2>🔍 Research</h2>
      <p className="muted" style={{ fontSize: 12, marginTop: -8, marginBottom: 12 }}>
        Search any coin, token, or paste a contract address (0x…)
      </p>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          placeholder="Bitcoin, BTC, ETH, or 0x…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          style={{ flex: 1 }}
        />
        <button className="btn" onClick={search}
          style={{ width: 'auto', padding: '0 18px', flex: 'none' }}>Go</button>
      </div>

      {loading && <Spinner text="Searching…" />}
      {error && <div style={{ color: '#FF3D57', textAlign: 'center', padding: '24px 0', fontSize: 13 }}>{error}</div>}

      {!loading && results.map(c => (
        <div key={c.id} className="card" style={{ cursor: 'pointer' }} onClick={() => openCoin(c.id)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {c.thumb && <img src={c.thumb} width={36} height={36} style={{ borderRadius: '50%' }} />}
            <div style={{ flex: 1 }}>
              <strong>{c.name}</strong>
              <div className="muted">{c.symbol?.toUpperCase()}{c.market_cap_rank ? ` · Rank #${c.market_cap_rank}` : ''}</div>
            </div>
            <span style={{ color: '#505050', fontSize: 18 }}>›</span>
          </div>
        </div>
      ))}

      {!loading && results.length === 0 && !error && (
        <>
          <div style={{ textAlign: 'center', color: '#505050', padding: '32px 0 16px', fontSize: 13 }}>
            Type a coin name, ticker, or paste a contract address<br />
            <span style={{ fontSize: 28, display: 'block', marginTop: 12 }}>🔍</span>
          </div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>Popular coins</div>
          {POPULAR.map(c => (
            <div key={c.id} className="card" style={{ cursor: 'pointer' }} onClick={() => openCoin(c.id)}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <img src={c.thumb} width={36} height={36} style={{ borderRadius: '50%' }} />
                <div style={{ flex: 1 }}>
                  <strong>{c.name}</strong>
                  <div className="muted">{c.sym}</div>
                </div>
                <span style={{ color: '#505050', fontSize: 18 }}>›</span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
