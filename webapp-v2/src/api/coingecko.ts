import type { Coin, GlobalMarketData, TrendingCoin, NewsArticle } from '../types'

const CG = 'https://api.coingecko.com/api/v3'
const CC = 'https://api.coincap.io/v2'
const DS = 'https://api.dexscreener.com/latest'

const CACHE = new Map<string, { data: unknown; ts: number }>()

function cached<T>(key: string, ttl: number): T | null {
  const c = CACHE.get(key)
  return c && Date.now() - c.ts < ttl ? (c.data as T) : null
}
function cache(key: string, data: unknown) {
  if (CACHE.size > 120) CACHE.delete(CACHE.keys().next().value!)
  CACHE.set(key, { data, ts: Date.now() })
}

async function get(url: string, ttl = 15000): Promise<unknown> {
  const cached_val = cached<unknown>(url, ttl)
  if (cached_val) return cached_val
  const r = await fetch(url, { signal: AbortSignal.timeout(12000) })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const d = await r.json()
  cache(url, d)
  return d
}

async function tryOr<T>(primary: () => Promise<T>, ...fallbacks: Array<() => Promise<T>>): Promise<T> {
  try { return await primary() } catch { /* fall through */ }
  for (const fb of fallbacks) {
    try { return await fb() } catch { /* fall through */ }
  }
  return [] as unknown as T
}

// ── Global ────────────────────────────────────────────────────────────────────
export async function fetchGlobal() {
  const d = await get(`${CG}/global`, 60000) as { data: GlobalMarketData }
  return d.data
}

// ── Top Coins ─────────────────────────────────────────────────────────────────
export async function fetchTopCoins(limit = 100): Promise<Coin[]> {
  return tryOr(
    async () => {
      const d = await get(
        `${CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=${limit}&page=1&sparkline=true&price_change_percentage=24h,7d`
      ) as Coin[]
      return d
    },
    async () => {
      const d = await get(`${CC}/assets?limit=${limit}`) as { data: unknown[] }
      return (d.data || []).map((a: unknown) => {
        const asset = a as Record<string, string>
        const price = parseFloat(asset.priceUsd || '0')
        return {
          id: asset.id, symbol: (asset.symbol || '').toLowerCase(),
          name: asset.name, image: '',
          current_price: price, market_cap: parseFloat(asset.marketCapUsd || '0'),
          market_cap_rank: parseInt(asset.rank || '0'),
          total_volume: parseFloat(asset.volumeUsd24Hr || '0'),
          price_change_24h: 0,
          price_change_percentage_24h: parseFloat(asset.changePercent24Hr || '0'),
          ath: 0, ath_change_percentage: 0, circulating_supply: parseFloat(asset.supply || '0'),
        } as Coin
      })
    }
  )
}

// ── Coin Detail ───────────────────────────────────────────────────────────────
export async function fetchCoinDetail(id: string) {
  return tryOr(
    () => get(`${CG}/coins/${id}?localization=false&tickers=true&market_data=true&community_data=false&developer_data=false&sparkline=true`, 30000),
    async () => {
      const d = await get(`${CC}/assets/${id}`) as { data: Record<string, string> }
      const a = d.data
      const price = parseFloat(a.priceUsd || '0')
      return {
        id: a.id, symbol: (a.symbol || '').toLowerCase(), name: a.name,
        image: { large: '' },
        market_data: {
          current_price: { usd: price },
          market_cap: { usd: parseFloat(a.marketCapUsd || '0') },
          total_volume: { usd: parseFloat(a.volumeUsd24Hr || '0') },
          price_change_percentage_24h: parseFloat(a.changePercent24Hr || '0'),
          price_change_percentage_7d_in_currency: { usd: 0 },
          ath: { usd: 0 }, atl: { usd: 0 },
          circulating_supply: parseFloat(a.supply || '0'),
        },
        description: { en: '' }, links: {}, tickers: [],
      }
    }
  )
}

// ── OHLC ──────────────────────────────────────────────────────────────────────
export async function fetchOHLC(id: string, days = 7): Promise<number[][]> {
  return tryOr(
    async () => {
      const d = await get(`${CG}/coins/${id}/ohlc?vs_currency=usd&days=${days}`) as number[][]
      return Array.isArray(d) ? d : []
    },
    async () => {
      const sym = id.toUpperCase() + 'USDT'
      const d = await get(`https://api.binance.com/api/v3/klines?symbol=${sym}&interval=1d&limit=${days}`) as unknown[][]
      return d.map((k) => [
        k[0] as number,
        parseFloat(k[1] as string),
        parseFloat(k[2] as string),
        parseFloat(k[3] as string),
        parseFloat(k[4] as string),
      ])
    }
  )
}

// ── Trending ──────────────────────────────────────────────────────────────────
export async function fetchTrending(): Promise<TrendingCoin[]> {
  return tryOr(
    async () => {
      const d = await get(`${CG}/search/trending`, 300000) as { coins: Array<{ item: TrendingCoin }> }
      return (d.coins || []).map((c) => c.item)
    },
    async () => {
      const d = await get(`${DS}/dex/tokens/trending`) as { pairs?: unknown[] }
      return (d.pairs || []).slice(0, 10).map((p: unknown, i: number) => {
        const pair = p as Record<string, unknown>
        const base = pair.baseToken as Record<string, string> || {}
        return {
          id: base.address || String(i), coin_id: i, name: base.name || '',
          symbol: base.symbol || '', market_cap_rank: i + 1,
          thumb: '', small: '', price_btc: 0, score: i,
        } as TrendingCoin
      })
    }
  )
}

// ── Search ────────────────────────────────────────────────────────────────────
export async function searchCoins(q: string) {
  if (!q.trim()) return []
  return tryOr(
    async () => {
      const d = await get(`${CG}/search?query=${encodeURIComponent(q)}`) as { coins: unknown[] }
      return (d.coins || []).slice(0, 8)
    },
    async () => {
      const d = await get(`${CC}/assets?search=${encodeURIComponent(q)}&limit=8`) as { data: Array<Record<string, string>> }
      return (d.data || []).map((a) => ({
        id: a.id, name: a.name, symbol: a.symbol,
        thumb: '', large: '', market_cap_rank: parseInt(a.rank || '0') || null,
      }))
    }
  )
}

// ── Contract address (DEX tokens) ─────────────────────────────────────────────
export async function fetchByContract(address: string) {
  const networks = ['bsc', 'eth', 'polygon_pos', 'arbitrum', 'base', 'solana', 'avalanche']
  for (const net of networks) {
    try {
      const d = await get(`https://api.geckoterminal.com/api/v2/networks/${net}/tokens/${address.toLowerCase()}`, 60000) as { data?: { attributes?: Record<string, unknown> } }
      const attrs = d?.data?.attributes
      if (attrs?.price_usd) return { ...attrs, _network: net, _source: 'geckoterminal' }
    } catch { continue }
  }
  return null
}

// ── News ──────────────────────────────────────────────────────────────────────
export async function fetchCryptoNews(symbol?: string, limit = 10): Promise<NewsArticle[]> {
  try {
    const isGeneral = !symbol || symbol.toLowerCase() === 'cryptocurrency'
    const url = isGeneral
      ? `https://min-api.cryptocompare.com/data/v2/news/?lang=EN&sortOrder=latest`
      : `https://min-api.cryptocompare.com/data/v2/news/?categories=${encodeURIComponent(symbol.toUpperCase())}&lang=EN&sortOrder=latest`
    const r = await fetch(url, { signal: AbortSignal.timeout(10000) })
    if (!r.ok) throw new Error()
    const d = await r.json() as { Data?: NewsArticle[] }
    return (d.Data || []).slice(0, limit)
  } catch { return [] }
}

// ── Fear & Greed ──────────────────────────────────────────────────────────────
export async function fetchFearGreed(): Promise<number> {
  try {
    const r = await fetch('https://api.alternative.me/fng/?limit=1', { signal: AbortSignal.timeout(8000) })
    const d = await r.json() as { data?: Array<{ value: string }> }
    return parseInt(d.data?.[0]?.value || '50')
  } catch { return 50 }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
export function fp(n: number): string {
  if (!n || isNaN(n)) return '0'
  if (n >= 1000) return n.toLocaleString('en', { maximumFractionDigits: 2 })
  if (n >= 1) return n.toFixed(4)
  if (n >= 0.01) return n.toFixed(6)
  return n.toFixed(8)
}

export function fmcap(n: number): string {
  if (!n) return '$0'
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9)  return `$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6)  return `$${(n / 1e6).toFixed(1)}M`
  return `$${n.toLocaleString()}`
}
