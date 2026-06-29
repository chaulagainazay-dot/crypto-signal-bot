import { useState, useEffect } from 'react'
import './App.css'
import { initTelegram, getTelegramUser } from './utils/telegram'
import { useStore } from './store'
import BottomNav from './components/BottomNav'
import ErrorBoundary from './components/ErrorBoundary'
import AccessGate from './components/AccessGate'
import Guide from './tabs/Guide'
import Signals from './tabs/Signals'
import Strategy from './tabs/Strategy'
import Portfolio from './tabs/Portfolio'
import Research from './tabs/Research'
import Alerts from './tabs/Alerts'
import type { TabId } from './types'

export default function App() {
  const [granted, setGranted] = useState(false)
  const { activeTab, setActiveTab, setUser, researchCoinId } = useStore()

  useEffect(() => {
    initTelegram()
    const user = getTelegramUser()
    if (user) setUser({ telegramId: user.id, username: user.username ?? null })
  }, [])

  function renderTab() {
    switch (activeTab as TabId) {
      case 'guide':     return <Guide />
      case 'signals':   return <Signals />
      case 'strategy':  return <Strategy />
      case 'portfolio': return <Portfolio />
      case 'research':  return <Research initialCoinId={researchCoinId} />
      case 'alerts':    return <Alerts />
      default:          return <Guide />
    }
  }

  if (!granted) return <AccessGate onGranted={() => setGranted(true)} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', background: 'var(--bg)', overflow: 'hidden' }}>
      <ErrorBoundary>
        {renderTab()}
      </ErrorBoundary>
      <BottomNav active={activeTab as TabId} onSelect={t => { setActiveTab(t); }} />
    </div>
  )
}
