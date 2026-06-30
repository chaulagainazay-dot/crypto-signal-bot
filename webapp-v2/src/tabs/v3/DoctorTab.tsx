import { useState, useEffect } from 'react'
import { useStore } from '../../store'
import { fetchCoinDetail } from '../../api/coingecko'
import { Spinner, ProgressBar, EmptyState } from '../../components/ui'
import { fmcap, fp } from '../../api/coingecko'
import type { DoctorReport } from '../../types'

const API = ''

export default function DoctorTab({ goPortfolio }: { goPortfolio: () => void }) {
  const { holdings } = useStore()
  const [result, setResult] = useState<DoctorReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [livePrices, setLivePrices] = useState<Record<string, number>>({})
  const [pricesLoaded, setPricesLoaded] = useState(false)

  useEffect(() => {
    if (holdings.length === 0) return
    let cancelled = false
    async function loadPrices() {
      const prices: Record<string, number> = {}
      await Promise.all(holdings.map(async h => {
        try {
          const d = await fetchCoinDetail(h.coinId) as { market_data?: { current_price?: { usd?: number } } } | null
          const price = d?.market_data?.current_price?.usd
          if (price) prices[h.symbol.toUpperCase()] = price
        } catch { /* ignore */ }
      }))
      if (!cancelled) { setLivePrices(prices); setPricesLoaded(true) }
    }
    loadPrices()
    return () => { cancelled = true }
  }, [holdings])

  useEffect(() => {
    if (!pricesLoaded || holdings.length === 0) return
    runDiagnosis()
  }, [pricesLoaded])  // eslint-disable-line react-hooks/exhaustive-deps

  async function runDiagnosis() {
    setLoading(true)
    const portfolio: Record<string, number> = {}
    for (const h of holdings) {
      const livePrice = livePrices[h.symbol.toUpperCase()] ?? h.buyPrice
      portfolio[h.symbol.toUpperCase()] = (portfolio[h.symbol.toUpperCase()] || 0) + livePrice * h.amount
    }
    try {
      const r = await window.fetch(`${API}/api/v3/doctor`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio }),
      })
      setResult(await r.json() as DoctorReport)
    } catch { /* ignore */ }
    setLoading(false)
  }

  if (holdings.length === 0) return <EmptyState icon="🏥" title="No holdings" sub="Add coins in Portfolio to diagnose."
    action={<button className="btn" onClick={goPortfolio}>Go to Portfolio →</button>} />

  const statusColor = result?.health_status === 'HEALTHY' ? 'var(--green)' : result?.health_status === 'NEEDS_ATTENTION' ? 'var(--accent)' : 'var(--red)'
  const statusCls   = result?.health_status === 'HEALTHY' ? 'badge-buy' : result?.health_status === 'NEEDS_ATTENTION' ? 'badge-hold' : 'badge-sell'
  const totalValue  = holdings.reduce((s, h) => s + (livePrices[h.symbol.toUpperCase()] ?? h.buyPrice) * h.amount, 0)

  return (
    <div>
      {/* Live portfolio breakdown */}
      <div className="card" style={{ marginBottom: 10 }}>
        <div className="row" style={{ marginBottom: 10 }}>
          <div className="section-label" style={{ marginBottom: 0 }}>Live Portfolio</div>
          <span className="muted" style={{ fontSize: 11 }}>{holdings.length} assets · {totalValue > 0 ? fmcap(totalValue) : '—'}</span>
        </div>
        {holdings.map(h => {
          const price  = livePrices[h.symbol.toUpperCase()] ?? h.buyPrice
          const value  = price * h.amount
          const pct    = totalValue > 0 ? (value / totalValue) * 100 : 0
          const pnlPct = h.buyPrice > 0 ? (price - h.buyPrice) / h.buyPrice * 100 : 0
          return (
            <div key={h.id} style={{ marginBottom: 10 }}>
              <div className="row" style={{ marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {h.image && <img src={h.image} style={{ width: 18, height: 18, borderRadius: '50%' }} />}
                  <span style={{ fontSize: 13, fontWeight: 700 }}>{h.symbol.toUpperCase()}</span>
                  <span className="muted" style={{ fontSize: 11 }}>{pct.toFixed(1)}%</span>
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: pnlPct >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                    {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{value > 0 ? fmcap(value) : `$${fp(price)}`}</span>
                </div>
              </div>
              <ProgressBar pct={pct} color="var(--accent)" height={3} />
            </div>
          )
        })}
      </div>

      <button className="btn" onClick={runDiagnosis} disabled={loading} style={{ marginBottom: 12 }}>
        {loading ? 'Diagnosing…' : 'Refresh Diagnosis'}
      </button>

      {loading && <Spinner />}

      {result && !loading && (
        <>
          <div className="card">
            <div className="row" style={{ marginBottom: 12 }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>Portfolio Health</span>
              <span className={`badge ${statusCls}`}>{result.health_status.replace('_', ' ')}</span>
            </div>
            <div className="row" style={{ marginBottom: 8 }}>
              <span className="muted">Overall Score</span>
              <span style={{ fontWeight: 800, fontSize: 18, color: statusColor }}>{result.overall_score}/100</span>
            </div>
            <ProgressBar pct={result.overall_score} color={statusColor} />
          </div>

          {result.problems.length > 0 && (
            <div className="card" style={{ borderColor: 'rgba(239,68,68,0.3)' }}>
              <div className="section-label" style={{ color: 'var(--red)' }}>Problems Found</div>
              {result.problems.map((p, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 6 }}>✗ {p}</div>
              ))}
            </div>
          )}

          {result.recommendations.length > 0 && (
            <div className="card" style={{ borderColor: 'rgba(34,197,94,0.3)' }}>
              <div className="section-label" style={{ color: 'var(--green)' }}>How to Fix</div>
              {result.recommendations.map((r, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 6 }}>{i + 1}. {r}</div>
              ))}
            </div>
          )}

          <div className="card">
            <div className="section-label">Score Breakdown</div>
            {Object.entries(result.breakdown).map(([key, val]) => {
              const col = val >= 70 ? 'var(--green)' : val >= 40 ? 'var(--accent)' : 'var(--red)'
              return (
                <div key={key} style={{ marginBottom: 10 }}>
                  <div className="row" style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: 'var(--text2)', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: col }}>{Math.round(val)}</span>
                  </div>
                  <ProgressBar pct={val} color={col} />
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
