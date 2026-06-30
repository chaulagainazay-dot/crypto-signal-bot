import { useState } from 'react'
import { ChipRow } from '../components/ui'
import MentorTab from './v3/MentorTab'
import DoctorTab from './v3/DoctorTab'
import RiskTab   from './v3/RiskTab'
import IntelTab  from './v3/IntelTab'

type AITab = 'mentor' | 'doctor' | 'risk' | 'intel'

const AI_TABS: { value: AITab; label: string }[] = [
  { value: 'mentor', label: 'Mentor'  },
  { value: 'doctor', label: 'Doctor'  },
  { value: 'risk',   label: 'Risk'    },
  { value: 'intel',  label: 'Intel'   },
]

export default function V3Hub({ goPortfolio }: { goPortfolio: () => void }) {
  const [tab, setTab] = useState<AITab>('mentor')

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 14 }}>
        <h1 className="page-title">AI Hub</h1>
        <span className="badge badge-purple" style={{ fontSize: 10 }}>BETA</span>
      </div>

      <div style={{ marginBottom: 16 }}>
        <ChipRow options={AI_TABS} active={tab} onChange={setTab} purple />
      </div>

      {tab === 'mentor' && <MentorTab goPortfolio={goPortfolio} />}
      {tab === 'doctor' && <DoctorTab goPortfolio={goPortfolio} />}
      {tab === 'risk'   && <RiskTab   goPortfolio={goPortfolio} />}
      {tab === 'intel'  && <IntelTab  goPortfolio={goPortfolio} />}
    </div>
  )
}
