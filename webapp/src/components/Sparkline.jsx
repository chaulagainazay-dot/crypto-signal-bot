export default function Sparkline({ prices, width = 300, height = 60, color = '#F7931A' }) {
  if (!prices || prices.length < 2) return null

  const vals = prices.map(p => (Array.isArray(p) ? p[1] : p))
  const min  = Math.min(...vals)
  const max  = Math.max(...vals)
  const range = max - min || 1

  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * width
    const y = height - ((v - min) / range) * height
    return `${x},${y}`
  }).join(' ')

  const isUp = vals[vals.length - 1] >= vals[0]
  const lineColor = color || (isUp ? '#00C853' : '#FF3D57')

  // gradient fill under line
  const gradId = `sg-${Math.random().toString(36).slice(2, 7)}`
  const fillPts = `0,${height} ${pts} ${width},${height}`

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 60, display: 'block' }}
      preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.3" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={fillPts} fill={`url(#${gradId})`} />
      <polyline points={pts} fill="none" stroke={lineColor} strokeWidth="2"
        strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}
