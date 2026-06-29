interface Props { height?: number; width?: string; borderRadius?: number }

export default function Skeleton({ height = 20, width = '100%', borderRadius = 8 }: Props) {
  return (
    <div style={{
      height, width, borderRadius,
      background: '#1A1A1A',
      animation: 'pulse 1.5s ease-in-out infinite',
    }} />
  )
}

export function SkeletonCard() {
  return (
    <div style={{ background: '#141414', border: '1px solid #2A2A2A', borderRadius: 12, padding: '14px 16px', marginBottom: 10 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
        <Skeleton height={36} width="36px" borderRadius={18} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <Skeleton height={14} width="40%" />
          <Skeleton height={11} width="25%" />
        </div>
        <Skeleton height={20} width="60px" />
      </div>
      <Skeleton height={3} />
    </div>
  )
}
