import { useState, useEffect } from 'react'
import { useStore } from '../../store'
import { Spinner, EmptyState } from '../../components/ui'
import type { WhaleData, NewsBrief } from '../../types'

const API = ''

export default function IntelTab({ goPortfolio }: { goPortfolio: () => void }) {
  const { holdings } = useStore()
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [whaleData, setWhaleData] = useState<Record<string, WhaleData>>({})
  const [brief, setBrief] = useState<NewsBrief | null>(null)
  const [loadingWhale, setLoadingWhale] = useState(false)
  const [loadingBrief, setLoadingBrief] = useState(true)

  const currentSymbol = holdings[selectedIdx]?.symbol.toUpperCase() ?? 'BTC'

  async function fetchWhale(sym: string) {
    if (whaleData[sym]) return
    setLoadingWhale(true)
    try {
      const r = await window.fetch(`${API}/api/v3/whale?symbol=${sym}`)
      const d = await r.json() as WhaleData
      setWhaleData(prev => ({ ...prev, [sym]: d }))
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

  useEffect(() => {
    fetchBrief()
    if (holdings.length > 0) fetchWhale(holdings[0].symbol.toUpperCase())
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetchWhale(currentSymbol) }, [currentSymbol])  // eslint-disable-line react-hooks/exhaustive-deps

  const whale = whaleData[currentSymbol]

  return (
    <div>
      {/* Market Brief */}
      <div className="row" style={{ marginBottom: 10 }}>
        <div className="section-label" style={{ marginBottom: 0 }}>Market Brief</div>
        <button className="btn-icon" onClick={fetchBrief} title="Refresh brief" style={{ width: 28, height: 28 }}>
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
            <path d="M11 6.5A4.5 4.5 0 1 1 6.5 2a4.5 4.5 0 0 1 3.3 1.4"/>
            <path d="M11 2v3H8"/>
          </svg>
        </button>
      </div>

      {loadingBrief ? <Spinner /> : brief && (
        <div className="card" style={{ marginBottom: 12 }}>
          <div className="stat-grid-4" style={{ marginBottom: 12 }}>
            {[
              { label: 'BTC',  val: brief.btc_sentiment },
              { label: 'ETH',  val: brief.eth_sentiment },
              { label: 'Alts', val: brief.alt_sentiment },
              { label: 'Articles', val: String(brief.article_count) },
            ].map(({ label, val }) => (
              <div key={label} className="stat-box">
                <div className="label">{label}</div>
                <div className="value" style={{
                  fontSize: 11,
                  color: val?.includes('Bullish') ? 'var(--green)' : val?.includes('Bearish') ? 'var(--red)' : 'var(--text2)',
                }}>{val}</div>
              </div>
            ))}
          </div>
          <div className="card-inner" style={{ marginBottom: 10 }}>
            <div className="section-label">Top Event</div>
            <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>{brief.top_event}</div>
          </div>
          {Object.keys(brief.key_levels).length > 0 && (
            <div>
              <div className="section-label">Key Levels</div>
              <div style={{ display: 'flex', gap: 8 }}>
                {Object.entries(brief.key_levels).map(([asset, level]) => (
                  <div key={asset} className="stat-box" style={{ flex: 1, textAlign: 'center' }}>
                    <div className="label">{asset}</div>
                    <div className="value" style={{ color: 'var(--accent)' }}>${level}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Whale Tracker */}
      <div className="section-label">Whale Tracker</div>

      {holdings.length === 0 ? (
        <EmptyState icon="🐋" title="No holdings" sub="Add coins to track whale activity."
          action={<button className="btn" onClick={goPortfolio}>Go to Portfolio →</button>} />
      ) : (
        <>
          <div className="chip-row" style={{ marginBottom: 10 }}>
            {holdings.map((h, i) => (
              <button key={h.id} className={`chip${selectedIdx === i ? ' active-purple' : ''}`}
                onClick={() => setSelectedIdx(i)}>
                {h.image && <img src={h.image} style={{ width: 14, height: 14, borderRadius: '50%', verticalAlign: 'middle', marginRight: 4 }} />}
                {h.symbol.toUpperCase()}
              </button>
            ))}
          </div>

          {loadingWhale ? <Spinner /> : whale && (
            <div className="card">
              <div className="row" style={{ marginBottom: 10 }}>
                <span style={{ fontWeight: 700 }}>{whale.symbol}</span>
                <span className={`badge ${whale.whale_accumulation ? 'badge-buy' : 'badge-sell'}`}>
                  {whale.whale_accumulation ? 'Accumulating' : 'Distributing'}
                </span>
              </div>

              <div className="card-inner" style={{ marginBottom: 12, fontSize: 13, color: whale.whale_accumulation ? 'var(--green)' : 'var(--red)', lineHeight: 1.5 }}>
                {whale.interpretation}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
                {[
                  { label: 'Inflow',  val: `$${whale.exchange_flows.inflow}M`,  color: 'var(--red)'   },
                  { label: 'Outflow', val: `$${whale.exchange_flows.outflow}M`, color: 'var(--green)' },
                  { label: 'Net',     val: `${whale.exchange_flows.net > 0 ? '+' : ''}$${whale.exchange_flows.net}M`, color: whale.exchange_flows.net < 0 ? 'var(--green)' : 'var(--red)' },
                ].map(({ label, val, color }) => (
                  <div key={label} className="stat-box" style={{ flex: 1, textAlign: 'center', margin: '0 4px' }}>
                    <div className="label">{label}</div>
                    <div className="value" style={{ color }}>{val}</div>
                  </div>
                ))}
              </div>

              {whale.large_transactions.slice(0, 3).map((tx, i) => (
                <div key={i} className="row" style={{ padding: '8px 0', borderTop: '1px solid var(--border2)' }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{tx.entity}</div>
                    <div className="muted" style={{ fontSize: 11 }}>{tx.action} · {tx.time}</div>
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)' }}>${tx.value_usd_m}M</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      <div className="muted" style={{ fontSize: 10, textAlign: 'center', marginTop: 8 }}>Educational only — not financial advice</div>
    </div>
  )
}
