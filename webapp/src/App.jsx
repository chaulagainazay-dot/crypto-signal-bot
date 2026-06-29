import { useState } from 'react'
import BottomNav from './components/BottomNav'
import Market from './tabs/Market'
import Signals from './tabs/Signals'
import Portfolio from './tabs/Portfolio'
import Research from './tabs/Research'
import Alerts from './tabs/Alerts'

export default function App() {
  const [tab, setTab]           = useState('market')
  const [researchCoin, setRC]   = useState(null)

  function goResearch(coinId) {
    setRC(coinId)
    setTab('research')
  }

  function renderTab() {
    switch (tab) {
      case 'market':    return <Market onResearch={goResearch} />
      case 'signals':   return <Signals />
      case 'portfolio': return <Portfolio />
      case 'research':  return <Research key={researchCoin} initialCoinId={researchCoin} />
      case 'alerts':    return <Alerts />
      default:          return <Market onResearch={goResearch} />
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', paddingBottom: 80 }}>
      {renderTab()}
      <BottomNav active={tab} onSelect={t => { setTab(t); if (t !== 'research') setRC(null) }} />
    </div>
  )
}
