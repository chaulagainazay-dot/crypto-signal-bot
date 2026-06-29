import { useState } from 'react'
import BottomNav from './components/BottomNav'
import Guide from './tabs/Guide'
import Signals from './tabs/Signals'
import Strategy from './tabs/Strategy'
import Portfolio from './tabs/Portfolio'
import Research from './tabs/Research'
import Alerts from './tabs/Alerts'

export default function App() {
  const [tab, setTab]           = useState('guide')
  const [researchCoin, setRC]   = useState(null)

  function goResearch(coinId) {
    setRC(coinId)
    setTab('research')
  }

  function renderTab() {
    switch (tab) {
      case 'guide':     return <Guide />
      case 'signals':   return <Signals />
      case 'strategy':  return <Strategy />
      case 'portfolio': return <Portfolio />
      case 'research':  return <Research key={researchCoin} initialCoinId={researchCoin} />
      case 'alerts':    return <Alerts />
      default:          return <Guide />
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', height: '100vh', background: 'var(--bg)', overflow: 'hidden' }}>
      {renderTab()}
      <BottomNav active={tab} onSelect={t => { setTab(t); if (t !== 'research') setRC(null) }} />
    </div>
  )
}
