import { useState, useEffect } from 'react'
import { useStore } from '../../store'
import { EmptyState, Tag } from '../../components/ui'
import type { RiskResult } from '../../types'

const API = ''

export default function RiskTab({ goPortfolio }: { goPortfolio: () => void }) {
  const { holdings } = useStore()
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [symbol, setSymbol] = useState('')
  const [entry, setEntry] = useState('')
  const [stop, setStop] = useState('')
  const [target, setTarget] = useState('')
  const [capital, setCapital] = useState('1000')
  const [result, setResult] = useState<RiskResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    const h = holdings[selectedIdx]
    if (!h) return
    setSymbol(h.symbol.toUpperCase())
    setEntry(h.buyPrice.toString())
    setStop((h.buyPrice * 0.95).toFixed(4))
    setTarget((h.buyPrice * 1.15).toFixed(4))
  }, [selectedIdx, holdings])

  useEffect(() => {
    if (holdings.length > 0) {
      const total = holdings.reduce((s, h) => s + h.buyPrice * h.amount, 0)
      setCapital(Math.round(total).toString())
    }
  }, [holdings])

  async function calculate() {
    if (!entry || !stop || !target) { setErr('Fill in entry, stop and target.'); return }
    setErr(''); setLoading(true)
    try {
      const url = `${API}/api/v3/risk?symbol=${symbol}&entry=${entry}&stop=${stop}&target=${target}&capital=${capital}`
      const r = await window.fetch(url)
      setResult(await r.json() as RiskResult)
    } catch { setErr('Network error') }
    setLoading(false)
  }

  if (holdings.length === 0) return <EmptyState icon="⚖️" title="No holdings" sub="Add coins in Portfolio to use the risk calculator."
    action={<button className="btn" onClick={goPortfolio}>Go to Portfolio →</button>} />

  return (
    <div>
      {/* Holding selector */}
      <div style={{ marginBottom: 12 }}>
        <div className="section-label">Select Holding</div>
        <div className="chip-row">
          {holdings.map((h, i) => (
            <button key={h.id} className={`chip${selectedIdx === i ? ' active' : ''}`} onClick={() => setSelectedIdx(i)}>
              {h.image && <img src={h.image} style={{ width: 14, height: 14, borderRadius: '50%', verticalAlign: 'middle', marginRight: 4 }} />}
              {h.symbol.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Input grid */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-label">Trade Parameters</div>
        <div className="stat-grid-2" style={{ gap: 10 }}>
          <div>
            <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Symbol</div>
            <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} />
          </div>
          <div>
            <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Capital ($)</div>
            <input value={capital} onChange={e => setCapital(e.target.value)} type="number" />
          </div>
          <div>
            <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Entry Price</div>
            <input value={entry} onChange={e => setEntry(e.target.value)} type="number" />
          </div>
          <div>
            <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Stop Loss</div>
            <input value={stop} onChange={e => setStop(e.target.value)} type="number" />
          </div>
        </div>
        <div style={{ marginTop: 10 }}>
          <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>Target Price</div>
          <input value={target} onChange={e => setTarget(e.target.value)} type="number" />
        </div>
      </div>

      {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 8 }}>{err}</div>}
      <button className="btn" onClick={calculate} disabled={loading} style={{ marginBottom: 14 }}>
        {loading ? 'Calculating…' : 'Calculate Risk'}
      </button>

      {result && !loading && (() => {
        const rr = result.risk_reward_ratio
        const rrColor = rr >= 2 ? 'var(--green)' : rr >= 1 ? 'var(--accent)' : 'var(--red)'
        return (
          <>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-around' }}>
                {[
                  { label: 'Risk',    val: result.risk_level,   color: result.risk_level === 'Low' ? 'var(--green)' : result.risk_level === 'Medium' ? 'var(--accent)' : 'var(--red)' },
                  { label: 'Reward',  val: result.reward_level, color: result.reward_level === 'High' ? 'var(--green)' : 'var(--accent)' },
                  { label: 'R:R',     val: `1:${rr.toFixed(1)}`, color: rrColor },
                ].map(({ label, val, color }) => (
                  <div key={label} style={{ textAlign: 'center' }}>
                    <div className="muted" style={{ fontSize: 10, marginBottom: 6 }}>{label}</div>
                    <Tag text={val} color={color} />
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <div className="section-label">Position Sizing</div>
              {[
                { label: 'Position Size', val: `$${result.position_size.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${result.position_size_percent.toFixed(1)}%)`, color: 'var(--text)' },
                { label: 'Max Loss',      val: `-$${result.max_loss.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: 'var(--red)' },
                { label: 'Max Gain',      val: `+$${result.max_gain.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: 'var(--green)' },
              ].map(({ label, val, color }) => (
                <div key={label} className="row" style={{ marginBottom: 10 }}>
                  <span className="muted">{label}</span>
                  <span style={{ fontSize: 14, fontWeight: 700, color }}>{val}</span>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="section-label">Scenarios</div>
              {[
                { label: 'Best Case',  val: `+$${result.scenarios.best_case.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,          color: 'var(--green)' },
                { label: 'Base Case',  val: `+$${result.scenarios.base_case.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,          color: 'var(--accent)' },
                { label: 'Worst Case', val: `-$${Math.abs(result.scenarios.worst_case).toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: 'var(--red)' },
              ].map(({ label, val, color }) => (
                <div key={label} className="row" style={{ marginBottom: 10 }}>
                  <span className="muted">{label}</span>
                  <span style={{ fontSize: 14, fontWeight: 700, color }}>{val}</span>
                </div>
              ))}
            </div>
          </>
        )
      })()}
    </div>
  )
}
