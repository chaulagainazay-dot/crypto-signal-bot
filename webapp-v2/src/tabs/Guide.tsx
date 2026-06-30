import { useState, useEffect } from 'react'
import { useGlobalMarket, useTrendingCoins, useFearGreed } from '../hooks/useCoins'
import { fetchCryptoNews, fetchTopCoins, fp, fmcap } from '../api/coingecko'
import { Spinner, ChipRow, EmptyState } from '../components/ui'
import type { NewsArticle, Coin } from '../types'

type Section = 'briefing' | 'news' | 'learn' | 'quiz'
const SECTIONS: { value: Section; label: string }[] = [
  { value: 'briefing', label: 'Briefing' },
  { value: 'news',     label: 'News'     },
  { value: 'learn',    label: 'Learn'    },
  { value: 'quiz',     label: 'Quiz'     },
]

const TIPS = [
  { title: 'What is DCA?', body: 'Dollar-Cost Averaging means buying a fixed dollar amount regularly (e.g. $20 every week). You buy more when price is low and less when high — averaging your cost over time. Removes the stress of timing the market.' },
  { title: 'Always use a Stop-Loss', body: "A stop-loss is a price below your buy point where you'd sell to limit losses. Example: buy at $100, stop-loss at $85 (−15%). Protects you from big drops. Most exchanges support this automatically." },
  { title: 'Market Cap > Price', body: 'A coin priced at $0.001 can still be worth billions. Always check market cap — it shows the real size of a project. A $100 coin with 1M supply is smaller than a $0.001 coin with 1 quadrillion supply.' },
  { title: 'Volume confirms moves', body: 'High volume + price increase = real move. High volume + price drop = real selling. Low volume moves are usually fake and reverse quickly.' },
  { title: 'FOMO is your enemy', body: 'Fear Of Missing Out makes you buy after a coin already pumped 50%. By then, early buyers are selling to you. If you missed the move, wait for the next dip — there is always another opportunity.' },
  { title: 'BTC leads everything', body: 'When Bitcoin rises strongly, altcoins follow. When Bitcoin drops, altcoins drop harder. Always check BTC dominance. Above 55% = altcoins are weak.' },
  { title: 'RSI Explained', body: 'RSI measures momentum 0–100. Below 30 = oversold (potential bounce). Above 70 = overbought (caution). One of the most reliable entry/exit indicators.' },
  { title: 'Only invest what you can lose', body: 'Crypto is highly volatile. A coin can drop 90% and stay there. Never invest rent money, emergency funds, or borrowed money. Start small, learn, grow slowly.' },
]

const QUIZ = [
  { q: 'What does "market cap" mean?', opts: ['The highest price ever', 'Price × total supply', 'Max daily trading volume', 'Number of exchanges listing it'], ans: 1, exp: 'Market cap = current price × circulating supply. It shows the total value of all coins in existence.' },
  { q: 'RSI below 30 means:', opts: ['Strong sell signal', 'Overbought — caution', 'Oversold — potential bounce', 'No signal'], ans: 2, exp: 'RSI under 30 means the asset is oversold and may bounce. Not guaranteed, but historically a buying opportunity.' },
  { q: 'What is Dollar-Cost Averaging?', opts: ['Buying all at once at the lowest price', 'Buying small fixed amounts regularly', 'Setting a stop-loss', 'Selling at the top'], ans: 1, exp: 'DCA = buy $X every week/month regardless of price. Reduces risk of buying at the worst time.' },
  { q: 'High volume + big price rise means:', opts: ['A fake pump', 'Real move with strong buyer interest', 'Coin will crash soon', 'Nothing — volume does not matter'], ans: 1, exp: 'Volume confirms price moves. High volume + price rise = real momentum. Low volume = weak, often reverses.' },
]

function FearGreedGauge({ value }: { value: number }) {
  const color = value >= 75 ? 'var(--red)' : value >= 55 ? 'var(--accent)' : value >= 45 ? '#EAB308' : 'var(--green)'
  const label = value >= 75 ? 'Extreme Greed' : value >= 55 ? 'Greed' : value >= 45 ? 'Neutral' : value >= 25 ? 'Fear' : 'Extreme Fear'
  const hint  = value >= 55 ? 'Market hot — be cautious' : value >= 45 ? 'Balanced market' : value >= 25 ? 'Panic zone — potential opportunity' : 'Extreme panic — historically good to buy'
  const r = 46, circ = 2 * Math.PI * r, dash = (value / 100) * circ
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
      <svg width={108} height={108} style={{ flexShrink: 0 }}>
        <circle cx={54} cy={54} r={r} fill="none" stroke="var(--border)" strokeWidth={9} />
        <circle cx={54} cy={54} r={r} fill="none" stroke={color} strokeWidth={9}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" transform="rotate(-90 54 54)" />
        <text x={54} y={50} textAnchor="middle" fill={color} fontSize={22} fontWeight={800}>{value}</text>
        <text x={54} y={64} textAnchor="middle" fill="var(--text3)" fontSize={9}>/100</text>
      </svg>
      <div>
        <div style={{ fontWeight: 800, fontSize: 17, color }}>{label}</div>
        <div className="muted" style={{ marginTop: 4, lineHeight: 1.5 }}>{hint}</div>
      </div>
    </div>
  )
}

function newsSentiment(title: string) {
  const t = title.toLowerCase()
  const p = ['surge','rally','bullish','pump','gain','rise','ath','launch','etf','approval'].filter(w => t.includes(w)).length
  const n = ['crash','drop','bear','dump','ban','hack','fraud','fall','plunge','lawsuit'].filter(w => t.includes(w)).length
  if (p > n) return { cls: 'badge-buy',  label: 'Bullish', color: 'var(--green)' }
  if (n > p) return { cls: 'badge-sell', label: 'Bearish', color: 'var(--red)'   }
  return       { cls: 'badge-hold',      label: 'Neutral', color: 'var(--text2)'  }
}

function TipCard({ tip }: { tip: typeof TIPS[0] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card" style={{ cursor: 'pointer', marginBottom: 8 }} onClick={() => setOpen(o => !o)}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <strong style={{ fontSize: 14 }}>{tip.title}</strong>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--text3)" strokeWidth="1.5"
          style={{ flexShrink: 0, transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }}>
          <path d="M4 6l4 4 4-4"/>
        </svg>
      </div>
      {open && <p style={{ marginTop: 10, fontSize: 13, color: 'var(--text2)', lineHeight: 1.7 }}>{tip.body}</p>}
    </div>
  )
}

export default function Guide() {
  const [section, setSection] = useState<Section>('briefing')
  const [quizIdx, setQuizIdx] = useState(0)
  const [quizAns, setQuizAns] = useState<number | null>(null)
  const [topCoins, setTop] = useState<Coin[]>([])
  const [news, setNews] = useState<NewsArticle[]>([])
  const [newsLoading, setNewsLoading] = useState(false)

  const { data: global } = useGlobalMarket()
  const { data: trending } = useTrendingCoins()
  const { data: fg } = useFearGreed()

  useEffect(() => { fetchTopCoins(20).then(setTop).catch(() => {}) }, [])
  useEffect(() => {
    if (section !== 'news' || news.length || newsLoading) return
    setNewsLoading(true)
    fetchCryptoNews(undefined, 20).then(setNews).catch(() => {}).finally(() => setNewsLoading(false))
  }, [section])

  const topBuys = topCoins.filter(c => (c.price_change_percentage_24h || 0) > 4 && (c.total_volume / c.market_cap) > 0.05).slice(0, 3)
  const q = QUIZ[quizIdx % QUIZ.length]

  return (
    <div className="tab-content">
      <div className="row" style={{ marginBottom: 16 }}>
        <h1 className="page-title">Market</h1>
      </div>

      <ChipRow options={SECTIONS} active={section} onChange={setSection} />

      {section === 'briefing' && (
        <>
          {fg !== undefined && (
            <div className="card">
              <div className="section-label">Sentiment Index</div>
              <FearGreedGauge value={fg} />
            </div>
          )}
          {global && (
            <div className="card">
              <div className="section-label">Global Market</div>
              <div className="stat-grid-2">
                {[
                  { label: 'Total Cap',     value: fmcap(global.total_market_cap.usd), sub: `${global.market_cap_change_percentage_24h_usd >= 0 ? '+' : ''}${global.market_cap_change_percentage_24h_usd.toFixed(1)}% 24h`, subColor: global.market_cap_change_percentage_24h_usd >= 0 ? 'var(--green)' : 'var(--red)' },
                  { label: '24h Volume',    value: fmcap(global.total_volume.usd) },
                  { label: 'BTC Dominance', value: `${global.market_cap_percentage.btc.toFixed(1)}%`, sub: global.market_cap_percentage.btc > 55 ? '⚠ Alts weak' : '✓ Altseason', subColor: global.market_cap_percentage.btc > 55 ? 'var(--accent)' : 'var(--green)' },
                  { label: 'ETH Dominance', value: `${global.market_cap_percentage.eth.toFixed(1)}%` },
                ].map(({ label, value, sub, subColor }) => (
                  <div key={label} className="stat-box">
                    <div className="label">{label}</div>
                    <div className="value">{value}</div>
                    {sub && <div style={{ fontSize: 10, color: subColor, marginTop: 3 }}>{sub}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {topBuys.length > 0 && (
            <div className="card">
              <div className="section-label">Today's Opportunities</div>
              {topBuys.map((c, i) => {
                const chg = c.price_change_percentage_24h || 0
                return (
                  <div key={c.id}>
                    {i > 0 && <div className="divider" />}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
                      {c.image && <img src={c.image} className="coin-avatar" style={{ width: 32, height: 32 }} />}
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 13 }}>{c.symbol.toUpperCase()}</div>
                        <div className="muted" style={{ fontSize: 11 }}>${fp(c.current_price)}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span className="badge badge-buy" style={{ marginBottom: 3 }}>BUY</span>
                        <div style={{ fontSize: 11, color: 'var(--green)' }}>▲{chg.toFixed(2)}%</div>
                      </div>
                    </div>
                  </div>
                )
              })}
              <div className="muted" style={{ fontSize: 10, marginTop: 6 }}>Educational only — not financial advice</div>
            </div>
          )}
          {trending.length > 0 && (
            <div className="card">
              <div className="section-label">Trending Now</div>
              {trending.slice(0, 5).map((t, i) => (
                <div key={t.id}>
                  {i > 0 && <div className="divider" />}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0' }}>
                    <span style={{ color: 'var(--text3)', fontSize: 11, width: 18 }}>#{i + 1}</span>
                    {t.small && <img src={t.small} style={{ width: 28, height: 28, borderRadius: '50%' }} />}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{t.name}</div>
                      <div className="muted" style={{ fontSize: 11 }}>{t.symbol?.toUpperCase()}</div>
                    </div>
                    <span className="badge badge-hot">Hot</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {section === 'news' && (
        <>
          {newsLoading && <Spinner />}
          {!newsLoading && news.length === 0 && <EmptyState icon="📰" title="No news available" sub="Could not load news right now." />}
          {news.map((art, i) => {
            const s = newsSentiment(art.title)
            return (
              <a key={i} href={art.url} target="_blank" rel="noreferrer" className="news-card">
                <div className="card" style={{ borderLeft: `3px solid ${s.color}`, marginBottom: 8 }}>
                  <div className="row" style={{ marginBottom: 6 }}>
                    <span className={`badge ${s.cls}`}>{s.label}</span>
                    <span className="muted" style={{ fontSize: 10 }}>{new Date(art.published_on * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.5, marginBottom: 4 }}>{art.title}</div>
                  {art.body && <div className="muted" style={{ fontSize: 11, lineHeight: 1.5 }}>{art.body.slice(0, 100)}…</div>}
                  <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text3)' }}>{art.source_info?.name || art.source} ↗</div>
                </div>
              </a>
            )
          })}
        </>
      )}

      {section === 'learn' && (
        <>
          <div className="muted" style={{ marginBottom: 12 }}>Tap any card to expand</div>
          {TIPS.map((tip, i) => <TipCard key={i} tip={tip} />)}
        </>
      )}

      {section === 'quiz' && (
        <>
          <div className="muted" style={{ marginBottom: 12 }}>Question {(quizIdx % QUIZ.length) + 1} of {QUIZ.length}</div>
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 16, lineHeight: 1.5 }}>{q.q}</div>
            {q.opts.map((opt, i) => {
              const chosen = quizAns !== null
              const correct = i === q.ans
              const wrong = chosen && quizAns === i && !correct
              return (
                <button key={i} onClick={() => !chosen && setQuizAns(i)} style={{
                  display: 'block', width: '100%', textAlign: 'left',
                  padding: '12px 14px', marginBottom: 8, borderRadius: 10,
                  cursor: chosen ? 'default' : 'pointer', fontWeight: chosen && correct ? 700 : 400,
                  fontSize: 13, fontFamily: 'inherit',
                  background: chosen && correct ? 'rgba(34,197,94,0.1)' : chosen && wrong ? 'rgba(239,68,68,0.1)' : 'var(--surface2)',
                  border: `1px solid ${chosen && correct ? 'var(--green)' : chosen && wrong ? 'var(--red)' : 'var(--border)'}`,
                  color: chosen && correct ? 'var(--green)' : chosen && wrong ? 'var(--red)' : 'var(--text)',
                  transition: 'all 0.15s',
                }}>
                  {chosen && correct ? '✓ ' : chosen && wrong ? '✗ ' : ''}{opt}
                </button>
              )
            })}
            {quizAns !== null && (
              <div style={{ marginTop: 10, padding: '10px 12px', background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, fontSize: 13, color: 'var(--text2)', lineHeight: 1.6 }}>
                💡 {q.exp}
              </div>
            )}
          </div>
          {quizAns !== null && (
            <button className="btn" onClick={() => { setQuizIdx(n => n + 1); setQuizAns(null) }}>Next Question →</button>
          )}
        </>
      )}
    </div>
  )
}
