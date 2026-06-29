const CG = 'https://api.coingecko.com/api/v3'
const GT = 'https://api.geckoterminal.com/api/v2'

async function get(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(12000) })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function fetchGlobal() {
  const d = await get(`${CG}/global`)
  const m = d.data
  return {
    mcap:   m.total_market_cap.usd,
    vol:    m.total_volume.usd,
    btcDom: m.market_cap_percentage.btc,
    ethDom: m.market_cap_percentage.eth,
    change: m.market_cap_change_percentage_24h_usd,
    coins:  m.active_cryptocurrencies,
  }
}

export async function fetchTopCoins(limit = 50) {
  return get(
    `${CG}/coins/markets?vs_currency=usd&order=market_cap_desc` +
    `&per_page=${limit}&page=1&price_change_percentage=24h,7d`
  )
}

export async function fetchTrending() {
  const d = await get(`${CG}/search/trending`)
  return d.coins.map(c => c.item)
}

export async function fetchCoinDetail(id) {
  return get(
    `${CG}/coins/${id}?localization=false&tickers=true` +
    `&market_data=true&community_data=false&developer_data=false&sparkline=true`
  )
}

export async function fetchPriceChart(id, days = 7) {
  const d = await get(`${CG}/coins/${id}/market_chart?vs_currency=usd&days=${days}`)
  return d.prices || []
}

// OHLC candle data: returns [[ts, open, high, low, close], ...]
export async function fetchOHLC(id, days = 7) {
  const d = await get(`${CG}/coins/${id}/ohlc?vs_currency=usd&days=${days}`)
  return Array.isArray(d) ? d : []
}

// CryptoCompare free news — no API key needed
export async function fetchCryptoNews(symbol, limit = 6) {
  try {
    const url = `https://min-api.cryptocompare.com/data/v2/news/?categories=${encodeURIComponent(symbol.toUpperCase())}&lang=EN&limit=${limit}&sortOrder=latest`
    const r = await fetch(url, { signal: AbortSignal.timeout(10000) })
    if (!r.ok) throw new Error()
    const d = await r.json()
    return (d.Data || []).slice(0, limit)
  } catch { return [] }
}

export async function searchCoins(q) {
  const d = await get(`${CG}/search?query=${encodeURIComponent(q)}`)
  return d.coins.slice(0, 8)
}

const GT_NETS = [
  'bsc', 'eth', 'polygon_pos', 'arbitrum', 'base',
  'solana', 'optimism', 'avalanche', 'fantom', 'cronos',
]

export async function fetchByContract(address) {
  const lower = address.toLowerCase()
  for (const net of GT_NETS) {
    try {
      const d = await get(`${GT}/networks/${net}/tokens/${lower}`)
      const a = d?.data?.attributes
      if (a?.price_usd) return { _geckoterminal: true, _network: net, _attrs: a }
    } catch { /* try next chain */ }
  }
  return null
}

export async function fetchGTPool(network, address) {
  const d = await get(`${GT}/networks/${network}/pools/${address.toLowerCase()}`)
  return d?.data?.attributes || null
}

export function fp(price) {
  if (!price) return '0'
  const p = parseFloat(price)
  if (p >= 1000) return p.toLocaleString('en', { maximumFractionDigits: 2 })
  if (p >= 1)    return p.toFixed(4)
  if (p >= 0.01) return p.toFixed(6)
  return p.toFixed(8)
}

export function fmcap(v) {
  const n = parseFloat(v) || 0
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6)  return `$${(n / 1e6).toFixed(1)}M`
  if (n >= 1e3)  return `$${(n / 1e3).toFixed(1)}K`
  return `$${n.toLocaleString()}`
}

export function isAddress(s) {
  return /^0x[0-9a-fA-F]{40}$/.test(s) ||
         /^[1-9A-HJ-NP-Za-km-z]{32,88}$/.test(s)
}

// Compute a buy/sell signal from market data
export function computeSignal(md) {
  if (!md) return null
  const chg24  = md.price_change_percentage_24h || 0
  const chg7d  = md.price_change_percentage_7d   || 0
  const vol    = md.total_volume?.usd   || 0
  const mcap   = md.market_cap?.usd     || 1
  const ath    = md.ath?.usd            || 1
  const price  = md.current_price?.usd  || 0
  const athPct = ((price - ath) / ath) * 100   // negative = below ATH
  const vr     = vol / mcap

  let score = 50 // neutral baseline

  // Momentum
  if (chg24 > 10) score += 20
  else if (chg24 > 4) score += 10
  else if (chg24 < -10) score -= 20
  else if (chg24 < -4) score -= 10

  // Weekly trend
  if (chg7d > 15) score += 15
  else if (chg7d > 5) score += 8
  else if (chg7d < -15) score -= 15
  else if (chg7d < -5) score -= 8

  // Volume/mcap ratio
  if (vr > 0.3) score += 15
  else if (vr > 0.15) score += 8
  else if (vr < 0.02) score -= 5

  // ATH distance — if very close to ATH, caution
  if (athPct > -5) score -= 10   // near ATH, risky to buy
  else if (athPct < -80) score += 5  // deeply discounted

  score = Math.max(0, Math.min(100, score))

  if (score >= 72) return { label: 'STRONG BUY',  color: '#00E676', bg: '#00E67622', icon: '🚀', score, advice: 'Strong upward momentum. Volume is high. Consider buying in small portions.' }
  if (score >= 58) return { label: 'BUY',          color: '#00C853', bg: '#00C85322', icon: '📈', score, advice: 'Positive trend. Good time to add a position. Use dollar-cost averaging.' }
  if (score >= 42) return { label: 'NEUTRAL / HOLD', color: '#F7931A', bg: '#F7931A22', icon: '➡️', score, advice: 'Mixed signals. Wait for clearer direction before entering.' }
  if (score >= 28) return { label: 'SELL',          color: '#FF3D57', bg: '#FF3D5722', icon: '📉', score, advice: 'Downward pressure. Consider reducing your position.' }
  return               { label: 'STRONG SELL',  color: '#FF1744', bg: '#FF174422', icon: '🔥', score, advice: 'Heavy selling. Avoid buying. Consider exiting if holding.' }
}
