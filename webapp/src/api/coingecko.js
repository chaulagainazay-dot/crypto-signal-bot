// ─── Base URLs ────────────────────────────────────────────────────────────────
const CG  = 'https://api.coingecko.com/api/v3'
const GT  = 'https://api.geckoterminal.com/api/v2'
const CC  = 'https://api.coincap.io/v2'           // fallback #1 — no key, unlimited
const BN  = 'https://api.binance.com/api/v3'      // fallback #2 — no key, very high limit
const DS  = 'https://api.dexscreener.com/latest'  // fallback #3 — no key, unlimited

// ─── Core fetch with timeout ──────────────────────────────────────────────────
async function get(url) {
  const r = await fetch(url, { signal: AbortSignal.timeout(12000) })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

// Try primary, fall back silently on any error
async function tryOr(primary, ...fallbacks) {
  try { return await primary() } catch { /* fall through */ }
  for (const fb of fallbacks) {
    try { return await fb() } catch { /* fall through */ }
  }
  return null
}

// ─── CoinCap helpers ──────────────────────────────────────────────────────────

// CoinCap uses its own ID system (lowercase name, e.g. "bitcoin").
// Build a small slug map on demand.
const _cgToCcSlug = {} // coinId → coincap slug

async function ccAsset(slug) {
  return get(`${CC}/assets/${encodeURIComponent(slug)}`)
}

// Map CoinGecko ID → CoinCap slug heuristic (works for top 500)
function cgIdToCcSlug(cgId) {
  if (_cgToCcSlug[cgId]) return _cgToCcSlug[cgId]
  // CoinCap slugs are usually just the coin name lower-cased, same as CoinGecko id
  return cgId
}

// ─── Global market ─────────────────────────────────────────────────────────────
export async function fetchGlobal() {
  return tryOr(
    async () => {
      const d = await get(`${CG}/global`)
      const m = d.data
      return {
        mcap:   m.total_market_cap.usd,
        vol:    m.total_volume.usd,
        btcDom: m.market_cap_percentage.btc,
        ethDom: m.market_cap_percentage.eth,
        change: m.market_cap_change_percentage_24h_usd,
        coins:  m.active_cryptocurrencies,
        _source: 'coingecko',
      }
    },
    async () => {
      // CoinCap global
      const d = await get(`${CC}/assets?limit=2&ids=bitcoin,ethereum`)
      const btc = d.data.find(a => a.id === 'bitcoin')
      const eth = d.data.find(a => a.id === 'ethereum')
      const totalMcap = parseFloat(btc?.marketCapUsd || 0) / ((parseFloat(btc?.marketCapUsd || 1) / (parseFloat(btc?.marketCapUsd || 1) + parseFloat(eth?.marketCapUsd || 0))) || 1)
      return {
        mcap:   parseFloat(btc?.marketCapUsd || 0) * 4, // rough estimate
        vol:    parseFloat(btc?.volumeUsd24Hr || 0) * 4,
        btcDom: 50,
        ethDom: 15,
        change: parseFloat(btc?.changePercent24Hr || 0),
        coins:  10000,
        _source: 'coincap',
      }
    }
  )
}

// ─── Top coins list ──────────────────────────────────────────────────────────
export async function fetchTopCoins(limit = 50) {
  return tryOr(
    () => get(
      `${CG}/coins/markets?vs_currency=usd&order=market_cap_desc` +
      `&per_page=${Math.min(limit, 250)}&page=1&price_change_percentage=24h,7d`
    ),
    async () => {
      // CoinCap fallback — maps to CoinGecko-compatible shape
      const d = await get(`${CC}/assets?limit=${Math.min(limit, 200)}`)
      return (d.data || []).map(a => ({
        id:                            a.id,
        symbol:                        a.symbol?.toLowerCase(),
        name:                          a.name,
        image:                         `https://assets.coincap.io/assets/icons/${a.symbol?.toLowerCase()}@2x.png`,
        current_price:                 parseFloat(a.priceUsd || 0),
        market_cap:                    parseFloat(a.marketCapUsd || 0),
        market_cap_rank:               parseInt(a.rank || 0),
        total_volume:                  parseFloat(a.volumeUsd24Hr || 0),
        price_change_percentage_24h:   parseFloat(a.changePercent24Hr || 0),
        price_change_percentage_7d:    0, // CoinCap free doesn't provide 7d
        ath:                           0,
        _source:                       'coincap',
      }))
    }
  )
}

// ─── Trending ────────────────────────────────────────────────────────────────
export async function fetchTrending() {
  return tryOr(
    async () => {
      const d = await get(`${CG}/search/trending`)
      return d.coins.map(c => c.item)
    },
    async () => {
      // DexScreener trending tokens as fallback
      const d = await get(`${DS}/dex/tokens/trending`)
      return (d.pairs || []).slice(0, 10).map(p => ({
        id:     p.baseToken?.address || p.baseToken?.symbol?.toLowerCase(),
        name:   p.baseToken?.name,
        symbol: p.baseToken?.symbol,
        small:  null,
        thumb:  null,
        data:   { price: p.priceUsd, price_change_percentage_24h: { usd: p.priceChange?.h24 || 0 } },
        _source: 'dexscreener',
      }))
    }
  )
}

// ─── Coin detail ─────────────────────────────────────────────────────────────
export async function fetchCoinDetail(id) {
  return tryOr(
    () => get(
      `${CG}/coins/${id}?localization=false&tickers=true` +
      `&market_data=true&community_data=false&developer_data=false&sparkline=true`
    ),
    async () => {
      const slug = cgIdToCcSlug(id)
      const d = await ccAsset(slug)
      const a = d.data
      const price = parseFloat(a.priceUsd || 0)
      const mcap  = parseFloat(a.marketCapUsd || 0)
      const vol   = parseFloat(a.volumeUsd24Hr || 0)
      const chg24 = parseFloat(a.changePercent24Hr || 0)
      return {
        id:     a.id,
        symbol: a.symbol?.toLowerCase(),
        name:   a.name,
        image: { large: `https://assets.coincap.io/assets/icons/${a.symbol?.toLowerCase()}@2x.png` },
        market_data: {
          current_price:              { usd: price },
          market_cap:                 { usd: mcap },
          total_volume:               { usd: vol },
          price_change_percentage_24h: chg24,
          price_change_percentage_7d_in_currency: { usd: 0 },
          ath:                        { usd: 0 },
          atl:                        { usd: 0 },
          circulating_supply:         parseFloat(a.supply || 0),
          max_supply:                 parseFloat(a.maxSupply || 0) || null,
          market_cap_rank:            parseInt(a.rank || 0),
        },
        tickers:     [],
        description: { en: '' },
        links:       {},
        _source:     'coincap',
      }
    }
  )
}

// ─── OHLC candle data ─────────────────────────────────────────────────────────
// Returns [[ts, open, high, low, close], ...]
export async function fetchOHLC(id, days = 7) {
  return tryOr(
    async () => {
      const d = await get(`${CG}/coins/${id}/ohlc?vs_currency=usd&days=${days}`)
      return Array.isArray(d) ? d : []
    },
    async () => {
      // Binance OHLC fallback — map CoinGecko id → Binance symbol heuristic
      const sym = id.split('-')[0].toUpperCase() + 'USDT'
      const interval = days <= 1 ? '1h' : days <= 7 ? '4h' : '1d'
      const limit    = days <= 1 ? 24  : days <= 7 ? 42   : days
      const d = await get(`${BN}/klines?symbol=${sym}&interval=${interval}&limit=${limit}`)
      if (!Array.isArray(d)) return []
      return d.map(k => [
        k[0],           // ts
        parseFloat(k[1]), // open
        parseFloat(k[2]), // high
        parseFloat(k[3]), // low
        parseFloat(k[4]), // close
      ])
    }
  )
}

// ─── Price chart (line) ───────────────────────────────────────────────────────
export async function fetchPriceChart(id, days = 7) {
  return tryOr(
    async () => {
      const d = await get(`${CG}/coins/${id}/market_chart?vs_currency=usd&days=${days}`)
      return d.prices || []
    },
    async () => {
      // Derive from Binance klines
      const sym = id.split('-')[0].toUpperCase() + 'USDT'
      const d = await get(`${BN}/klines?symbol=${sym}&interval=1d&limit=${days}`)
      if (!Array.isArray(d)) return []
      return d.map(k => [k[0], parseFloat(k[4])]) // [ts, close]
    }
  )
}

// ─── News ─────────────────────────────────────────────────────────────────────
// CryptoCompare is already reliable & free — no fallback needed
export async function fetchCryptoNews(symbol, limit = 6) {
  try {
    const isGeneral = !symbol || symbol.toLowerCase() === 'cryptocurrency'
    const url = isGeneral
      ? `https://min-api.cryptocompare.com/data/v2/news/?lang=EN&sortOrder=latest`
      : `https://min-api.cryptocompare.com/data/v2/news/?categories=${encodeURIComponent(symbol.toUpperCase())}&lang=EN&sortOrder=latest`
    const r = await fetch(url, { signal: AbortSignal.timeout(10000) })
    if (!r.ok) throw new Error()
    const d = await r.json()
    return (d.Data || []).slice(0, limit)
  } catch { return [] }
}

// ─── Search ───────────────────────────────────────────────────────────────────
export async function searchCoins(q) {
  return tryOr(
    async () => {
      const d = await get(`${CG}/search?query=${encodeURIComponent(q)}`)
      return d.coins.slice(0, 8)
    },
    async () => {
      // CoinCap search fallback
      const d = await get(`${CC}/assets?search=${encodeURIComponent(q)}&limit=8`)
      return (d.data || []).map(a => ({
        id:              a.id,
        name:            a.name,
        symbol:          a.symbol,
        thumb:           `https://assets.coincap.io/assets/icons/${a.symbol?.toLowerCase()}@2x.png`,
        large:           `https://assets.coincap.io/assets/icons/${a.symbol?.toLowerCase()}@2x.png`,
        market_cap_rank: parseInt(a.rank || 0) || null,
        _source:         'coincap',
      }))
    },
    async () => {
      // DexScreener search fallback — good for small/new tokens
      const d = await get(`${DS}/dex/search/?q=${encodeURIComponent(q)}`)
      const seen = new Set()
      return (d.pairs || []).slice(0, 8).reduce((acc, p) => {
        const key = p.baseToken?.symbol
        if (!key || seen.has(key)) return acc
        seen.add(key)
        acc.push({
          id:              p.baseToken?.address || key.toLowerCase(),
          name:            p.baseToken?.name,
          symbol:          p.baseToken?.symbol,
          thumb:           null,
          market_cap_rank: null,
          _source:         'dexscreener',
          _pair:           p,
        })
        return acc
      }, [])
    }
  )
}

// ─── Contract address lookup ──────────────────────────────────────────────────
const GT_NETS = [
  'bsc', 'eth', 'polygon_pos', 'arbitrum', 'base',
  'solana', 'optimism', 'avalanche', 'fantom', 'cronos',
]

export async function fetchByContract(address) {
  const lower = address.toLowerCase()

  // GeckoTerminal first
  for (const net of GT_NETS) {
    try {
      const d = await get(`${GT}/networks/${net}/tokens/${lower}`)
      const a = d?.data?.attributes
      if (a?.price_usd) return { _geckoterminal: true, _network: net, _attrs: a }
    } catch { /* try next chain */ }
  }

  // DexScreener fallback
  try {
    const d = await get(`${DS}/dex/tokens/${lower}`)
    const p = d?.pairs?.[0]
    if (p) {
      return {
        _geckoterminal: true,
        _network:       p.chainId,
        _source:        'dexscreener',
        _attrs: {
          name:                   p.baseToken?.name,
          symbol:                 p.baseToken?.symbol,
          price_usd:              p.priceUsd,
          volume_usd:             { h24: p.volume?.h24 },
          price_change_percentage:{ h24: p.priceChange?.h24 },
          fdv_usd:                p.fdv,
        },
      }
    }
  } catch { /* no result */ }

  return null
}

export async function fetchGTPool(network, address) {
  const d = await get(`${GT}/networks/${network}/pools/${address.toLowerCase()}`)
  return d?.data?.attributes || null
}

// ─── Formatting helpers ───────────────────────────────────────────────────────
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
  const athPct = ((price - ath) / ath) * 100
  const vr     = vol / mcap

  let score = 50

  if (chg24 > 10) score += 20
  else if (chg24 > 4) score += 10
  else if (chg24 < -10) score -= 20
  else if (chg24 < -4) score -= 10

  if (chg7d > 15) score += 15
  else if (chg7d > 5) score += 8
  else if (chg7d < -15) score -= 15
  else if (chg7d < -5) score -= 8

  if (vr > 0.3) score += 15
  else if (vr > 0.15) score += 8
  else if (vr < 0.02) score -= 5

  if (athPct > -5) score -= 10
  else if (athPct < -80) score += 5

  score = Math.max(0, Math.min(100, score))

  if (score >= 72) return { label: 'STRONG BUY',    color: '#00E676', bg: '#00E67622', icon: '🚀', score, advice: 'Strong upward momentum. Volume is high. Consider buying in small portions.' }
  if (score >= 58) return { label: 'BUY',            color: '#00C853', bg: '#00C85322', icon: '📈', score, advice: 'Positive trend. Good time to add a position. Use dollar-cost averaging.' }
  if (score >= 42) return { label: 'NEUTRAL / HOLD', color: '#F7931A', bg: '#F7931A22', icon: '➡️', score, advice: 'Mixed signals. Wait for clearer direction before entering.' }
  if (score >= 28) return { label: 'SELL',            color: '#FF3D57', bg: '#FF3D5722', icon: '📉', score, advice: 'Downward pressure. Consider reducing your position.' }
  return               { label: 'STRONG SELL',    color: '#FF1744', bg: '#FF174422', icon: '🔥', score, advice: 'Heavy selling. Avoid buying. Consider exiting if holding.' }
}
