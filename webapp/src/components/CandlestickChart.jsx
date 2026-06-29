import { fp } from '../api/coingecko'

const W = 320
const H = 180
const PAD = { top: 24, right: 8, bottom: 32, left: 52 }
const CW  = W - PAD.left - PAD.right
const CH  = H - PAD.top  - PAD.bottom

function niceNum(range, round) {
  const exp   = Math.floor(Math.log10(range))
  const frac  = range / Math.pow(10, exp)
  let nice
  if (round) { nice = frac < 1.5 ? 1 : frac < 3 ? 2 : frac < 7 ? 5 : 10 }
  else        { nice = frac <= 1 ? 1 : frac <= 2 ? 2 : frac <= 5 ? 5 : 10 }
  return nice * Math.pow(10, exp)
}

export default function CandlestickChart({ candles, signal }) {
  if (!candles || candles.length < 2) return null

  const prices = candles.flatMap(c => [c[2], c[3]])
  const rawMin = Math.min(...prices)
  const rawMax = Math.max(...prices)
  const range  = niceNum(rawMax - rawMin || rawMax * 0.02, false)
  const step   = niceNum(range / 4, true)
  const yMin   = Math.floor(rawMin / step) * step
  const yMax   = Math.ceil(rawMax  / step) * step

  const yScale = v => CH - ((v - yMin) / (yMax - yMin)) * CH
  const xScale = i => (i / (candles.length - 1)) * CW

  const ticks = []
  for (let t = yMin; t <= yMax + step * 0.01; t += step) ticks.push(t)

  // Signal zone background
  const sigColor = signal
    ? signal.score >= 72 ? '#00E676'
    : signal.score >= 58 ? '#00C853'
    : signal.score >= 42 ? '#F7931A'
    : signal.score >= 28 ? '#FF3D57'
    : '#FF1744'
    : '#808080'

  const candleW = Math.max(2, CW / candles.length * 0.6)

  return (
    <div style={{ position: 'relative' }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', display: 'block' }}
        preserveAspectRatio="xMidYMid meet"
      >
        <g transform={`translate(${PAD.left},${PAD.top})`}>

          {/* Grid lines + Y labels */}
          {ticks.map((t, i) => {
            const y = yScale(t)
            if (y < -2 || y > CH + 2) return null
            return (
              <g key={i}>
                <line x1={0} y1={y} x2={CW} y2={y}
                  stroke="#2A2A2A" strokeWidth="1" strokeDasharray="3,3" />
                <text x={-4} y={y + 4} textAnchor="end"
                  fill="#606060" fontSize="9">
                  {t >= 1000 ? `${(t/1000).toFixed(1)}k` : fp(t)}
                </text>
              </g>
            )
          })}

          {/* Signal zone tint behind candles */}
          {signal && (
            <rect x={0} y={0} width={CW} height={CH}
              fill={sigColor} fillOpacity="0.04" rx="4" />
          )}

          {/* Candles */}
          {candles.map((c, i) => {
            const [, open, high, low, close] = c
            const x    = xScale(i)
            const isUp = close >= open
            const col  = isUp ? '#00C853' : '#FF3D57'
            const yO   = yScale(open)
            const yC   = yScale(close)
            const yH   = yScale(high)
            const yL   = yScale(low)
            const bodyTop = Math.min(yO, yC)
            const bodyH   = Math.max(1, Math.abs(yO - yC))
            return (
              <g key={i}>
                {/* Wick */}
                <line x1={x} y1={yH} x2={x} y2={yL}
                  stroke={col} strokeWidth="1" />
                {/* Body */}
                <rect
                  x={x - candleW / 2}
                  y={bodyTop}
                  width={candleW}
                  height={bodyH}
                  fill={col}
                  rx="1"
                />
              </g>
            )
          })}

          {/* Buy/Sell annotation */}
          {signal && (
            <text x={CW} y={-8} textAnchor="end"
              fill={sigColor} fontSize="10" fontWeight="700">
              {signal.icon} {signal.label}
            </text>
          )}

          {/* X axis labels — first and last date */}
          {candles.length > 0 && (() => {
            const fmt = ts => {
              const d = new Date(ts)
              return `${d.getDate()}/${d.getMonth()+1}`
            }
            return (
              <>
                <text x={0} y={CH + 14} fill="#505050" fontSize="9">{fmt(candles[0][0])}</text>
                <text x={CW} y={CH + 14} textAnchor="end" fill="#505050" fontSize="9">
                  {fmt(candles[candles.length-1][0])}
                </text>
              </>
            )
          })()}

          {/* Axes */}
          <line x1={0} y1={0} x2={0} y2={CH} stroke="#3A3A3A" strokeWidth="1" />
          <line x1={0} y1={CH} x2={CW} y2={CH} stroke="#3A3A3A" strokeWidth="1" />
        </g>
      </svg>
    </div>
  )
}
