import type { WebSocketPrice } from '../types'

const REST = 'https://api.binance.com'

export async function fetchBinanceKlines(symbol: string, interval = '1d', limit = 100): Promise<unknown[][]> {
  const r = await fetch(`${REST}/api/v3/klines?symbol=${symbol.toUpperCase()}&interval=${interval}&limit=${limit}`)
  if (!r.ok) throw new Error(`Binance ${r.status}`)
  return r.json()
}

export class BinanceWebSocket {
  private ws: WebSocket | null = null
  private callbacks = new Map<string, Set<(d: WebSocketPrice) => void>>()
  private reconnects = 0
  private symbols: string[] = []
  private connecting = false

  connect(symbols: string[]) {
    if (this.connecting) return
    this.symbols = symbols.map(s => s.toUpperCase())
    this.connecting = true
    const streams = this.symbols.map(s => `${s.toLowerCase()}@ticker`).join('/')
    const url = this.symbols.length === 1
      ? `wss://stream.binance.com:9443/ws/${streams}`
      : `wss://stream.binance.com:9443/stream?streams=${streams}`

    this.ws = new WebSocket(url)
    this.ws.onopen = () => { this.reconnects = 0; this.connecting = false }
    this.ws.onmessage = (e) => {
      const raw = JSON.parse(e.data)
      const t = raw.data || raw
      const data: WebSocketPrice = {
        symbol: t.s,
        price: parseFloat(t.c),
        change24h: parseFloat(t.p),
        changePercent24h: parseFloat(t.P),
        volume24h: parseFloat(t.v),
        high24h: parseFloat(t.h),
        low24h: parseFloat(t.l),
        lastUpdate: new Date(t.E),
      }
      this.callbacks.get(t.s)?.forEach(cb => cb(data))
    }
    this.ws.onclose = () => {
      this.connecting = false
      if (this.reconnects < 5) {
        this.reconnects++
        setTimeout(() => this.connect(this.symbols), 3000 * this.reconnects)
      }
    }
    this.ws.onerror = () => { this.connecting = false; this.ws?.close() }
  }

  subscribe(symbol: string, cb: (d: WebSocketPrice) => void) {
    const sym = symbol.toUpperCase()
    if (!this.callbacks.has(sym)) this.callbacks.set(sym, new Set())
    this.callbacks.get(sym)!.add(cb)
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN)
      this.connect(Array.from(this.callbacks.keys()))
  }

  unsubscribe(symbol: string, cb: (d: WebSocketPrice) => void) {
    const sym = symbol.toUpperCase()
    this.callbacks.get(sym)?.delete(cb)
    if (this.callbacks.get(sym)?.size === 0) this.callbacks.delete(sym)
  }

  disconnect() { this.ws?.close(); this.ws = null; this.callbacks.clear(); this.reconnects = 0 }
}

export const binanceWS = new BinanceWebSocket()
