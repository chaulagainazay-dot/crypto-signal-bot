interface Props { prices: number[]; width?: number; height?: number; positive?: boolean }

export default function Sparkline({ prices, width = 80, height = 32, positive }: Props) {
  if (!prices || prices.length < 2) return null
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const range = max - min || 1
  const pts = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * width
    const y = height - ((p - min) / range) * height
    return `${x},${y}`
  }).join(' ')
  const color = positive !== undefined ? (positive ? '#00C853' : '#FF3D57')
    : (prices[prices.length - 1] >= prices[0] ? '#00C853' : '#FF3D57')
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
