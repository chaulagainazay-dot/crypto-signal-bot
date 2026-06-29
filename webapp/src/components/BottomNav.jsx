const TABS = [
  { id: 'guide',     icon: '🤖', label: 'Guide'     },
  { id: 'signals',   icon: '🎯', label: 'Signals'   },
  { id: 'strategy',  icon: '📊', label: 'Strategy'  },
  { id: 'portfolio', icon: '💼', label: 'Portfolio'  },
  { id: 'research',  icon: '🔍', label: 'Research'   },
]

export default function BottomNav({ active, onSelect }) {
  return (
    <nav style={{
      position: 'fixed',
      bottom: 0, left: 0, right: 0,
      height: 'calc(64px + env(safe-area-inset-bottom, 0px))',
      background: '#141414',
      borderTop: '1px solid #2A2A2A',
      display: 'flex',
      zIndex: 100,
    }}>
      {TABS.map(t => {
        const isActive = active === t.id
        return (
          <button key={t.id} onClick={() => onSelect(t.id)} style={{
            flex: 1,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 3,
            paddingBottom: 'env(safe-area-inset-bottom, 0px)',
            color: isActive ? '#F7931A' : '#505050',
            transition: 'color 0.15s',
            position: 'relative',
          }}>
            {isActive && (
              <div style={{
                position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)',
                width: 24, height: 2, background: '#F7931A', borderRadius: 2,
              }} />
            )}
            <span style={{ fontSize: 20 }}>{t.icon}</span>
            <span style={{ fontSize: 10, fontWeight: isActive ? 700 : 400 }}>{t.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
