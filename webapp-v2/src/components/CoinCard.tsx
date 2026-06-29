import type { Coin } from '../types'
import { fp, fmcap } from '../api/coingecko'
import Sparkline from './Sparkline'

interface Props {
  coin: Coin
  currency?: string
  onClick?: () => void
  wsPrice?: number
}

export default function CoinCard({ coin, onClick, wsPrice }: Props) {
  const price = wsPrice ?? coin.current_price
  const chg = coin.price_change_percentage_24h || 0
  const pos = chg >= 0

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '12px 0', borderBottom: '1px solid #1E1E1E',
        cursor: onClick ? 'pointer' : 'default',
      }}
    >
      <img src={coin.image} width={36} height={36} style={{ borderRadius: '50%' }}
        onError={e => ((e.target as HTMLImageElement).style.display = 'none')} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14 }}>{coin.symbol.toUpperCase()}</div>
        <div style={{ color: '#606060', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {coin.name}
        </div>
      </div>
      {coin.sparkline_in_7d?.price && (
        <Sparkline prices={coin.sparkline_in_7d.price} width={60} height={28} positive={pos} />
      )}
      <div style={{ textAlign: 'right', minWidth: 80 }}>
        <div style={{ fontWeight: 700, fontSize: 14 }}>${fp(price)}</div>
        <div style={{
          fontSize: 12, fontWeight: 600,
          color: pos ? '#00C853' : '#FF3D57',
        }}>
          {pos ? '▲' : '▼'} {Math.abs(chg).toFixed(2)}%
        </div>
      </div>
    </div>
  )
}

export function CoinCardCompact({ coin, onClick }: Props) {
  const chg = coin.price_change_percentage_24h || 0
  const pos = chg >= 0
  return (
    <div onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid #1A1A1A', cursor: onClick ? 'pointer' : 'default' }}>
      <span style={{ color: '#404040', fontSize: 11, width: 22 }}>#{coin.market_cap_rank}</span>
      {coin.image && <img src={coin.image} width={28} height={28} style={{ borderRadius: '50%' }} onError={e => ((e.target as HTMLImageElement).style.display = 'none')} />}
      <div style={{ flex: 1 }}>
        <strong style={{ fontSize: 13 }}>{coin.symbol.toUpperCase()}</strong>
        <div style={{ color: '#505050', fontSize: 11 }}>{fmcap(coin.market_cap)}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontWeight: 600, fontSize: 13 }}>${fp(coin.current_price)}</div>
        <div style={{ fontSize: 11, color: pos ? '#00C853' : '#FF3D57' }}>
          {pos ? '▲' : '▼'}{Math.abs(chg).toFixed(2)}%
        </div>
      </div>
    </div>
  )
}
