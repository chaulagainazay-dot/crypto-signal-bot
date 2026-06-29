import { useEffect, useState, useCallback, useRef } from 'react'
import { binanceWS } from '../api/binance'
import type { WebSocketPrice } from '../types'

export function useBinancePrice(symbols: string[]) {
  const [prices, setPrices] = useState<Record<string, WebSocketPrice>>({})
  const [connected, setConnected] = useState(false)
  const key = symbols.join(',')
  const keyRef = useRef(key)
  keyRef.current = key

  const handleUpdate = useCallback((data: WebSocketPrice) => {
    setPrices(prev => ({ ...prev, [data.symbol]: data }))
  }, [])

  useEffect(() => {
    if (symbols.length === 0) return
    setConnected(true)
    symbols.forEach(s => binanceWS.subscribe(s + 'USDT', handleUpdate))
    return () => { symbols.forEach(s => binanceWS.unsubscribe(s + 'USDT', handleUpdate)) }
  }, [key]) // eslint-disable-line react-hooks/exhaustive-deps

  return { prices, connected }
}
