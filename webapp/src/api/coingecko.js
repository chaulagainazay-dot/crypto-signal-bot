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
    `&per_page=${limit}&page=1&price_change_percentage=24h`
  )
}

export async function fetchTrending() {
  const d = await get(`${CG}/search/trending`)
  return d.coins.map(c => c.item)
}

export async function fetchCoinDetail(id) {
  return get(
    `${CG}/coins/${id}?localization=false&tickers=false` +
    `&community_data=false&developer_data=false`
  )
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
