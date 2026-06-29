import { useState, useEffect } from 'react'
import { useGlobalMarket, useTrendingCoins, useFearGreed } from '../hooks/useCoins'
import { fetchCryptoNews, fetchTopCoins, fp, fmcap } from '../api/coingecko'
import Spinner from '../components/Spinner'
import type { NewsArticle, Coin } from '../types'

const TIPS = [
  { icon: '💡', title: 'What is DCA?', body: 'Dollar-Cost Averaging means buying a fixed dollar amount regularly (e.g. $20 every week). You buy more when price is low and less when high — averaging your cost over time. Removes the stress of timing the market.' },
  { icon: '🛑', title: 'Always use a Stop-Loss', body: "A stop-loss is a price below your buy point where you'd sell to limit losses. Example: buy at $100, stop-loss at $85 (−15%). Protects you from big drops. Most exchanges support this automatically." },
  { icon: '🎯', title: 'Market Cap > Price', body: 'A coin priced at $0.001 can still be worth billions. Always check market cap — it shows the real size of a project. A $100 coin with 1M supply is smaller than a $0.001 coin with 1 quadrillion supply.' },
  { icon: '📊', title: 'Volume tells the truth', body: 'High volume + price increase = real move. High volume + price drop = real selling. Low volume moves are usually fake and reverse quickly.' },
  { icon: '🔥', title: 'FOMO is your enemy', body: 'Fear Of Missing Out makes you buy after a coin already pumped 50%. By then, early buyers are selling to you. If you missed the move, wait for the next dip — there is always another opportunity.' },
  { icon: '🌊', title: 'BTC leads everything', body: 'When Bitcoin rises strongly, altcoins follow. When Bitcoin drops, altcoins drop harder. Always check BTC dominance. Above 55% = altcoins are weak.' },
  { icon: '📈', title: 'RSI Explained', body: 'RSI (Relative Strength Index) measures momentum 0–100. Below 30 = oversold (potential bounce). Above 70 = overbought (caution). It is one of the most reliable entry/exit indicators.' },
  { icon: '🏦', title: 'Only invest what you can lose', body: 'Crypto is highly volatile. A coin can drop 90% and stay there. Never invest rent money, emergency funds, or borrowed money. Start small, learn, grow slowly.' },
]

const QUIZ = [
  { q: 'What does "market cap" mean?', opts: ['The highest price ever', 'Price × total supply', 'Max daily trading volume', 'Number of exchanges listing it'], ans: 1, exp: 'Market cap = current price × circulating supply. It shows the total value of all coins.' },
  { q: 'RSI below 30 means:', opts: ['Strong sell signal', 'Overbought — caution', 'Oversold — potential bounce', 'No signal'], ans: 2, exp: 'RSI under 30 means the asset is oversold and may bounce. It is not guaranteed, but historically a buying opportunity.' },
  { q: 'What is Dollar-Cost Averaging?', opts: ['Buying all at once at the lowest price', 'Buying small fixed amounts regularly', 'Setting a stop-loss', 'Selling at the top'], ans: 1, exp: 'DCA = buy $X every week/month regardless of price. Reduces risk of buying at the worst time.' },
  { q: 'High volume + big price rise means:', opts: ['A fake pump', 'Real move with strong buyer interest', 'Coin will crash soon', 'Nothing — volume does not matter'], ans: 1, exp: 'Volume confirms price moves. High volume + price rise = real momentum. Low volume = weak, often reverses.' },
]

function TipCard({ tip }: { tip: typeof TIPS[0] }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="card" style={{ marginBottom: 10, cursor: 'pointer' }} onClick={() => setOpen(o => !o)}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 22 }}>{tip.icon}</span>
        <strong style={{ fontSize: 14, flex: 1 }}>{tip.title}</strong>
        <span className="muted">{open ? '▲' : '▼'}</span>
      </div>
      {open && <p style={{ marginTop: 10, fontSize: 13, color: '#C0C0C0', lineHeight: 1.7 }}>{tip.body}</p>}
    </div>
  )
}

function FearGreedGauge({ value }: { value: number }) {
  const color = value >= 75 ? '#FF3D57' : value >= 55 ? '#F7931A' : value >= 45 ? '#FFD700' : value >= 25 ? '#00C853' : '#00E676'
  const label = value >= 75 ? 'Extreme Greed' : value >= 55 ? 'Greed' : value >= 45 ? 'Neutral' : value >= 25 ? 'Fear' : 'Extreme Fear'
  const hint = value >= 75 ? 'Market overheated — be careful buying' : value >= 55 ? 'Optimism high — stay cautious' : value >= 45 ? 'Balanced market' : value >= 25 ? 'People scared — potential opportunity' : 'Panic selling — historically good to buy in portions'
  const r = 48, circ = 2 * Math.PI * r, dash = (value / 100) * circ
  return (
    <div style={{ textAlign: 'center', padding: '8px 0' }}>
      <svg width={120} height={120}>
        <circle cx={60} cy={60} r={r} fill="none" stroke="#2A2A2A" strokeWidth={10} />
        <circle cx={60} cy={60} r={r} fill="none" stroke={color} strokeWidth={10}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" transform="rotate(-90 60 60)" />
        <text x={60} y={54} textAnchor="middle" fill={color} fontSize={24} fontWeight={900}>{value}</text>
        <text x={60} y={72} textAnchor="middle" fill="#808080" fontSize={10}>/100</text>
      </svg>
      <div style={{ fontWeight: 800, color, fontSize: 16, marginTop: 4 }}>{label}</div>
      <div className="muted" style={{ fontSize: 12, marginTop: 4, padding: '0 16px' }}>{hint}</div>
    </div>
  )
}

function newsSentiment(title: string) {
  const t = title.toLowerCase()
  const p = ['surge','rally','bullish','pump','gain','rise','ath','launch','partnership','etf','approval','record'].filter(w => t.includes(w)).length
  const n = ['crash','drop','bear','dump','ban','hack','fraud','fall','plunge','fear','lawsuit','fine'].filter(w => t.includes(w)).length
  if (p > n) return { label: '🟢 Bullish', color: '#00C853' }
  if (n > p) return { label: '🔴 Bearish', color: '#FF3D57' }
  return { label: '⚪ Neutral', color: '#808080' }
}

function NewsItem({ art }: { art: NewsArticle }) {
  const s = newsSentiment(art.title)
  return (
    <a href={art.url} target="_blank" rel="noreferrer" style={{ display: 'block', textDecoration: 'none', marginBottom: 8 }}>
      <div className="card" style={{ borderLeft: `3px solid ${s.color}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: s.color }}>{s.label}</span>
          <span className="muted" style={{ fontSize: 10 }}>{new Date(art.published_on * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#E0E0E0', lineHeight: 1.5 }}>{art.title}</div>
        {art.body && <div className="muted" style={{ fontSize: 11, marginTop: 4, lineHeight: 1.5 }}>{art.body.slice(0, 110)}…</div>}
        <div style={{ marginTop: 5, fontSize: 10, color: '#444' }}>{art.source_info?.name || art.source} ↗</div>
      </div>
    </a>
  )
}

export default function Guide() {
  const [section, setSection] = useState<'briefing' | 'news' | 'learn' | 'quiz'>('briefing')
  const [quizIdx, setQuizIdx] = useState(0)
  const [quizAns, setQuizAns] = useState<number | null>(null)
  const [topCoins, setTop] = useState<Coin[]>([])
  const [news, setNews] = useState<NewsArticle[]>([])
  const [newsLoading, setNewsLoading] = useState(false)

  const { data: global, isLoading: gLoading } = useGlobalMarket()
  const { data: trending } = useTrendingCoins()
  const { data: fg } = useFearGreed()

  useEffect(() => {
    fetchTopCoins(20).then(setTop).catch(() => {})
  }, [])

  useEffect(() => {
    if (section !== 'news' || news.length || newsLoading) return
    setNewsLoading(true)
    fetchCryptoNews(undefined, 20).then(setNews).catch(() => {}).finally(() => setNewsLoading(false))
  }, [section])

  const topBuys = topCoins.filter(c => (c.price_change_percentage_24h || 0) > 4 && (c.total_volume / c.market_cap) > 0.05).slice(0, 3)
  const q = QUIZ[quizIdx % QUIZ.length]

  return (
    <div className="tab-content">
      <h2>🤖 Guide</h2>
      <div className="pills">
        {(['briefing', 'news', 'learn', 'quiz'] as const).map(s => (
          <button key={s} className={`pill${section === s ? ' active' : ''}`} onClick={() => setSection(s)}>
            {{ briefing: '📋 Briefing', news: '📰 News', learn: '📚 Learn', quiz: '🧠 Quiz' }[s]}
          </button>
        ))}
      </div>

      {/* BRIEFING */}
      {section === 'briefing' && (
        <>
          {gLoading && <Spinner text="Loading market data…" />}
          {fg !== undefined && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>😱 Market Sentiment</div>
              <FearGreedGauge value={fg} />
            </div>
          )}
          {global && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>🌍 Global Market</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 8 }}>
                {[
                  { label: 'Market Cap',    val: fmcap(global.total_market_cap.usd), sub: `${global.market_cap_change_percentage_24h_usd >= 0 ? '▲' : '▼'} ${Math.abs(global.market_cap_change_percentage_24h_usd).toFixed(1)}% 24h` },
                  { label: '24h Volume',    val: fmcap(global.total_volume.usd) },
                  { label: 'BTC Dominance', val: `${global.market_cap_percentage.btc.toFixed(1)}%`, sub: global.market_cap_percentage.btc > 55 ? '⚠️ Altcoins weak' : '✅ Altseason zone' },
                  { label: 'ETH Dominance', val: `${global.market_cap_percentage.eth.toFixed(1)}%` },
                ].map(({ label, val, sub }) => (
                  <div key={label} style={{ padding: '10px 12px', background: '#141414', borderRadius: 8 }}>
                    <div className="muted" style={{ fontSize: 10, marginBottom: 3 }}>{label}</div>
                    <div style={{ fontWeight: 800, fontSize: 14 }}>{val}</div>
                    {sub && <div style={{ fontSize: 10, color: sub.includes('⚠️') ? '#F7931A' : '#00C853', marginTop: 2 }}>{sub}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {topBuys.length > 0 && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>🎯 Today's Opportunities</div>
              <div className="muted" style={{ fontSize: 11, marginBottom: 8 }}>Strong momentum coins right now</div>
              {topBuys.map(c => {
                const chg = c.price_change_percentage_24h || 0
                return (
                  <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid #1E1E1E' }}>
                    {c.image && <img src={c.image} width={32} height={32} style={{ borderRadius: '50%' }} />}
                    <div style={{ flex: 1 }}>
                      <strong style={{ fontSize: 13 }}>{c.symbol.toUpperCase()}</strong>
                      <div className="muted" style={{ fontSize: 11 }}>${fp(c.current_price)}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#00C853' }}>📈 BUY</div>
                      <div className="badge badge-green" style={{ fontSize: 10 }}>▲{chg.toFixed(2)}%</div>
                    </div>
                  </div>
                )
              })}
              <div className="muted" style={{ marginTop: 8, fontSize: 10 }}>⚠️ Not financial advice. Always DYOR.</div>
            </div>
          )}
          {trending.length > 0 && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>🔥 Trending on CoinGecko</div>
              {trending.slice(0, 5).map((t, i) => (
                <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid #1E1E1E' }}>
                  <span style={{ color: '#404040', fontSize: 12, width: 20 }}>#{i + 1}</span>
                  {t.small && <img src={t.small} width={28} height={28} style={{ borderRadius: '50%' }} />}
                  <div style={{ flex: 1 }}>
                    <strong style={{ fontSize: 13 }}>{t.name}</strong>
                    <div className="muted" style={{ fontSize: 11 }}>{t.symbol?.toUpperCase()}</div>
                  </div>
                  <span className="badge badge-orange">🔥 Hot</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* NEWS */}
      {section === 'news' && (
        <>
          {newsLoading && <Spinner text="Loading news…" />}
          {!newsLoading && news.length === 0 && <div className="muted" style={{ textAlign: 'center', padding: '40px 0' }}>No news loaded.</div>}
          {news.map((art, i) => <NewsItem key={i} art={art} />)}
        </>
      )}

      {/* LEARN */}
      {section === 'learn' && (
        <>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>Tap any card to expand</div>
          {TIPS.map((tip, i) => <TipCard key={i} tip={tip} />)}
        </>
      )}

      {/* QUIZ */}
      {section === 'quiz' && (
        <div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>Question {(quizIdx % QUIZ.length) + 1} of {QUIZ.length}</div>
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
                  fontSize: 13, cursor: chosen ? 'default' : 'pointer',
                  fontWeight: chosen && correct ? 700 : 400,
                  background: chosen && correct ? '#1A2A1A' : chosen && wrong ? '#2A1A1A' : '#1A1A1A',
                  border: `1px solid ${chosen && correct ? '#00C853' : chosen && wrong ? '#FF3D57' : '#2A2A2A'}`,
                  color: chosen && correct ? '#00C853' : chosen && wrong ? '#FF3D57' : '#E0E0E0',
                }}>
                  {chosen && correct && '✓ '}{chosen && wrong && '✗ '}{opt}
                </button>
              )
            })}
            {quizAns !== null && (
              <div style={{ marginTop: 10, padding: '10px 12px', background: '#1A1A2A', borderRadius: 8, fontSize: 13, color: '#C0C0C0', lineHeight: 1.6 }}>
                💡 {q.exp}
              </div>
            )}
          </div>
          {quizAns !== null && (
            <button className="btn" onClick={() => { setQuizIdx(n => n + 1); setQuizAns(null) }}>Next Question →</button>
          )}
        </div>
      )}
    </div>
  )
}
