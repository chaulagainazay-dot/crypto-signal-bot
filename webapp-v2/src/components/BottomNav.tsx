import { hapticImpact } from '../utils/telegram'
import type { TabId } from '../types'

const TABS: { id: TabId; icon: string; label: string }[] = [
  { id: 'guide',     icon: '🤖', label: 'Guide'    },
  { id: 'signals',   icon: '🎯', label: 'Signals'  },
  { id: 'strategy',  icon: '📊', label: 'Strategy' },
  { id: 'portfolio', icon: '💼', label: 'Portfolio' },
  { id: 'research',  icon: '🔍', label: 'Research' },
]

interface Props { active: TabId; onSelect: (tab: TabId) => void }

export default function BottomNav({ active, onSelect }: Props) {
  return (
    <nav style={{
      display: 'flex', height: 64, background: '#111111',
      borderTop: '1px solid #1E1E1E', flexShrink: 0,
    }}>
      {TABS.map(tab => {
        const isActive = active === tab.id
        return (
          <button
            key={tab.id}
            onClick={() => { hapticImpact('light'); onSelect(tab.id) }}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', gap: 3, border: 'none', background: 'none',
              cursor: 'pointer', padding: '6px 0',
              color: isActive ? '#F7931A' : '#505050',
              transition: 'color 0.15s',
            }}
          >
            <span style={{ fontSize: 20, lineHeight: 1 }}>{tab.icon}</span>
            <span style={{ fontSize: 9, fontWeight: isActive ? 700 : 400, letterSpacing: 0.3 }}>
              {tab.label}
            </span>
            {isActive && (
              <div style={{
                position: 'absolute', bottom: 0, width: 24, height: 2,
                background: '#F7931A', borderRadius: 2,
              }} />
            )}
          </button>
        )
      })}
    </nav>
  )
}
