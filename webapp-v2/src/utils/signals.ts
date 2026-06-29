import type { Coin, Signal } from '../types'

export function generateSignal(coin: Coin): Signal {
  const prices = coin.sparkline_in_7d?.price || []
  const rsi = calculateRSI(prices)
  const macdSignal = calculateMACD(prices)
  const volRatio = (coin.total_volume || 0) / (coin.market_cap || 1)
  const chg24 = coin.price_change_percentage_24h || 0
  const chg7d = coin.price_change_percentage_7d_in_currency || 0
  const athDist = coin.ath ? ((coin.current_price - coin.ath) / coin.ath) * 100 : 0

  let score = 50
  const reasons: string[] = []

  // RSI
  if (rsi < 30) { score += 18; reasons.push(`RSI oversold (${rsi.toFixed(0)}) — potential bounce`) }
  else if (rsi < 45) { score += 8; reasons.push(`RSI below midpoint (${rsi.toFixed(0)})`) }
  else if (rsi > 70) { score -= 18; reasons.push(`RSI overbought (${rsi.toFixed(0)}) — caution`) }
  else if (rsi > 60) { score -= 5; reasons.push(`RSI elevated (${rsi.toFixed(0)})`) }

  // MACD
  if (macdSignal === 'bullish') { score += 10; reasons.push('MACD bullish crossover') }
  else if (macdSignal === 'bearish') { score -= 10; reasons.push('MACD bearish crossover') }

  // 24h momentum
  if (chg24 > 10) { score += 15; reasons.push(`Strong 24h gain +${chg24.toFixed(1)}%`) }
  else if (chg24 > 4) { score += 8; reasons.push(`Positive 24h momentum +${chg24.toFixed(1)}%`) }
  else if (chg24 < -10) { score -= 15; reasons.push(`Heavy 24h drop ${chg24.toFixed(1)}%`) }
  else if (chg24 < -4) { score -= 8; reasons.push(`Negative 24h momentum ${chg24.toFixed(1)}%`) }

  // 7d trend
  if (chg7d > 20) { score += 10; reasons.push(`Strong 7d uptrend +${chg7d.toFixed(1)}%`) }
  else if (chg7d > 8) { score += 5; reasons.push(`Positive 7d trend +${chg7d.toFixed(1)}%`) }
  else if (chg7d < -20) { score -= 10; reasons.push(`7d downtrend ${chg7d.toFixed(1)}%`) }

  // Volume
  if (volRatio > 0.3 && chg24 > 0) { score += 10; reasons.push('High volume confirms upward move') }
  else if (volRatio > 0.15) { score += 5; reasons.push('Above-average trading volume') }
  else if (volRatio < 0.02) { score -= 5; reasons.push('Low trading volume — weak conviction') }

  // ATH proximity
  if (athDist > -10) { score -= 8; reasons.push('Near all-time high — resistance zone') }
  else if (athDist < -80) { score += 8; reasons.push('Deep ATH discount — potential recovery') }

  score = Math.max(0, Math.min(100, score))

  const type: Signal['type'] =
    score >= 72 ? 'STRONG BUY' :
    score >= 58 ? 'BUY' :
    score >= 42 ? 'HOLD' :
    score >= 28 ? 'SELL' : 'STRONG SELL'

  const confidence = Math.min(95,
    40 +
    (rsi < 30 || rsi > 70 ? 15 : 0) +
    (volRatio > 0.15 ? 10 : 0) +
    Math.min(20, Math.abs(chg24) * 1.5)
  )

  return {
    id: coin.id,
    symbol: coin.symbol,
    name: coin.name,
    image: coin.image,
    type,
    score,
    confidence,
    reasons,
    price: coin.current_price,
    change24h: chg24,
    change7d: chg7d,
    isTrending: false,
    isSmallCap: (coin.market_cap || 0) < 500_000_000,
    timestamp: Date.now(),
  }
}

function calculateRSI(prices: number[], period = 14): number {
  if (prices.length < period + 1) return 50
  let gains = 0, losses = 0
  for (let i = prices.length - period; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1]
    if (diff > 0) gains += diff
    else losses += Math.abs(diff)
  }
  const avgGain = gains / period
  const avgLoss = losses / period
  if (avgLoss === 0) return 100
  const rs = avgGain / avgLoss
  return 100 - 100 / (1 + rs)
}

function calculateMACD(prices: number[]): 'bullish' | 'bearish' | 'neutral' {
  if (prices.length < 26) return 'neutral'
  const ema12 = ema(prices, 12)
  const ema26 = ema(prices, 26)
  const macdLine = ema12 - ema26
  const prev12 = ema(prices.slice(0, -1), 12)
  const prev26 = ema(prices.slice(0, -1), 26)
  const prevMacd = prev12 - prev26
  if (macdLine > 0 && prevMacd <= 0) return 'bullish'
  if (macdLine < 0 && prevMacd >= 0) return 'bearish'
  return 'neutral'
}

function ema(prices: number[], period: number): number {
  if (prices.length === 0) return 0
  const k = 2 / (period + 1)
  let val = prices[0]
  for (let i = 1; i < prices.length; i++) val = prices[i] * k + val * (1 - k)
  return val
}
