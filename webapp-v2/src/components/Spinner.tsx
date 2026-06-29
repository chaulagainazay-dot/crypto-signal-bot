interface Props { text?: string }

export default function Spinner({ text }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 20px', gap: 14 }}>
      <div style={{
        width: 32, height: 32,
        border: '3px solid #2A2A2A',
        borderTop: '3px solid #F7931A',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      {text && <div style={{ color: '#606060', fontSize: 13 }}>{text}</div>}
    </div>
  )
}
