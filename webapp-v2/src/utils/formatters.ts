const CURRENCY_RATES: Record<string, number> = {
  USD: 1,
  NPR: 133.5,
  INR: 83.5,
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  NPR: 'Rs.',
  INR: '₹',
}

export function formatPrice(price: number | string, currency = 'USD'): string {
  const num = typeof price === 'string' ? parseFloat(price) : price
  if (!num || isNaN(num)) return '0'
  const converted = num * (CURRENCY_RATES[currency] || 1)
  const sym = CURRENCY_SYMBOLS[currency] || '$'
  if (converted >= 1000) return `${sym}${converted.toLocaleString('en', { maximumFractionDigits: 2 })}`
  if (converted >= 1) return `${sym}${converted.toFixed(4)}`
  if (converted >= 0.01) return `${sym}${converted.toFixed(6)}`
  return `${sym}${converted.toFixed(8)}`
}

export function formatMarketCap(value: number | string): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (!num || isNaN(num)) return '$0'
  if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`
  if (num >= 1e9)  return `$${(num / 1e9).toFixed(2)}B`
  if (num >= 1e6)  return `$${(num / 1e6).toFixed(1)}M`
  return `$${num.toLocaleString()}`
}

export function formatVolume(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`
  return `$${(value / 1e3).toFixed(1)}K`
}

export function formatPct(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

export function formatTimeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

export function isContractAddress(input: string): boolean {
  return /^0x[0-9a-fA-F]{40}$/.test(input) || /^[1-9A-HJ-NP-Za-km-z]{32,88}$/.test(input)
}
