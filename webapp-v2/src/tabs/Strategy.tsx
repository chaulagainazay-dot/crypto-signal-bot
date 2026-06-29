import { useState } from 'react'

const STRATEGIES = [
  {
    id: 'dca', icon: '💰', name: 'DCA', full: 'Dollar-Cost Averaging',
    legend: 'Buffett / Bogle', color: '#00C853',
    alloc: [60, 30, 10],
    risk: 'Low', timeframe: 'Months–Years', suitable: 'Beginners, long-term holders',
    desc: 'Invest a fixed amount on a schedule regardless of price. Removes emotion and timing risk.',
    rules: ['Set a fixed weekly/monthly buy amount ($20–$500)', 'Buy on the same day every period, no matter what', 'Never skip a buy due to fear or excitement', 'Hold for minimum 1 year before evaluating'],
    entry: 'Any price — the schedule is the strategy',
    exit: 'Long-term target or life goal reached',
  },
  {
    id: 'swing', icon: '🌊', name: 'Swing', full: 'Swing Trading',
    legend: 'Minervini / Raschke', color: '#F7931A',
    alloc: [50, 35, 15],
    risk: 'Medium', timeframe: '2–14 days', suitable: 'Active traders with time',
    desc: 'Capture medium-term price swings using technical analysis. Hold for days to weeks.',
    rules: ['Only trade coins with volume > $10M/day', 'Enter on confirmed breakout with volume surge', 'Set stop-loss at 8–12% below entry', 'Take 50% profit at first target, let rest run'],
    entry: 'RSI 40–55 zone + price breaking resistance with volume',
    exit: '+15–25% profit or stop-loss hit',
  },
  {
    id: 'breakout', icon: '🚀', name: 'Breakout', full: 'Breakout Trading',
    legend: "O'Neil / Livermore", color: '#7C9FF7',
    alloc: [40, 40, 20],
    risk: 'Medium-High', timeframe: '1–7 days', suitable: 'Traders who watch charts daily',
    desc: 'Buy when price breaks above key resistance with strong volume. Ride the momentum.',
    rules: ['Identify clear resistance level from chart', 'Wait for candle to close above resistance', 'Volume must be 2× the 20-day average', 'Use tight 5–8% stop-loss below breakout level'],
    entry: 'Candle close above resistance + volume confirmation',
    exit: '+20–40% or stop-loss triggered',
  },
  {
    id: 'trend', icon: '📈', name: 'Trend Follow', full: 'Trend Following',
    legend: 'Dennis / Turtle Traders', color: '#FFD700',
    alloc: [30, 50, 20],
    risk: 'Medium', timeframe: 'Weeks–Months', suitable: 'Disciplined, rule-based traders',
    desc: 'Follow the macro trend. Buy in uptrends, exit when trend breaks. Never fight the market.',
    rules: ['Only buy coins above their 50-day moving average', 'Add to position on pullbacks to MA', 'Exit immediately if price closes below 50-day MA', 'Never short — crypto trends up long term'],
    entry: 'Price above 50-day MA + higher highs pattern',
    exit: 'Close below 50-day MA or major structure break',
  },
  {
    id: 'altcoin', icon: '🔄', name: 'Alt Rotation', full: 'Altcoin Rotation',
    legend: 'Crypto-native strategy', color: '#FF6B9D',
    alloc: [20, 50, 30],
    risk: 'High', timeframe: '1–4 weeks', suitable: 'Experienced crypto traders',
    desc: 'Rotate between BTC, ETH, and top altcoins based on BTC dominance cycles.',
    rules: ['BTC dominance rising → hold BTC/ETH, reduce alts', 'BTC dominance falling → rotate into top 50 alts', 'Never hold more than 5 alts at once', 'Take profits on alts every 30–50% gain'],
    entry: 'BTC dominance breaks below 50% = altseason signal',
    exit: 'BTC dominance rising again — rotate back to BTC',
  },
  {
    id: 'rsi', icon: '📉', name: 'RSI Bounce', full: 'RSI Oversold Bounce',
    legend: 'Wilder / Connors', color: '#00E5FF',
    alloc: [50, 30, 20],
    risk: 'Medium', timeframe: '3–10 days', suitable: 'Technical analysts',
    desc: 'Buy when RSI drops below 30 (oversold). Sell when RSI recovers to 50–60.',
    rules: ['RSI must be below 30 on daily chart', 'Coin must be in overall uptrend (above 200 MA)', 'Buy in 3 portions: 30% / 40% / 30% on dips', 'Exit when RSI hits 55–65 zone'],
    entry: 'RSI < 30 + uptrend intact + price at support',
    exit: 'RSI 55–65 or +15–20% gain, whichever comes first',
  },
]

function AllocationBar({ alloc, color }: { alloc: number[]; color: string }) {
  const labels = ['Large Cap', 'Mid Cap', 'Small Cap']
  const colors = ['#F7931A', '#7C9FF7', '#00C853']
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="muted" style={{ fontSize: 10, marginBottom: 6 }}>Portfolio Allocation</div>
      <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', height: 12 }}>
        {alloc.map((pct, i) => (
          <div key={i} style={{ width: `${pct}%`, background: colors[i] }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
        {alloc.map((pct, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: colors[i] }} />
            <span style={{ fontSize: 10, color: '#808080' }}>{labels[i]} {pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function GrowthCalculator() {
  const [capital, setCapital] = useState('1000')
  const [monthly, setMonthly] = useState('100')
  const [apy, setApy] = useState('50')
  const [years, setYears] = useState('3')

  const c = parseFloat(capital) || 0
  const m = parseFloat(monthly) || 0
  const r = (parseFloat(apy) || 0) / 100 / 12
  const n = (parseFloat(years) || 1) * 12

  const milestones: { month: number; value: number }[] = []
  let val = c
  for (let i = 1; i <= n; i++) {
    val = val * (1 + r) + m
    if (i % 3 === 0 || i === n) milestones.push({ month: i, value: val })
  }
  const final = milestones[milestones.length - 1]?.value || 0
  const maxVal = Math.max(...milestones.map(m => m.value))

  return (
    <div className="card">
      <div className="section-title" style={{ marginTop: 0 }}>📈 Portfolio Growth Calculator</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
        {[
          { label: 'Starting Capital ($)', val: capital, set: setCapital },
          { label: 'Monthly Add ($)', val: monthly, set: setMonthly },
          { label: 'Expected APY (%)', val: apy, set: setApy },
          { label: 'Years', val: years, set: setYears },
        ].map(({ label, val, set }) => (
          <div key={label}>
            <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>{label}</div>
            <input type="number" value={val} onChange={e => set(e.target.value)} style={{ padding: '8px 10px', fontSize: 13 }} />
          </div>
        ))}
      </div>

      <div style={{ padding: '12px 16px', background: '#0D1A0D', borderRadius: 10, marginBottom: 14, border: '1px solid #1A3A1A' }}>
        <div className="muted" style={{ fontSize: 11 }}>Projected Value after {years} year{parseFloat(years) !== 1 ? 's' : ''}</div>
        <div style={{ fontSize: 28, fontWeight: 900, color: '#00C853', marginTop: 4 }}>
          ${final >= 1e6 ? `${(final / 1e6).toFixed(2)}M` : final >= 1000 ? `${(final / 1000).toFixed(1)}K` : final.toFixed(0)}
        </div>
        <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
          Total invested: ${(c + m * n).toLocaleString()} · Gain: ${(final - c - m * n).toFixed(0)}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 80 }}>
        {milestones.map((ms, i) => (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <div style={{ width: '100%', background: '#00C853', borderRadius: '3px 3px 0 0', height: `${(ms.value / maxVal) * 72}px`, minHeight: 4 }} />
            {(i === 0 || i === Math.floor(milestones.length / 2) || i === milestones.length - 1) && (
              <div className="muted" style={{ fontSize: 8 }}>m{ms.month}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function StrategyCard({ s }: { s: typeof STRATEGIES[0] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card" style={{ marginBottom: 10, borderLeft: `3px solid ${s.color}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }} onClick={() => setOpen(o => !o)}>
        <span style={{ fontSize: 24 }}>{s.icon}</span>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 14 }}>{s.name}</strong>
          <div className="muted" style={{ fontSize: 11 }}>{s.full} · {s.legend}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ background: s.color + '22', color: s.color, padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>
            {s.risk} Risk
          </span>
          <div className="muted" style={{ fontSize: 10, marginTop: 3 }}>{open ? '▲' : '▼'}</div>
        </div>
      </div>
      {open && (
        <div style={{ marginTop: 14 }}>
          <AllocationBar alloc={s.alloc} color={s.color} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
            {[
              { label: 'Timeframe', val: s.timeframe },
              { label: 'Best for', val: s.suitable },
            ].map(({ label, val }) => (
              <div key={label} style={{ padding: '8px 10px', background: '#141414', borderRadius: 8 }}>
                <div className="muted" style={{ fontSize: 9, marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{val}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: 13, color: '#C0C0C0', lineHeight: 1.7, marginBottom: 12 }}>{s.desc}</p>
          <div className="section-title" style={{ marginTop: 0 }}>Rules</div>
          {s.rules.map((r, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, padding: '6px 0', borderBottom: '1px solid #1E1E1E' }}>
              <span style={{ color: s.color, fontWeight: 700, fontSize: 12 }}>{i + 1}.</span>
              <span style={{ fontSize: 12, color: '#C0C0C0', lineHeight: 1.6 }}>{r}</span>
            </div>
          ))}
          <div style={{ marginTop: 12, padding: '10px 12px', background: '#141414', borderRadius: 10 }}>
            <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>ENTRY</div>
            <div style={{ fontSize: 12, color: '#00C853' }}>{s.entry}</div>
          </div>
          <div style={{ marginTop: 8, padding: '10px 12px', background: '#141414', borderRadius: 10 }}>
            <div className="muted" style={{ fontSize: 10, marginBottom: 4 }}>EXIT</div>
            <div style={{ fontSize: 12, color: '#FF3D57' }}>{s.exit}</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Strategy() {
  return (
    <div className="tab-content">
      <h2>📊 Strategy</h2>
      <div className="muted" style={{ fontSize: 12, marginBottom: 16 }}>
        6 strategies from the world's best traders. Tap to expand.
      </div>
      {STRATEGIES.map(s => <StrategyCard key={s.id} s={s} />)}
      <GrowthCalculator />
      <div className="muted" style={{ textAlign: 'center', fontSize: 11, marginTop: 16, padding: '0 16px' }}>
        ⚠️ All strategies are educational. Crypto is high risk. Never invest more than you can afford to lose.
      </div>
    </div>
  )
}
