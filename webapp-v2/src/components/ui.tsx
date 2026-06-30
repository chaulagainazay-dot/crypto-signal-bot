import type { CSSProperties, ReactNode } from 'react'

// ── Spinner ──────────────────────────────────────────────────────────────────
export function Spinner({ size = 24 }: { size?: number }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
      <div style={{
        width: size, height: size,
        border: `3px solid var(--border)`,
        borderTop: `3px solid var(--accent)`,
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
    </div>
  )
}

// ── Tag / Badge ──────────────────────────────────────────────────────────────
export function Tag({ text, color = 'var(--accent)' }: { text: string; color?: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      background: color + '22', color,
      fontSize: 11, fontWeight: 700,
      padding: '3px 8px', borderRadius: 6,
      whiteSpace: 'nowrap', lineHeight: 1,
    }}>{text}</span>
  )
}

// ── Progress Bar ─────────────────────────────────────────────────────────────
export function ProgressBar({ pct, color = 'var(--accent)', height = 4 }: { pct: number; color?: string; height?: number }) {
  return (
    <div className="progress-track" style={{ height }}>
      <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%`, background: color }} />
    </div>
  )
}

// ── Section Label ─────────────────────────────────────────────────────────────
export function SectionLabel({ children }: { children: ReactNode }) {
  return <div className="section-label">{children}</div>
}

// ── Stat Box ─────────────────────────────────────────────────────────────────
export function StatBox({ label, value, color, style }: { label: string; value: string; color?: string; style?: CSSProperties }) {
  return (
    <div className="stat-box" style={style}>
      <div className="label">{label}</div>
      <div className="value" style={color ? { color } : undefined}>{value}</div>
    </div>
  )
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function EmptyState({
  icon, title, sub, action,
}: { icon: string; title: string; sub?: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <div className="ei">{icon}</div>
      <div className="et">{title}</div>
      {sub && <div className="es">{sub}</div>}
      {action}
    </div>
  )
}

// ── Chip Row ──────────────────────────────────────────────────────────────────
export function ChipRow<T extends string>({
  options, active, onChange, purple,
}: { options: { value: T; label: string }[]; active: T; onChange: (v: T) => void; purple?: boolean }) {
  return (
    <div className="chip-row">
      {options.map(o => (
        <button
          key={o.value}
          className={`chip${active === o.value ? (purple ? ' active-purple' : ' active') : ''}`}
          onClick={() => onChange(o.value)}
        >{o.label}</button>
      ))}
    </div>
  )
}
