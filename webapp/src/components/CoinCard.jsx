import { fp } from '../api/coingecko'

export default function CoinCard({ coin, onClick, rank }) {
  const chg = coin.price_change_percentage_24h ?? 0
  const isUp = chg >= 0

  return (
    <div className="card" style={{ cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <div className="row">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {rank && <span style={{ color: '#404040', fontSize: 12, width: 20, flexShrink: 0 }}>#{rank}</span>}
          {coin.image && (
            <img src={coin.image} alt={coin.symbol} width={32} height={32}
              style={{ borderRadius: '50%', flexShrink: 0 }} />
          )}
          <div className="col">
            <strong style={{ fontSize: 14 }}>{coin.symbol?.toUpperCase()}</strong>
            <span className="muted">{coin.name}</span>
          </div>
        </div>
        <div className="col" style={{ alignItems: 'flex-end' }}>
          <strong style={{ fontSize: 15 }}>${fp(coin.current_price)}</strong>
          <span className={`badge badge-${isUp ? 'green' : 'red'}`}>
            {isUp ? '▲' : '▼'} {Math.abs(chg).toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  )
}
