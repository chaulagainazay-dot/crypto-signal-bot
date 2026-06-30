import { useState, useEffect, useCallback } from 'react'
import { useStore } from '../../store'
import { Spinner, Tag, ProgressBar, EmptyState, ChipRow } from '../../components/ui'
import type { MentorAnalysis } from '../../types'

const API = ''
const RISK_OPTIONS = [
  { value: 'conservative', label: 'Conservative' },
  { value: 'medium',       label: 'Medium'       },
  { value: 'aggressive',   label: 'Aggressive'   },
]

export default function MentorTab({ goPortfolio }: { goPortfolio: () => void }) {
  const { holdings } = useStore()
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [manualSymbol, setManualSymbol] = useState('')
  const [capital, setCapital] = useState('1000')
  const [risk, setRisk] = useState('medium')
  const [result, setResult] = useState<MentorAnalysis | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (holdings.length > 0) {
      const total = holdings.reduce((s, h) => s + h.buyPrice * h.amount, 0)
      setCapital(Math.round(total).toString())
    }
  }, [holdings])

  const symbol = manualSymbol.trim() ? manualSymbol.toUpperCase() : holdings[selectedIdx]?.symbol.toUpperCase() ?? 'BTC'

  const portfolio: Record<string, number> = {}
  for (const h of holdings) {
    portfolio[h.symbol.toUpperCase()] = (portfolio[h.symbol.toUpperCase()] || 0) + h.buyPrice * h.amount
  }

  const analyze = useCallback(async () => {
    setLoading(true); setResult(null)
    try {
      const r = await window.fetch(`${API}/api/v3/mentor?symbol=${symbol}&capital=${capital}&risk=${risk}`)
      setResult(await r.json() as MentorAnalysis)
    } catch { /* ignore */ }
    setLoading(false)
  }, [symbol, capital, risk])

  useEffect(() => { analyze() }, [analyze])

  const recColor = result?.recommendation === 'BUY' ? 'var(--green)' : result?.recommendation === 'SELL' ? 'var(--red)' : 'var(--accent)'
  const recCls   = result?.recommendation === 'BUY' ? 'badge-buy'   : result?.recommendation === 'SELL' ? 'badge-sell' : 'badge-hold'

  return (
    <div>
      {holdings.length === 0 && <EmptyState icon="💼" title="No holdings yet" sub="Add coins in Portfolio to get AI analysis."
        action={<button className="btn" onClick={goPortfolio}>Go to Portfolio →</button>} />}

      {/* Holding selector */}
      {holdings.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div className="section-label">Your Holdings</div>
          <div className="chip-row">
            {holdings.map((h, i) => (
              <button key={h.id} className={`chip${selectedIdx === i && !manualSymbol ? ' active' : ''}`}
                onClick={() => { setSelectedIdx(i); setManualSymbol('') }}>
                {h.image && <img src={h.image} style={{ width: 14, height: 14, borderRadius: '50%', verticalAlign: 'middle', marginRight: 4 }} />}
                {h.symbol.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input value={manualSymbol} onChange={e => setManualSymbol(e.target.value)} placeholder="or type symbol…"
          style={{ flex: 1, minWidth: 90 }} onKeyDown={e => e.key === 'Enter' && analyze()} />
        <input value={capital} onChange={e => setCapital(e.target.value)} type="number"
          placeholder="Capital $" style={{ width: 100 }} />
      </div>
      <div style={{ marginBottom: 14 }}>
        <ChipRow options={RISK_OPTIONS} active={risk} onChange={setRisk} />
      </div>

      {loading && <Spinner />}

      {result && !loading && (
        <>
          <div className="card">
            <div className="row" style={{ marginBottom: 12 }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>{symbol} Analysis</span>
              <span className={`badge ${recCls}`}>{result.recommendation}</span>
            </div>

            {result.risk_warnings.length > 0 && (
              <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 10, padding: '10px 12px', marginBottom: 12 }}>
                {result.risk_warnings.map((w, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--accent)', marginBottom: i < result.risk_warnings.length - 1 ? 4 : 0 }}>⚡ {w}</div>
                ))}
              </div>
            )}

            {result.reasons.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div className="section-label">Why</div>
                {result.reasons.map((r, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 4 }}>· {r}</div>
                ))}
              </div>
            )}

            {result.entry_conditions.length > 0 && (
              <div>
                <div className="section-label">Wait for</div>
                {result.entry_conditions.map((c, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 4 }}>✓ {c}</div>
                ))}
              </div>
            )}
          </div>

          {/* Allocation comparison */}
          <div className="card">
            <div className="section-label">Suggested vs Your Portfolio</div>
            {Object.entries(result.allocation).map(([asset, suggestedAmt]) => {
              const sugPct  = Number(capital) > 0 ? Math.round(suggestedAmt / Number(capital) * 100) : 0
              const actAmt  = portfolio[asset] ?? 0
              const actPct  = Number(capital) > 0 ? Math.round(actAmt / Number(capital) * 100) : 0
              const diff    = sugPct - actPct
              return (
                <div key={asset} style={{ marginBottom: 12 }}>
                  <div className="row" style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: 12, fontWeight: 700 }}>{asset}</span>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span className="muted" style={{ fontSize: 11 }}>You: {actPct}%</span>
                      <span style={{ fontSize: 11, color: 'var(--accent)' }}>Target: {sugPct}%</span>
                      {diff !== 0 && <Tag text={`${diff > 0 ? '+' : ''}${diff}%`} color={diff > 0 ? 'var(--green)' : 'var(--red)'} />}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <ProgressBar pct={actPct} color="var(--border)" height={4} />
                    <ProgressBar pct={sugPct} color="var(--accent)" height={4} />
                  </div>
                </div>
              )
            })}
            <div className="muted" style={{ fontSize: 10 }}>Gray = current · Amber = suggested</div>
          </div>
        </>
      )}
      <div className="muted" style={{ fontSize: 10, textAlign: 'center', marginTop: 4 }}>Educational only — not financial advice</div>
    </div>
  )
}
