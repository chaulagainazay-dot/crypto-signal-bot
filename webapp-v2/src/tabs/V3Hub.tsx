import { useState, useEffect, type CSSProperties } from 'react'
import type { MentorAnalysis, DoctorReport, RiskResult, WhaleData, NewsBrief } from '../types'
import { useStore } from '../store'

const API = ''
type Pill = 'mentor' | 'doctor' | 'risk' | 'intel'

// ─── helpers ──────────────────────────────────────────────────────────────────
function Card({ children, style }: { children: React.ReactNode; style?: CSSProperties }) {
  return (
    <div style={{
      background: '#141414', border: '1px solid #222', borderRadius: 14,
      padding: '16px', marginBottom: 12, ...style,
    }}>
      {children}
    </div>
  )
}

function Tag({ text, color = '#F7931A' }: { text: string; color?: string }) {
  return (
    <span style={{
      background: color + '22', color, fontSize: 11, fontWeight: 700,
      padding: '3px 8px', borderRadius: 20, letterSpacing: 0.4,
    }}>{text}</span>
  )
}

function Score({ value, max = 100 }: { value: number; max?: number }) {
  const pct = (value / max) * 100
  const color = value >= 70 ? '#22c55e' : value >= 40 ? '#f59e0b' : '#ef4444'
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: '#808080' }}>Score</span>
        <span style={{ fontWeight: 700, color }}>{value}/{max}</span>
      </div>
      <div style={{ height: 6, background: '#222', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width 0.5s' }} />
      </div>
    </div>
  )
}

function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
      <div style={{
        width: 28, height: 28, border: '3px solid #222', borderTop: '3px solid #F7931A',
        borderRadius: '50%', animation: 'spin 0.8s linear infinite',
      }} />
    </div>
  )
}

// ─── MENTOR ───────────────────────────────────────────────────────────────────
function MentorTab() {
  const [symbol, setSymbol] = useState('BTC')
  const [input, setInput] = useState('BTC')
  const [capital, setCapital] = useState('1000')
  const [risk, setRisk] = useState('medium')
  const [result, setResult] = useState<MentorAnalysis | null>(null)
  const [loading, setLoading] = useState(false)

  async function fetch() {
    setLoading(true)
    try {
      const r = await window.fetch(`${API}/api/v3/mentor?symbol=${symbol}&capital=${capital}&risk=${risk}`)
      setResult(await r.json() as MentorAnalysis)
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { fetch() }, [symbol, capital, risk]) // eslint-disable-line react-hooks/exhaustive-deps

  const recColor = result?.recommendation === 'BUY' ? '#22c55e' : result?.recommendation === 'SELL' ? '#ef4444' : '#f59e0b'

  return (
    <div>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && setSymbol(input)}
          placeholder="Symbol"
          style={inputStyle}
        />
        <button onClick={() => setSymbol(input)} style={btnSmall}>Analyze</button>
        <select value={risk} onChange={e => setRisk(e.target.value)} style={inputStyle}>
          <option value="conservative">Conservative</option>
          <option value="medium">Medium</option>
          <option value="aggressive">Aggressive</option>
        </select>
        <input
          value={capital}
          onChange={e => setCapital(e.target.value)}
          placeholder="Capital $"
          type="number"
          style={{ ...inputStyle, width: 90 }}
        />
      </div>

      {loading && <Spinner />}

      {result && !loading && (
        <>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontWeight: 700, fontSize: 16 }}>🤖 {symbol} Analysis</span>
              <Tag text={result.recommendation} color={recColor} />
            </div>

            {result.risk_warnings.length > 0 && (
              <div style={{ background: '#f59e0b11', border: '1px solid #f59e0b33', borderRadius: 10, padding: 10, marginBottom: 12 }}>
                {result.risk_warnings.map((w, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#f59e0b', marginBottom: 3 }}>⚡ {w}</div>
                ))}
              </div>
            )}

            {result.reasons.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: '#606060', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>Why</div>
                {result.reasons.map((r, i) => <div key={i} style={{ fontSize: 13, color: '#C0C0C0', marginBottom: 4 }}>• {r}</div>)}
              </div>
            )}

            {result.entry_conditions.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: '#606060', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>Wait for</div>
                {result.entry_conditions.map((c, i) => (
                  <div key={i} style={{ fontSize: 13, color: '#C0C0C0', marginBottom: 4 }}>✔ {c}</div>
                ))}
              </div>
            )}
          </Card>

          {Object.keys(result.allocation).length > 0 && (
            <Card>
              <div style={{ fontSize: 12, color: '#606060', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                💼 Suggested Allocation (${Number(capital).toLocaleString()})
              </div>
              {Object.entries(result.allocation).map(([asset, amount]) => {
                const pct = Math.round((amount / Number(capital)) * 100)
                return (
                  <div key={asset} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <div style={{ width: 40, fontSize: 12, fontWeight: 700, color: '#E0E0E0' }}>{asset}</div>
                    <div style={{ flex: 1, height: 6, background: '#222', borderRadius: 3 }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: '#F7931A', borderRadius: 3 }} />
                    </div>
                    <div style={{ fontSize: 12, color: '#E0E0E0', minWidth: 60, textAlign: 'right' }}>${amount.toLocaleString()}</div>
                    <div style={{ fontSize: 11, color: '#606060', minWidth: 28, textAlign: 'right' }}>{pct}%</div>
                  </div>
                )
              })}
            </Card>
          )}
        </>
      )}

      <div style={{ fontSize: 10, color: '#404040', textAlign: 'center', marginTop: 8 }}>
        Educational only — not financial advice
      </div>
    </div>
  )
}

// ─── DOCTOR ───────────────────────────────────────────────────────────────────
function DoctorTab() {
  const { holdings } = useStore()
  const [result, setResult] = useState<DoctorReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  async function runDiagnosis() {
    if (holdings.length === 0) { setErr('No holdings. Add some in Portfolio tab first.'); return }
    setErr(''); setLoading(true)
    const portfolio: Record<string, number> = {}
    for (const h of holdings) portfolio[h.symbol] = (portfolio[h.symbol] || 0) + h.buyPrice * h.amount
    try {
      const r = await window.fetch(`${API}/api/v3/doctor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio }),
      })
      setResult(await r.json() as DoctorReport)
    } catch { setErr('Network error') }
    setLoading(false)
  }

  const statusColor = result?.health_status === 'HEALTHY' ? '#22c55e'
    : result?.health_status === 'NEEDS_ATTENTION' ? '#f59e0b' : '#ef4444'

  return (
    <div>
      <button onClick={runDiagnosis} disabled={loading} style={{ ...btnFull, marginBottom: 16 }}>
        {loading ? '🔍 Diagnosing…' : '🏥 Run Portfolio Diagnosis'}
      </button>

      {err && <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 12 }}>{err}</div>}
      {loading && <Spinner />}

      {result && !loading && (
        <>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <span style={{ fontWeight: 700, fontSize: 16 }}>Portfolio Health</span>
              <Tag text={result.health_status.replace('_', ' ')} color={statusColor} />
            </div>
            <Score value={result.overall_score} />
          </Card>

          {result.problems.length > 0 && (
            <Card>
              <div style={{ fontSize: 12, color: '#ef4444', marginBottom: 8, fontWeight: 600 }}>❌ Problems Found</div>
              {result.problems.map((p, i) => <div key={i} style={{ fontSize: 13, color: '#C0C0C0', marginBottom: 5 }}>• {p}</div>)}
            </Card>
          )}

          {result.recommendations.length > 0 && (
            <Card>
              <div style={{ fontSize: 12, color: '#22c55e', marginBottom: 8, fontWeight: 600 }}>💡 Recommendations</div>
              {result.recommendations.map((r, i) => (
                <div key={i} style={{ fontSize: 13, color: '#C0C0C0', marginBottom: 5 }}>{i + 1}. {r}</div>
              ))}
            </Card>
          )}

          <Card>
            <div style={{ fontSize: 12, color: '#606060', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Target Allocation</div>
            {Object.entries(result.target_allocation).map(([asset, pct]) => (
              <div key={asset} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 40, fontSize: 12, fontWeight: 700 }}>{asset.toUpperCase()}</div>
                <div style={{ flex: 1, height: 6, background: '#222', borderRadius: 3 }}>
                  <div style={{ height: '100%', width: `${pct * 100}%`, background: '#F7931A', borderRadius: 3 }} />
                </div>
                <div style={{ fontSize: 12, color: '#E0E0E0' }}>{Math.round(pct * 100)}%</div>
              </div>
            ))}
          </Card>

          <Card>
            <div style={{ fontSize: 12, color: '#606060', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Score Breakdown</div>
            {Object.entries(result.breakdown).map(([key, val]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 12, color: '#808080', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: val >= 70 ? '#22c55e' : val >= 40 ? '#f59e0b' : '#ef4444' }}>{Math.round(val)}</span>
              </div>
            ))}
          </Card>
        </>
      )}
    </div>
  )
}

// ─── RISK METER ───────────────────────────────────────────────────────────────
function RiskTab() {
  const [symbol, setSymbol] = useState('BTC')
  const [entry, setEntry] = useState('')
  const [stop, setStop] = useState('')
  const [target, setTarget] = useState('')
  const [capital, setCapital] = useState('1000')
  const [result, setResult] = useState<RiskResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

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

  const rr = result?.risk_reward_ratio ?? 0

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
        <div>
          <Label>Symbol</Label>
          <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} style={inputFull} />
        </div>
        <div>
          <Label>Capital ($)</Label>
          <input value={capital} onChange={e => setCapital(e.target.value)} type="number" style={inputFull} />
        </div>
        <div>
          <Label>Entry Price</Label>
          <input value={entry} onChange={e => setEntry(e.target.value)} type="number" style={inputFull} placeholder="e.g. 105000" />
        </div>
        <div>
          <Label>Stop Loss</Label>
          <input value={stop} onChange={e => setStop(e.target.value)} type="number" style={inputFull} placeholder="e.g. 102000" />
        </div>
        <div style={{ gridColumn: 'span 2' }}>
          <Label>Target Price</Label>
          <input value={target} onChange={e => setTarget(e.target.value)} type="number" style={inputFull} placeholder="e.g. 115000" />
        </div>
      </div>
      {err && <div style={{ color: '#ef4444', fontSize: 12, marginBottom: 8 }}>{err}</div>}
      <button onClick={calculate} disabled={loading} style={{ ...btnFull, marginBottom: 16 }}>
        {loading ? 'Calculating…' : '⚖️ Calculate Risk'}
      </button>

      {loading && <Spinner />}

      {result && !loading && (
        <>
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: 10, color: '#606060', marginBottom: 4 }}>RISK</div>
                <Tag text={result.risk_level} color={result.risk_level === 'Low' ? '#22c55e' : result.risk_level === 'Medium' ? '#f59e0b' : '#ef4444'} />
              </div>
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: 10, color: '#606060', marginBottom: 4 }}>REWARD</div>
                <Tag text={result.reward_level} color={result.reward_level === 'High' ? '#22c55e' : result.reward_level === 'Medium' ? '#f59e0b' : '#ef4444'} />
              </div>
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: 10, color: '#606060', marginBottom: 4 }}>R:R</div>
                <span style={{ fontWeight: 700, fontSize: 15, color: rr >= 2 ? '#22c55e' : rr >= 1 ? '#f59e0b' : '#ef4444' }}>
                  1:{rr.toFixed(1)}
                </span>
              </div>
            </div>
          </Card>

          <Card>
            <div style={{ fontSize: 12, color: '#606060', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Position Sizing</div>
            {[
              ['Position Size', `$${result.position_size.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${result.position_size_percent.toFixed(1)}%)`, '#E0E0E0'],
              ['Max Loss', `-$${result.max_loss.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, '#ef4444'],
              ['Max Gain', `+$${result.max_gain.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, '#22c55e'],
            ].map(([label, val, color]) => (
              <div key={label as string} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: '#808080' }}>{label}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: color as string }}>{val}</span>
              </div>
            ))}
          </Card>

          <Card>
            <div style={{ fontSize: 12, color: '#606060', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Scenario Analysis</div>
            {[
              ['🏆 Best Case', `+$${result.scenarios.best_case.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, '#22c55e'],
              ['📊 Base Case', `+$${result.scenarios.base_case.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, '#f59e0b'],
              ['💀 Worst Case', `-$${Math.abs(result.scenarios.worst_case).toLocaleString(undefined, { maximumFractionDigits: 0 })}`, '#ef4444'],
            ].map(([label, val, color]) => (
              <div key={label as string} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: '#808080' }}>{label}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: color as string }}>{val}</span>
              </div>
            ))}
          </Card>
        </>
      )}
    </div>
  )
}

// ─── WHALE + NEWS INTEL ───────────────────────────────────────────────────────
function IntelTab() {
  const [symbol, setSymbol] = useState('BTC')
  const [whaleInput, setWhaleInput] = useState('BTC')
  const [whale, setWhale] = useState<WhaleData | null>(null)
  const [brief, setBrief] = useState<NewsBrief | null>(null)
  const [loadingWhale, setLoadingWhale] = useState(false)
  const [loadingBrief, setLoadingBrief] = useState(false)

  async function fetchWhale() {
    setLoadingWhale(true)
    try {
      const r = await window.fetch(`${API}/api/v3/whale?symbol=${symbol}`)
      setWhale(await r.json() as WhaleData)
    } catch { /* ignore */ }
    setLoadingWhale(false)
  }

  async function fetchBrief() {
    setLoadingBrief(true)
    try {
      const r = await window.fetch(`${API}/api/v3/brief`)
      setBrief(await r.json() as NewsBrief)
    } catch { /* ignore */ }
    setLoadingBrief(false)
  }

  useEffect(() => { fetchWhale(); fetchBrief() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div>
      {/* Whale */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        <input
          value={whaleInput}
          onChange={e => setWhaleInput(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && (setSymbol(whaleInput), setTimeout(fetchWhale, 50))}
          placeholder="Symbol"
          style={{ ...inputStyle, flex: 1 }}
        />
        <button onClick={() => { setSymbol(whaleInput); setTimeout(fetchWhale, 50) }} style={btnSmall}>
          Track
        </button>
      </div>

      {loadingWhale ? <Spinner /> : whale && (
        <Card>
          <div style={{ fontWeight: 700, marginBottom: 10 }}>🐋 Whale Intelligence: {whale.symbol}</div>
          <div style={{
            background: whale.whale_accumulation ? '#22c55e11' : '#ef444411',
            border: `1px solid ${whale.whale_accumulation ? '#22c55e33' : '#ef444433'}`,
            borderRadius: 10, padding: 10, marginBottom: 12, fontSize: 13,
            color: whale.whale_accumulation ? '#22c55e' : '#ef4444',
          }}>
            {whale.interpretation}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            {[
              ['Inflow', `$${whale.exchange_flows.inflow}M`, '#ef4444'],
              ['Outflow', `$${whale.exchange_flows.outflow}M`, '#22c55e'],
              ['Net', `${whale.exchange_flows.net > 0 ? '+' : ''}$${whale.exchange_flows.net}M`, whale.exchange_flows.net < 0 ? '#22c55e' : '#ef4444'],
            ].map(([label, val, color]) => (
              <div key={label as string} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: '#606060', marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: color as string }}>{val}</div>
              </div>
            ))}
          </div>

          {whale.large_transactions.slice(0, 3).map((tx, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 0', borderTop: '1px solid #1E1E1E',
            }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{tx.entity}</div>
                <div style={{ fontSize: 11, color: '#606060' }}>{tx.action} · {tx.time}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#F7931A' }}>${tx.value_usd_m}M</div>
                <div style={{ fontSize: 11, color: '#606060' }}>{tx.amount.toLocaleString()} {tx.entity === 'Binance' ? 'BTC' : whale.symbol}</div>
              </div>
            </div>
          ))}
        </Card>
      )}

      {/* News Brief */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, marginTop: 4 }}>
        <span style={{ fontWeight: 700, fontSize: 14 }}>📰 Market Brief</span>
        <button onClick={fetchBrief} disabled={loadingBrief} style={btnSmall}>
          {loadingBrief ? '…' : 'Refresh'}
        </button>
      </div>

      {loadingBrief ? <Spinner /> : brief && (
        <Card>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            {[
              ['₿ BTC', brief.btc_sentiment],
              ['Ξ ETH', brief.eth_sentiment],
              ['🌐 Alts', brief.alt_sentiment],
            ].map(([label, sentiment]) => (
              <div key={label} style={{ flex: 1, minWidth: 80, background: '#1A1A1A', borderRadius: 10, padding: '8px 10px' }}>
                <div style={{ fontSize: 10, color: '#606060', marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: sentiment?.includes('Bullish') ? '#22c55e' : sentiment?.includes('Bearish') ? '#ef4444' : '#f59e0b' }}>
                  {sentiment}
                </div>
              </div>
            ))}
          </div>

          <div style={{ background: '#1A1A1A', borderRadius: 10, padding: '10px 12px', marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: '#606060', marginBottom: 3 }}>⚡ TOP EVENT</div>
            <div style={{ fontSize: 13, color: '#E0E0E0', lineHeight: 1.5 }}>{brief.top_event}</div>
          </div>

          <div style={{ fontSize: 11, color: '#606060', marginBottom: 6 }}>KEY LEVELS</div>
          {Object.entries(brief.key_levels).map(([asset, level]) => (
            <div key={asset} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
              <span style={{ fontSize: 12, color: '#808080' }}>{asset}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#F7931A' }}>${level}</span>
            </div>
          ))}
        </Card>
      )}

      <div style={{ fontSize: 10, color: '#404040', textAlign: 'center', marginTop: 8 }}>
        Educational only — not financial advice
      </div>
    </div>
  )
}

// ─── shared styles ─────────────────────────────────────────────────────────────
const inputStyle: CSSProperties = {
  background: '#1A1A1A', border: '1px solid #2A2A2A', borderRadius: 10,
  padding: '8px 12px', color: '#E0E0E0', fontSize: 13, outline: 'none', width: 70,
}
const inputFull: CSSProperties = {
  ...inputStyle, width: '100%', boxSizing: 'border-box',
}
const btnSmall: CSSProperties = {
  background: '#F7931A', border: 'none', borderRadius: 10, color: '#000',
  fontWeight: 700, fontSize: 12, padding: '8px 14px', cursor: 'pointer',
}
const btnFull: CSSProperties = {
  ...btnSmall, width: '100%', fontSize: 14, padding: 12, borderRadius: 12,
}

function Label({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 11, color: '#606060', marginBottom: 4 }}>{children}</div>
}

// ─── MAIN HUB ─────────────────────────────────────────────────────────────────
const PILLS: { id: Pill; icon: string; label: string }[] = [
  { id: 'mentor', icon: '🤖', label: 'Mentor' },
  { id: 'doctor', icon: '🏥', label: 'Doctor' },
  { id: 'risk',   icon: '⚖️', label: 'Risk'   },
  { id: 'intel',  icon: '🐋', label: 'Intel'  },
]

export default function V3Hub() {
  const [pill, setPill] = useState<Pill>('mentor')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '14px 16px 0', flexShrink: 0 }}>
        <div style={{ fontWeight: 800, fontSize: 17, marginBottom: 12 }}>
          ✨ AI Features
        </div>
        {/* Pill nav */}
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 12 }}>
          {PILLS.map(p => (
            <button
              key={p.id}
              onClick={() => setPill(p.id)}
              style={{
                flexShrink: 0, padding: '7px 14px', borderRadius: 20, border: 'none', cursor: 'pointer',
                fontSize: 12, fontWeight: 600,
                background: pill === p.id ? '#F7931A' : '#1A1A1A',
                color: pill === p.id ? '#000' : '#808080',
                transition: 'all 0.15s',
              }}
            >
              {p.icon} {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px 20px' }}>
        {pill === 'mentor' && <MentorTab />}
        {pill === 'doctor' && <DoctorTab />}
        {pill === 'risk'   && <RiskTab />}
        {pill === 'intel'  && <IntelTab />}
      </div>
    </div>
  )
}
