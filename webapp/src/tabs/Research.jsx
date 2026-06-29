import { useState } from 'react'
import {
  fetchCoinDetail, fetchPriceChart, searchCoins,
  fetchByContract, fp, fmcap, isAddress, computeSignal,
} from '../api/coingecko'
import Spinner from '../components/Spinner'
import Sparkline from '../components/Sparkline'

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

const CHART_DAYS = [
  { label: '24h', days: 1 },
  { label: '7d',  days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
]

const TOP_EXCHANGES = [
  'Binance', 'Coinbase', 'Kraken', 'OKX', 'Bybit', 'KuCoin', 'Gate.io', 'Huobi',
]

// ─── GeckoTerminal fallback detail view ─────────────────────────────────────

function GTDetailView({ data, onBack }) {
  const { _attrs: a, _network: net } = data
  const price = parseFloat(a.price_usd || 0)
  const chg24 = parseFloat(a.price_change_percentage?.h24 || 0)
  const vol24 = parseFloat(a.volume_usd?.h24 || 0)
  const fdv   = parseFloat(a.fdv_usd || 0)
  const mcap  = parseFloat(a.market_cap_usd || 0)

  const sig = (() => {
    const vr = vol24 / (mcap || fdv || 1)
    if (chg24 > 10 && vr > 0.2) return { label: 'STRONG BUY',  color: '#00E676', icon: '🚀', advice: 'Strong upward momentum. Volume is high.' }
    if (chg24 > 4  && vr > 0.1) return { label: 'BUY',         color: '#00C853', icon: '📈', advice: 'Positive trend. Consider small position.' }
    if (chg24 < -10 && vr > 0.2) return { label: 'STRONG SELL', color: '#FF1744', icon: '🔥', advice: 'Heavy selling. Avoid buying now.' }
    if (chg24 < -4 && vr > 0.1) return { label: 'SELL',        color: '#FF3D57', icon: '📉', advice: 'Downward pressure. Be careful.' }
    return { label: 'NEUTRAL', color: '#F7931A', icon: '➡️', advice: 'Mixed signals. Wait for clearer direction.' }
  })()

  return (
    <div className="tab-content">
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: '#F7931A', cursor: 'pointer', padding: '0 0 12px', fontSize: 14 }}>← Back</button>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        {a.image_url && <img src={a.image_url} width={48} height={48} style={{ borderRadius: '50%' }} />}
        <div>
          <h2 style={{ margin: 0 }}>{a.name} <span style={{ color: '#606060', fontWeight: 400, fontSize: 14 }}>({(a.symbol || '').toUpperCase()})</span></h2>
          <div className="muted">via GeckoTerminal · {net}</div>
        </div>
      </div>

      {/* Price */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 28, fontWeight: 900 }}>${fp(price)}</div>
        <div style={{ marginTop: 4, display: 'flex', gap: 8 }}>{pct(chg24)} <span className="muted" style={{ fontSize: 12 }}>24h</span></div>
      </div>

      {/* Signal */}
      <div className="card" style={{ marginBottom: 12, borderLeft: `3px solid ${sig.color}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 24 }}>{sig.icon}</span>
          <span style={{ fontWeight: 800, color: sig.color, fontSize: 18 }}>{sig.label}</span>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: '#C0C0C0', lineHeight: 1.5 }}>{sig.advice}</p>
        <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>⚠️ Not financial advice. Always do your own research (DYOR).</div>
      </div>

      {/* Metrics */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>Key Metrics</div>
        {vol24  > 0 && <Row label="24h Volume" value={fmcap(vol24)} />}
        {fdv    > 0 && <Row label="FDV" value={fmcap(fdv)} />}
        {mcap   > 0 && <Row label="Market Cap" value={fmcap(mcap)} />}
        {a.gt_score && <Row label="GT Score" value={`${parseFloat(a.gt_score).toFixed(1)}/100`} />}
      </div>

      {/* Beginner tip */}
      <BeginnerTips />
    </div>
  )
}

// ─── Beginner tips box ───────────────────────────────────────────────────────

function BeginnerTips() {
  const [open, setOpen] = useState(false)
  return (
    <div className="card" style={{ marginBottom: 12, borderLeft: '3px solid #F7931A' }}>
      <button onClick={() => setOpen(o => !o)} style={{
        background: 'none', border: 'none', color: '#F7931A',
        cursor: 'pointer', fontWeight: 700, fontSize: 14, padding: 0, width: '100%', textAlign: 'left',
      }}>
        💡 Beginner Tips {open ? '▲' : '▼'}
      </button>
      {open && (
        <ul style={{ margin: '12px 0 0', padding: '0 0 0 16px', color: '#C0C0C0', fontSize: 13, lineHeight: 1.7 }}>
          <li><strong>Never invest more than you can afford to lose.</strong></li>
          <li>Use <strong>Dollar-Cost Averaging (DCA)</strong> — buy small amounts regularly instead of all at once.</li>
          <li>Set a <strong>stop-loss</strong> at 10–15% below your buy price to limit losses.</li>
          <li>Check <strong>market cap</strong>, not just price — a $0.001 coin can still be overvalued.</li>
          <li>High volume = more people trading = easier to buy/sell quickly (liquidity).</li>
          <li><strong>ATH</strong> = All-Time High. Buying near ATH is risky. Buying far below ATH may be an opportunity.</li>
          <li>Never buy based on hype alone. Read the project's website and whitepaper.</li>
        </ul>
      )}
    </div>
  )
}

// ─── Full CoinGecko detail view ───────────────────────────────────────────────

function CoinDetailView({ data, onBack }) {
  const [chartDays, setChartDays] = useState(7)
  const [chartPrices, setChartPrices] = useState(data._sparkline || [])
  const [chartLoading, setChartLoading] = useState(false)

  const md    = data.market_data
  const price = md?.current_price?.usd || 0
  const chg24 = md?.price_change_percentage_24h || 0
  const chg7d = md?.price_change_percentage_7d  || 0
  const chg30 = md?.price_change_percentage_30d || 0
  const ath   = md?.ath?.usd || 0
  const atl   = md?.atl?.usd || 0
  const athPct = md?.ath_change_percentage?.usd || 0
  const atlPct = md?.atl_change_percentage?.usd || 0
  const mcap  = md?.market_cap?.usd || 0
  const vol24 = md?.total_volume?.usd || 0
  const supply = md?.circulating_supply || 0
  const maxSup = md?.max_supply
  const fdv    = md?.fully_diluted_valuation?.usd || 0

  const sig = computeSignal(md)

  // top exchanges from tickers
  const tickers = (data.tickers || [])
    .filter(t => TOP_EXCHANGES.includes(t.market?.name) && t.converted_last?.usd)
    .slice(0, 5)

  const uniqueExchanges = [...new Set(tickers.map(t => t.market?.name))].slice(0, 5)

  async function loadChart(days) {
    setChartDays(days); setChartLoading(true)
    try {
      const prices = await fetchPriceChart(data.id, days)
      setChartPrices(prices)
    } catch { /* keep existing */ }
    setChartLoading(false)
  }

  // Support = ATL or 52w low, Resistance = ATH
  const supportNote  = atl > 0 ? `$${fp(atl)} (all-time low)` : '—'
  const resistNote   = ath > 0 ? `$${fp(ath)} (all-time high)` : '—'
  // Estimated buy zone: 5–15% above current support
  const buyZoneLow  = price * 0.95
  const buyZoneHigh = price * 1.00

  // links
  const website  = data.links?.homepage?.[0]
  const explorer = data.links?.blockchain_site?.[0]
  const reddit   = data.links?.subreddit_url
  const twitter  = data.links?.twitter_screen_name

  const desc = data.description?.en
    ?.replace(/<[^>]*>/g, '')
    ?.replace(/\s+/g, ' ')
    ?.trim()
    ?.slice(0, 400)

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
            {/* score bar */}
            <div style={{ flex: 1, height: 6, background: '#2A2A2A', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${sig.score}%`, height: '100%', background: sig.color, borderRadius: 3 }} />
            </div>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: '#C0C0C0', lineHeight: 1.6 }}>{sig.advice}</p>
          <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>⚠️ Not financial advice. Always DYOR.</div>
        </div>
      )}

      {/* Price chart */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>Price Chart</span>
          <div style={{ display: 'flex', gap: 4 }}>
            {CHART_DAYS.map(d => (
              <button key={d.days} onClick={() => loadChart(d.days)} style={{
                background: chartDays === d.days ? '#F7931A' : '#2A2A2A',
                color: chartDays === d.days ? '#000' : '#A0A0A0',
                border: 'none', borderRadius: 6, padding: '3px 8px',
                cursor: 'pointer', fontSize: 11, fontWeight: 700,
              }}>{d.label}</button>
            ))}
          </div>
        </div>
        {chartLoading
          ? <div style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span className="muted">Loading…</span></div>
          : <Sparkline prices={chartPrices} color={chg24 >= 0 ? '#00C853' : '#FF3D57'} />
        }
      </div>

      {/* Where to buy */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>🏦 Where to Buy</div>
        {uniqueExchanges.length > 0 ? (
          <>
            {tickers.filter((t, i, arr) => arr.findIndex(x => x.market?.name === t.market?.name) === i).map(t => (
              <div key={t.market?.name} className="row" style={{ padding: '7px 0', borderBottom: '1px solid #1E1E1E' }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{t.market?.name}</span>
                <span style={{ fontSize: 13, color: '#A0A0A0' }}>${fp(t.converted_last?.usd)}</span>
              </div>
            ))}
          </>
        ) : (
          <div className="muted" style={{ fontSize: 13 }}>
            Check: Binance · Coinbase · Kraken · OKX · Bybit
          </div>
        )}
        <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>
          💡 For beginners: Binance and Coinbase are the easiest to start with.
        </div>
      </div>

      {/* Buy zone */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>📍 Price Levels</div>
        <Row label="Current Price" value={`$${fp(price)}`} />
        <Row label="🟢 Support (ATL)" value={supportNote} sub="Historical low — strong support" />
        <Row label="🔴 Resistance (ATH)" value={resistNote} sub="Historical high — selling pressure" />
        <Row label="📉 Below ATH" value={`${Math.abs(athPct).toFixed(1)}% below peak`} />
        <div style={{ marginTop: 10, padding: '10px 12px', background: '#1A2A1A', borderRadius: 8 }}>
          <div style={{ fontSize: 12, color: '#00C853', fontWeight: 700, marginBottom: 4 }}>💡 DCA Buy Zone</div>
          <div className="muted" style={{ fontSize: 12 }}>
            Consider spreading buys between <strong style={{ color: '#E0E0E0' }}>${fp(buyZoneLow)}</strong> – <strong style={{ color: '#E0E0E0' }}>${fp(buyZoneHigh)}</strong> in small amounts over time.
          </div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>📊 Key Metrics</div>
        <Row label="Market Cap" value={fmcap(mcap)} sub="Total value of all coins" />
        <Row label="24h Volume" value={fmcap(vol24)} sub="How much traded today" />
        {fdv > 0 && <Row label="Fully Diluted Value" value={fmcap(fdv)} sub="If all coins were in circulation" />}
        <Row label="Circulating Supply" value={fmcap(supply)} sub="Coins currently in market" />
        {maxSup && <Row label="Max Supply" value={fmcap(maxSup)} sub="Total coins that will ever exist" />}
        {mcap > 0 && vol24 > 0 && <Row label="Vol / MCap Ratio" value={`${((vol24 / mcap) * 100).toFixed(2)}%`} sub=">10% = high activity" />}
      </div>

      {/* About */}
      {desc && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="section-title" style={{ marginTop: 0 }}>📖 About {data.name}</div>
          <p style={{ margin: 0, fontSize: 13, color: '#C0C0C0', lineHeight: 1.7 }}>{desc}…</p>
        </div>
      )}

      {/* Links */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>🔗 Links & News</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          {website && <a href={website} target="_blank" rel="noreferrer" style={linkStyle}>🌐 Website</a>}
          {explorer && <a href={explorer} target="_blank" rel="noreferrer" style={linkStyle}>🔍 Explorer</a>}
          {reddit && <a href={reddit} target="_blank" rel="noreferrer" style={linkStyle}>📣 Reddit</a>}
          {twitter && <a href={`https://x.com/${twitter}`} target="_blank" rel="noreferrer" style={linkStyle}>🐦 Twitter</a>}
          <a href={`https://www.coingecko.com/en/coins/${data.id}`} target="_blank" rel="noreferrer" style={linkStyle}>📰 CoinGecko</a>
          <a href={`https://coinmarketcap.com/currencies/${data.id}`} target="_blank" rel="noreferrer" style={{ ...linkStyle, background: '#1A2030' }}>📊 CMC</a>
        </div>
      </div>

      {/* Beginner tips */}
      <BeginnerTips />
    </div>
  )
}

const linkStyle = {
  background: '#1A1A2A',
  color: '#A0C0FF',
  padding: '6px 12px',
  borderRadius: 8,
  fontSize: 12,
  textDecoration: 'none',
  fontWeight: 600,
}

// ─── Search screen ────────────────────────────────────────────────────────────

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
      // attach sparkline prices if available
      const sparkline = d.market_data?.sparkline_7d?.price || []
      d._sparkline = sparkline.map(p => p)
      setDetail(d)
    } catch (e) {
      setErr('Failed to load. Try again.')
    }
    setLoad(false)
  }

  if (detail) {
    if (detail._geckoterminal) return <GTDetailView data={detail} onBack={() => setDetail(null)} />
    return <CoinDetailView data={detail} onBack={() => setDetail(null)} />
  }

  return (
    <div className="tab-content">
      <h2>🔍 Research</h2>
      <p className="muted" style={{ fontSize: 12, marginTop: -8, marginBottom: 12 }}>
        Search any coin, token, or paste a contract address
      </p>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          placeholder="Bitcoin, BTC, ETH, or 0x…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          style={{ flex: 1 }}
        />
        <button className="btn" onClick={search} style={{ width: 'auto', padding: '0 18px', flex: 'none' }}>
          Go
        </button>
      </div>

      {loading && <Spinner text="Searching…" />}
      {error && <div style={{ color: '#FF3D57', textAlign: 'center', padding: '24px 0', fontSize: 13 }}>{error}</div>}

      {!loading && results.map(c => (
        <div key={c.id} className="card" style={{ cursor: 'pointer' }} onClick={() => openCoin(c.id)}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {c.thumb && <img src={c.thumb} width={36} height={36} style={{ borderRadius: '50%' }} />}
            <div style={{ flex: 1 }}>
              <strong>{c.name}</strong>
              <div className="muted">{c.symbol?.toUpperCase()} {c.market_cap_rank ? `· Rank #${c.market_cap_rank}` : ''}</div>
            </div>
            <span style={{ color: '#505050', fontSize: 18 }}>›</span>
          </div>
        </div>
      ))}

      {!loading && results.length === 0 && !error && (
        <div style={{ color: '#505050', textAlign: 'center', padding: '40px 0 20px', fontSize: 13 }}>
          Type a coin name, ticker, or paste a contract address<br />
          <span style={{ fontSize: 20, display: 'block', marginTop: 16 }}>🔍</span>
        </div>
      )}

      {/* Quick shortcuts */}
      {!loading && results.length === 0 && !error && (
        <div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>Popular coins</div>
          {[
            { id: 'bitcoin',  name: 'Bitcoin',  sym: 'BTC', thumb: 'https://assets.coingecko.com/coins/images/1/thumb/bitcoin.png' },
            { id: 'ethereum', name: 'Ethereum', sym: 'ETH', thumb: 'https://assets.coingecko.com/coins/images/279/thumb/ethereum.png' },
            { id: 'solana',   name: 'Solana',   sym: 'SOL', thumb: 'https://assets.coingecko.com/coins/images/4128/thumb/solana.png' },
            { id: 'binancecoin', name: 'BNB',   sym: 'BNB', thumb: 'https://assets.coingecko.com/coins/images/825/thumb/bnb-icon2_2x.png' },
            { id: 'ripple',   name: 'XRP',      sym: 'XRP', thumb: 'https://assets.coingecko.com/coins/images/44/thumb/xrp-symbol-white-128.png' },
          ].map(c => (
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
        </div>
      )}
    </div>
  )
}
