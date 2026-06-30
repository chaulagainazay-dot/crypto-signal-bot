import { hapticImpact } from '../utils/telegram'
import type { TabId } from '../types'

// Minimal 20×20 SVG icons — single path, consistent 1.5px stroke
function IconBook() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 3h5a2 2 0 0 1 2 2v12l-3.5-2L4 17V3z"/>
      <path d="M11 5h5v12l-3.5-2-1.5 1"/>
    </svg>
  )
}
function IconSignal() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 14v2M7 10v6M11 7v9M15 4v12"/>
    </svg>
  )
}
function IconWallet() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="5" width="16" height="12" rx="2"/>
      <path d="M2 9h16"/>
      <circle cx="14.5" cy="13" r="1" fill="currentColor" stroke="none"/>
    </svg>
  )
}
function IconSearch() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="9" r="5"/>
      <path d="M16 16l-3.5-3.5"/>
    </svg>
  )
}
function IconSparkle() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 2v2M10 16v2M2 10h2M16 10h2"/>
      <path d="M10 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8z"/>
      <path d="M4.93 4.93l1.41 1.41M13.66 13.66l1.41 1.41M4.93 15.07l1.41-1.41M13.66 6.34l1.41-1.41"/>
    </svg>
  )
}

const TABS: { id: TabId; icon: React.ReactNode; label: string }[] = [
  { id: 'guide',     icon: <IconBook />,    label: 'Guide'     },
  { id: 'signals',   icon: <IconSignal />,  label: 'Signals'   },
  { id: 'portfolio', icon: <IconWallet />,  label: 'Portfolio' },
  { id: 'research',  icon: <IconSearch />,  label: 'Research'  },
  { id: 'v3',        icon: <IconSparkle />, label: 'AI'        },
]

interface Props { active: TabId; onSelect: (tab: TabId) => void }

export default function BottomNav({ active, onSelect }: Props) {
  return (
    <nav style={{
      display: 'flex',
      background: 'var(--surface)',
      borderTop: '1px solid var(--border)',
      flexShrink: 0,
      paddingBottom: 'env(safe-area-inset-bottom, 0px)',
    }}>
      {TABS.map(tab => {
        const isActive = active === tab.id
        const activeColor = tab.id === 'v3' ? 'var(--purple)' : 'var(--accent)'
        return (
          <button
            key={tab.id}
            onClick={() => { hapticImpact('light'); onSelect(tab.id) }}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', gap: 4, border: 'none', background: 'none',
              cursor: 'pointer', padding: '9px 0', position: 'relative', minWidth: 0,
              color: isActive ? activeColor : 'var(--text3)',
              transition: 'color 0.15s',
              fontFamily: 'inherit',
            }}
          >
            {tab.icon}
            <span style={{
              fontSize: 9, fontWeight: isActive ? 700 : 400,
              letterSpacing: 0.2, overflow: 'hidden',
              textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100%',
              paddingInline: 2,
            }}>
              {tab.label}
            </span>
            {isActive && (
              <div style={{
                position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)',
                width: 20, height: 2, background: activeColor, borderRadius: 2,
              }} />
            )}
          </button>
        )
      })}
    </nav>
  )
}
