import { useState } from 'react'

// ─── Strategy database — sourced from real traders ───────────────────────────
const STRATEGIES = [
  {
    id: 'dca',
    name: 'Dollar-Cost Averaging',
    shortName: 'DCA',
    icon: '📅',
    trader: 'Warren Buffett / John Bogle',
    traderNote: 'Buffett calls it the single best strategy for most investors. Bogle built Vanguard on it.',
    risk: 'Low',
    riskColor: '#00C853',
    timeframe: 'Long-term (months–years)',
    targetMonthly: '3–8%',
    targetMin: 3,
    targetMax: 8,
    summary: 'Buy a fixed dollar amount of your chosen coins at regular intervals — weekly or monthly — regardless of price. You buy more when cheap, less when expensive, automatically averaging your cost.',
    rules: [
      'Pick 1–3 strong coins (BTC, ETH, or high-conviction altcoins)',
      'Decide a fixed amount per cycle (e.g. $50/week)',
      'Buy every week or month — NO skipping, NO panic selling',
      'Never try to time the market',
      'Review holdings every 3 months, rebalance if one coin > 60% of portfolio',
      'Hold for minimum 1 year before judging results',
    ],
    entry: 'Any time — price does not matter for DCA',
    exit: 'Only sell when your target profit is reached (e.g. 3×) OR your thesis changes',
    allocation: { top: 70, mid: 25, small: 5 },
    pros: ['Zero stress', 'Works even in bear markets', 'Proven over decades'],
    cons: ['Slower gains', 'Requires patience', 'Less exciting'],
    example: 'Invest $100/week into BTC for 52 weeks = $5,200 invested. If BTC rises 40% over the year, your portfolio is ~$7,280.',
    color: '#00C853',
  },
  {
    id: 'swing',
    name: 'Swing Trading',
    shortName: 'Swing',
    icon: '🌊',
    trader: 'Linda Raschke / Mark Minervini',
    traderNote: 'Minervini turned $22K into $3M+ using swing trading. Raschke is known as one of the best short-term traders ever.',
    risk: 'Medium',
    riskColor: '#F7931A',
    timeframe: 'Short-term (days–weeks)',
    targetMonthly: '10–25%',
    targetMin: 10,
    targetMax: 25,
    summary: 'Catch price swings — buy at support (dips), sell at resistance (peaks). Hold for 2–14 days. You do not need to catch the full move, just the fat middle.',
    rules: [
      'Only trade coins with strong uptrends (price above 20-day and 50-day average)',
      'Buy on pullbacks to support — not after a 30% pump',
      'Set stop-loss at 7–10% below your buy price — ALWAYS',
      'Take 50% profit at +15%, let the other 50% ride',
      'Never risk more than 5% of your portfolio on a single trade',
      'Avoid trading during high-uncertainty events (Fed meetings, big news)',
    ],
    entry: 'Buy when price pulls back to support after an uptrend. Look for high volume on the bounce.',
    exit: 'Sell at the next resistance level OR if stop-loss is hit. Do not hold losers hoping for recovery.',
    allocation: { top: 50, mid: 35, small: 15 },
    pros: ['Faster gains than DCA', 'Clear entry/exit rules', 'Works in trending markets'],
    cons: ['Requires daily monitoring', 'Stop-losses can be triggered by volatility', 'Emotional discipline needed'],
    example: 'Buy SOL at $120 (pullback to support). Set stop at $108. Target $138. If it hits $138 in 10 days, that is +15%.',
    color: '#F7931A',
  },
  {
    id: 'breakout',
    name: 'Breakout Trading',
    shortName: 'Breakout',
    icon: '🚀',
    trader: 'William O\'Neil / Jesse Livermore',
    traderNote: 'O\'Neil created the CANSLIM system. Livermore made and lost fortunes on breakouts — "buy high, sell higher."',
    risk: 'Medium-High',
    riskColor: '#FFD700',
    timeframe: 'Days to weeks',
    targetMonthly: '15–40%',
    targetMin: 15,
    targetMax: 40,
    summary: 'Buy when a coin breaks above a key resistance level with high volume. The idea: once price breaks a ceiling it has tried multiple times, big momentum follows.',
    rules: [
      'Look for coins that have tested the same price level 2–3 times and failed',
      'Buy only on the actual breakout — when it closes above resistance',
      'Volume must be significantly higher on breakout day (2× average)',
      'Set stop-loss just below the breakout level',
      'If price falls back below breakout level within 3 days = false breakout, exit',
      'Target: next major resistance level (usually 20–50% higher)',
    ],
    entry: 'Enter when price breaks above resistance with 2× average volume. Do not buy before the break.',
    exit: 'Sell at the next resistance level. Exit immediately if price closes back below breakout point.',
    allocation: { top: 40, mid: 40, small: 20 },
    pros: ['Big wins when it works', 'Clear signal', 'Momentum is your friend'],
    cons: ['Many false breakouts in crypto', 'Can buy near local tops', 'Requires experience to identify'],
    example: 'BTC has resisted $70K three times. On the 4th attempt it breaks above $70K with 3× volume. You buy at $70,500. Target: $85K.',
    color: '#FFD700',
  },
  {
    id: 'trend',
    name: 'Trend Following',
    shortName: 'Trend',
    icon: '📈',
    trader: 'Richard Dennis / "Turtle Traders"',
    traderNote: 'Dennis turned $400 into $200M+ following trends. He taught the strategy to beginners (the "Turtle Traders") and they made $100M+ in 4 years.',
    risk: 'Medium',
    riskColor: '#F7931A',
    timeframe: 'Weeks to months',
    targetMonthly: '8–20%',
    targetMin: 8,
    targetMax: 20,
    summary: 'Follow the trend — buy assets going up, sell or avoid assets going down. "The trend is your friend." Use moving averages to identify direction and stay in winning positions.',
    rules: [
      'Only buy coins trading above their 50-day moving average',
      'If a coin falls below its 50-day MA, sell immediately — no exceptions',
      'Never fight the trend — if crypto market is in a downtrend, hold cash',
      'Add to winning positions as price rises (pyramid up)',
      'Diversify across 5–10 trending coins',
      'Check positions weekly, not daily — reduces emotional trading',
    ],
    entry: 'Buy when price crosses above 50-day MA with increasing volume.',
    exit: 'Sell when price falls below 50-day MA OR when a major market downtrend begins.',
    allocation: { top: 60, mid: 30, small: 10 },
    pros: ['Catches big bull runs', 'Clear rules', 'Proven in stocks and crypto'],
    cons: ['Late entries and exits', 'Whipsaws in sideways markets', 'Boring during flat periods'],
    example: 'ETH crosses above its 50-day MA at $2,800. You buy. It trends to $4,500 over 3 months before crossing back below MA. Profit: +60%.',
    color: '#00B4FF',
  },
  {
    id: 'altrotation',
    name: 'Altcoin Rotation',
    shortName: 'Alt Rotation',
    icon: '🔄',
    trader: 'Crypto-native — used by top CT traders',
    traderNote: 'Used by traders like Michaël van de Poppe and other crypto-native analysts who specialize in altcoin cycles.',
    risk: 'High',
    riskColor: '#FF3D57',
    timeframe: 'Days to weeks',
    targetMonthly: '20–60%',
    targetMin: 20,
    targetMax: 60,
    summary: 'Rotate capital from Bitcoin → Large caps → Mid caps → Small caps as the bull cycle progresses. Money flows predictably through the market in waves. Catch each wave.',
    rules: [
      'Phase 1 (BTC dominance rising): Hold mostly BTC — do not chase alts',
      'Phase 2 (BTC dominance falling): Rotate into ETH and large caps',
      'Phase 3 (ETH/BTC falling): Rotate into mid-cap alts ($100M–$1B mcap)',
      'Phase 4 (mid-caps pumping): Rotate into small-cap gems ($10M–$100M)',
      'Exit small caps first when BTC starts dropping (they crash the hardest)',
      'Never hold small caps through a bear market — 90% drawdowns are common',
    ],
    entry: 'Follow BTC dominance charts. Rotate when dominance clearly changes direction.',
    exit: 'Exit small/mid caps when BTC shows weakness. Rotate back to BTC or stablecoins.',
    allocation: { top: 30, mid: 40, small: 30 },
    pros: ['Highest potential returns in a bull market', 'Matches natural market cycles'],
    cons: ['Very high risk', 'Easy to get stuck in wrong phase', 'Requires experience'],
    example: 'BTC dominance drops from 58% to 50%. You sell 50% of BTC into ETH and top-20 alts. Alts go up 3–5× while BTC goes up 1.5×.',
    color: '#FF3D57',
  },
  {
    id: 'rsi',
    name: 'RSI Oversold Bounce',
    shortName: 'RSI Bounce',
    icon: '⚡',
    trader: 'Welles Wilder / Larry Connors',
    traderNote: 'Wilder invented RSI in 1978. Connors proved statistically that buying extreme RSI oversold conditions outperforms in the long run.',
    risk: 'Medium',
    riskColor: '#F7931A',
    timeframe: 'Days',
    targetMonthly: '8–18%',
    targetMin: 8,
    targetMax: 18,
    summary: 'Buy when a coin is extremely oversold (RSI below 30) in an overall uptrend. The idea: panic selloffs are temporary — price bounces back. Sell when RSI returns to 50–60.',
    rules: [
      'Only use in bull markets — RSI bounces fail in bear markets',
      'Buy when daily RSI drops below 30 (extreme fear)',
      'Wait for RSI to start recovering (crossing back above 30) before entering',
      'Only trade coins with strong long-term fundamentals',
      'Set stop-loss at recent low — if it makes a new low, the bounce failed',
      'Take profit when RSI reaches 55–65 (fair value restored)',
    ],
    entry: 'RSI crosses back above 30 after dipping below. Price should still be in a larger uptrend.',
    exit: 'RSI hits 60, or +10–15% profit, whichever comes first.',
    allocation: { top: 55, mid: 35, small: 10 },
    pros: ['High win rate in bull markets', 'Clear measurable signal', 'Short holding period'],
    cons: ['Fails badly in bear markets', 'RSI can stay oversold for weeks', 'Requires market context'],
    example: 'BTC is in a bull market. It drops 20%, RSI hits 25. RSI recovers above 30 — you buy. 7 days later RSI is at 62, price up 14%. You sell.',
    color: '#AA44FF',
  },
]

// ─── Portfolio Growth Calculator ─────────────────────────────────────────────
function GrowthCalculator({ strategy }) {
  const [portfolio, setPortfolio] = useState('1000')
  const [monthlyPct, setMonthly]  = useState(String(strategy.targetMin))
  const [months, setMonths]       = useState('12')

  const p0  = parseFloat(portfolio)  || 0
  const pct = parseFloat(monthlyPct) || 0
  const mo  = parseInt(months)       || 12
  const r   = 1 + pct / 100

  const milestones = []
  for (let i = 1; i <= mo; i++) {
    milestones.push({ month: i, value: p0 * Math.pow(r, i) })
  }
  const final  = milestones[mo - 1]?.value || p0
  const profit = final - p0
  const mult   = p0 > 0 ? final / p0 : 0

  const fmt = v => {
    if (v >= 1e6) return `$${(v/1e6).toFixed(2)}M`
    if (v >= 1e3) return `$${(v/1e3).toFixed(1)}K`
    return `$${v.toFixed(0)}`
  }

  // Show every 3rd month or key milestones
  const shown = milestones.filter((_, i) => {
    if (mo <= 6)  return true
    if (mo <= 12) return i % 2 === 1 || i === mo - 1
    return i % 3 === 2 || i === mo - 1
  })

  const maxVal = Math.max(...milestones.map(m => m.value))

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div className="section-title" style={{ marginTop: 0 }}>💰 Portfolio Growth Calculator</div>
      <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
        Compound growth using the {strategy.shortName} strategy
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
        <div>
          <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>Starting ($)</div>
          <input type="number" value={portfolio} onChange={e => setPortfolio(e.target.value)}
            style={{ padding: '8px 10px', fontSize: 14 }} />
        </div>
        <div>
          <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>Monthly % (realistic: {strategy.targetMin}–{strategy.targetMax}%)</div>
          <input type="number" value={monthlyPct} onChange={e => setMonthly(e.target.value)}
            style={{ padding: '8px 10px', fontSize: 14 }} />
        </div>
        <div>
          <div className="muted" style={{ fontSize: 11, marginBottom: 4 }}>Months</div>
          <input type="number" value={months} onChange={e => setMonths(e.target.value)}
            style={{ padding: '8px 10px', fontSize: 14 }} />
        </div>
      </div>

      {/* Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
        {[
          { label: 'Final Value',  val: fmt(final),  color: strategy.color },
          { label: 'Total Profit', val: `+${fmt(profit)}`, color: '#00C853' },
          { label: 'Multiplier',   val: `${mult.toFixed(1)}×`, color: '#F7931A' },
          { label: 'Monthly Goal', val: `${fmt(p0 * pct / 100)} / mo`, color: '#A0A0A0' },
        ].map(({ label, val, color }) => (
          <div key={label} style={{ padding: '10px 12px', background: '#141414', borderRadius: 8 }}>
            <div className="muted" style={{ fontSize: 10, marginBottom: 3 }}>{label}</div>
            <div style={{ fontWeight: 800, fontSize: 16, color }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Bar chart */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 80, marginBottom: 8 }}>
        {shown.map(({ month, value }) => {
          const h = maxVal > 0 ? (value / maxVal) * 72 : 4
          return (
            <div key={month} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <div style={{ width: '100%', height: h, background: strategy.color, borderRadius: '3px 3px 0 0', opacity: 0.85 }} />
              <div className="muted" style={{ fontSize: 8 }}>M{month}</div>
            </div>
          )
        })}
      </div>

      {/* Monthly milestones text */}
      <div style={{ maxHeight: 160, overflowY: 'auto' }}>
        {shown.map(({ month, value }) => (
          <div key={month} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1A1A1A', fontSize: 12 }}>
            <span className="muted">Month {month}</span>
            <span style={{ fontWeight: 600, color: strategy.color }}>{fmt(value)}</span>
          </div>
        ))}
      </div>

      <div className="muted" style={{ fontSize: 10, marginTop: 10 }}>
        ⚠️ This is compound interest math. Real trading has losing months — use this as motivation, not a guarantee.
      </div>
    </div>
  )
}

// ─── Allocation pie ───────────────────────────────────────────────────────────
function AllocationBar({ alloc, color }) {
  const segments = [
    { label: 'BTC/ETH (Top)',  pct: alloc.top,   col: color },
    { label: 'Mid Caps',       pct: alloc.mid,   col: color + 'AA' },
    { label: 'Small Caps',     pct: alloc.small, col: color + '55' },
  ]
  return (
    <div>
      <div style={{ display: 'flex', height: 10, borderRadius: 5, overflow: 'hidden', marginBottom: 8 }}>
        {segments.map(s => (
          <div key={s.label} style={{ width: `${s.pct}%`, background: s.col }} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 12 }}>
        {segments.map(s => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: s.col }} />
            <span className="muted" style={{ fontSize: 10 }}>{s.label} {s.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Strategy card ────────────────────────────────────────────────────────────
function StrategyCard({ s, selected, onSelect }) {
  return (
    <div className="card" onClick={() => onSelect(s.id)}
      style={{ marginBottom: 10, cursor: 'pointer', border: `1px solid ${selected ? s.color : '#2A2A2A'}`, transition: 'border 0.2s' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 28 }}>{s.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 800, fontSize: 15 }}>{s.name}</div>
          <div className="muted" style={{ fontSize: 11 }}>by {s.trader.split('/')[0].trim()}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: s.riskColor }}>{s.risk} Risk</div>
          <div style={{ fontSize: 11, color: s.color, fontWeight: 700 }}>{s.targetMonthly}/mo</div>
        </div>
      </div>
      {selected && (
        <div style={{ marginTop: 6 }}>
          <div style={{ width: 24, height: 2, background: s.color, borderRadius: 2, margin: '6px 0' }} />
          <div className="muted" style={{ fontSize: 11 }}>{s.timeframe}</div>
        </div>
      )}
    </div>
  )
}

// ─── Full strategy detail ─────────────────────────────────────────────────────
function StrategyDetail({ s }) {
  const [showCalc, setShowCalc] = useState(false)

  return (
    <div>
      {/* Header */}
      <div className="card" style={{ marginBottom: 12, borderLeft: `3px solid ${s.color}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
          <span style={{ fontSize: 36 }}>{s.icon}</span>
          <div>
            <div style={{ fontWeight: 900, fontSize: 18 }}>{s.name}</div>
            <div className="muted" style={{ fontSize: 12 }}>{s.trader}</div>
          </div>
        </div>
        <div style={{ padding: '10px 12px', background: '#141414', borderRadius: 8, fontSize: 12, color: '#C0C0C0', lineHeight: 1.7, fontStyle: 'italic', marginBottom: 10 }}>
          "{s.traderNote}"
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          {[
            { label: 'Risk',       val: s.risk,            col: s.riskColor },
            { label: 'Timeframe',  val: s.timeframe,       col: '#A0A0A0' },
            { label: 'Target/mo',  val: s.targetMonthly,   col: s.color },
          ].map(({ label, val, col }) => (
            <div key={label} style={{ padding: '8px 10px', background: '#141414', borderRadius: 8, textAlign: 'center' }}>
              <div className="muted" style={{ fontSize: 9, marginBottom: 3 }}>{label}</div>
              <div style={{ fontWeight: 700, fontSize: 12, color: col }}>{val}</div>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>📖 How it works</div>
        <p style={{ fontSize: 13, color: '#C0C0C0', lineHeight: 1.7, margin: 0 }}>{s.summary}</p>
      </div>

      {/* Rules */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>📋 Rules to follow</div>
        {s.rules.map((rule, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, padding: '7px 0', borderBottom: '1px solid #1A1A1A', fontSize: 13, color: '#C0C0C0', lineHeight: 1.5 }}>
            <span style={{ color: s.color, fontWeight: 800, flexShrink: 0 }}>{i + 1}.</span>
            {rule}
          </div>
        ))}
      </div>

      {/* Entry / Exit */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
        {[
          { label: '🟢 Entry Signal', val: s.entry, border: '#00C853' },
          { label: '🔴 Exit Signal',  val: s.exit,  border: '#FF3D57' },
        ].map(({ label, val, border }) => (
          <div key={label} className="card" style={{ borderTop: `2px solid ${border}` }}>
            <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 12, color: '#C0C0C0', lineHeight: 1.6 }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Portfolio allocation */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-title" style={{ marginTop: 0 }}>🎯 Recommended Portfolio Allocation</div>
        <AllocationBar alloc={s.allocation} color={s.color} />
        <div className="muted" style={{ fontSize: 11, marginTop: 10 }}>
          Keep {s.allocation.small}% or less in small caps — they carry the most risk.
        </div>
      </div>

      {/* Pros & Cons */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 12, color: '#00C853', marginBottom: 8 }}>✅ Pros</div>
          {s.pros.map((p, i) => <div key={i} style={{ fontSize: 12, color: '#C0C0C0', marginBottom: 5 }}>• {p}</div>)}
        </div>
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 12, color: '#FF3D57', marginBottom: 8 }}>⚠️ Cons</div>
          {s.cons.map((c, i) => <div key={i} style={{ fontSize: 12, color: '#C0C0C0', marginBottom: 5 }}>• {c}</div>)}
        </div>
      </div>

      {/* Example */}
      <div className="card" style={{ marginBottom: 12, background: '#141424', border: `1px solid ${s.color}33` }}>
        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }}>📊 Real Example</div>
        <p style={{ fontSize: 13, color: '#C0C0C0', lineHeight: 1.7, margin: 0 }}>{s.example}</p>
      </div>

      {/* Calculator toggle */}
      <button className="btn" onClick={() => setShowCalc(c => !c)} style={{ marginBottom: 12 }}>
        {showCalc ? '▲ Hide Calculator' : '💰 Calculate My Growth'}
      </button>
      {showCalc && <GrowthCalculator strategy={s} />}
    </div>
  )
}

// ─── Main export ─────────────────────────────────────────────────────────────
export default function Strategy() {
  const [selected, setSelected] = useState(null)
  const current = STRATEGIES.find(s => s.id === selected)

  if (current) {
    return (
      <div className="tab-content">
        <button onClick={() => setSelected(null)}
          style={{ background: 'none', border: 'none', color: '#A0A0A0', cursor: 'pointer', fontSize: 14, padding: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: 6 }}>
          ← Back to Strategies
        </button>
        <StrategyDetail s={current} />
      </div>
    )
  }

  return (
    <div className="tab-content">
      <h2>📊 Trading Strategies</h2>
      <div className="muted" style={{ marginBottom: 16, fontSize: 13 }}>
        Strategies from the world's best traders — adapted for crypto. Pick one that matches your risk tolerance and time commitment.
      </div>

      {/* Risk guide */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 16 }}>
        {[
          { label: 'Low Risk',  sub: '3–8%/mo',  col: '#00C853' },
          { label: 'Med Risk',  sub: '8–25%/mo', col: '#F7931A' },
          { label: 'High Risk', sub: '20–60%/mo', col: '#FF3D57' },
        ].map(({ label, sub, col }) => (
          <div key={label} style={{ padding: '8px', background: '#141414', borderRadius: 8, textAlign: 'center', borderTop: `2px solid ${col}` }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: col }}>{label}</div>
            <div className="muted" style={{ fontSize: 10 }}>{sub}</div>
          </div>
        ))}
      </div>

      {STRATEGIES.map(s => (
        <StrategyCard key={s.id} s={s} selected={selected === s.id} onSelect={id => setSelected(id)} />
      ))}

      <div className="muted" style={{ fontSize: 11, textAlign: 'center', padding: '16px 0' }}>
        ⚠️ No strategy guarantees profit. Never invest more than you can afford to lose. All trading carries risk.
      </div>
    </div>
  )
}
