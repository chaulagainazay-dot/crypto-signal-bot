export interface Coin {
  id: string
  symbol: string
  name: string
  image: string
  current_price: number
  market_cap: number
  market_cap_rank: number
  total_volume: number
  price_change_24h: number
  price_change_percentage_24h: number
  price_change_percentage_7d_in_currency?: number
  sparkline_in_7d?: { price: number[] }
  ath: number
  ath_change_percentage: number
  circulating_supply: number
}

export interface GlobalMarketData {
  total_market_cap: { usd: number }
  total_volume: { usd: number }
  market_cap_percentage: { btc: number; eth: number }
  market_cap_change_percentage_24h_usd: number
  active_cryptocurrencies: number
}

export interface TrendingCoin {
  id: string
  coin_id: number
  name: string
  symbol: string
  market_cap_rank: number
  thumb: string
  small: string
  price_btc: number
  score: number
}

export interface Signal {
  id: string
  symbol: string
  name: string
  image: string
  type: 'STRONG BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG SELL'
  score: number
  confidence: number
  reasons: string[]
  price: number
  change24h: number
  change7d: number
  isTrending: boolean
  isSmallCap: boolean
  timestamp: number
}

export interface Holding {
  id: string
  coinId: string
  symbol: string
  name: string
  image: string
  amount: number
  buyPrice: number
  addedAt: number
}

export interface PriceAlert {
  id: string
  symbol: string
  target: number
  direction: 'above' | 'below'
  created: number
  triggered?: number
  active: boolean
}

export interface UserState {
  telegramId: number | null
  username: string | null
  theme: 'dark' | 'light'
  currency: 'USD' | 'NPR' | 'INR'
}

export interface WebSocketPrice {
  symbol: string
  price: number
  change24h: number
  changePercent24h: number
  volume24h: number
  high24h: number
  low24h: number
  lastUpdate: Date
}

export interface GeckoTerminalToken {
  price_usd: string
  price_change_percentage: { h24?: string }
  market_cap_usd?: string
  fdv_usd?: string
  volume_usd?: { h24?: string }
  _network: string
  _source: 'geckoterminal'
}

export interface NewsArticle {
  id: string
  title: string
  url: string
  body: string
  source: string
  source_info?: { name: string }
  published_on: number
  imageurl?: string
}

export type TabId = 'guide' | 'signals' | 'portfolio' | 'research' | 'v3'

// v3 types
export interface MentorAnalysis {
  recommendation: 'BUY' | 'WAIT' | 'SELL'
  reasons: string[]
  entry_conditions: string[]
  allocation: Record<string, number>
  risk_warnings: string[]
}

export interface DoctorReport {
  overall_score: number
  health_status: 'HEALTHY' | 'NEEDS_ATTENTION' | 'CRITICAL'
  breakdown: Record<string, number>
  problems: string[]
  recommendations: string[]
  target_allocation: Record<string, number>
}

export interface RiskResult {
  risk_level: string
  reward_level: string
  risk_reward_ratio: number
  position_size: number
  position_size_percent: number
  max_loss: number
  max_gain: number
  scenarios: { best_case: number; base_case: number; worst_case: number }
}

export interface WhaleData {
  symbol: string
  netflow_usd_m: number
  whale_accumulation: boolean
  interpretation: string
  large_transactions: Array<{ entity: string; action: string; amount: number; value_usd_m: number; time: string }>
  exchange_flows: { inflow: number; outflow: number; net: number }
}

export interface NewsBrief {
  btc_sentiment: string
  eth_sentiment: string
  alt_sentiment: string
  top_event: string
  key_levels: Record<string, string>
  article_count: number
}
