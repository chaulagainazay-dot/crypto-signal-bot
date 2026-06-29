import { useState, useEffect } from 'react'
import { fetchGlobal, fetchTopCoins, fetchTrending, fetchCryptoNews, fmcap, fp } from '../api/coingecko'
import Spinner from '../components/Spinner'

const TIPS = [
  { icon: '💡', title: 'What is DCA?', body: 'Dollar-Cost Averaging means buying a fixed dollar amount regularly (e.g. $20 every week). You buy more when price is low and less when high — averaging your cost over time. It removes the stress of trying to "time the market".' },
  { icon: '🛑', title: 'Always use a Stop-Loss', body: 'A stop-loss is a price below your buy point where you\'d sell to limit losses. Example: if you buy at $100, set a stop-loss at $85 (−15%). This protects you from big drops. Most exchanges support this automatically.' },
  { icon: '🎯', title: 'Market Cap > Price', body: 'A coin priced at $0.001 can still be worth billions if there are trillions of coins. Always check market cap — it tells you the real size of a project. A $100 coin with 1M supply is smaller than a $0.001 coin with 1 quadrillion supply.' },
  { icon: '📊', title: 'Volume tells the truth', body: 'High trading volume with a price increase = real move with conviction. High volume with price drop = real selling pressure. Low volume moves are usually fake and reverse quickly.' },
  { icon: '🔥', title: 'FOMO is your enemy', body: 'Fear Of Missing Out makes you buy after a coin already pumped 50%. By then, early buyers are selling to you. If you missed the move, wait for the next dip — there is always another opportunity.' },
  { icon: '🌊', title: 'BTC leads everything', body: 'When Bitcoin goes up strongly, most altcoins follow. When Bitcoin drops, altcoins usually drop harder. Always check what BTC is doing before making a trade. BTC dominance above 55% = altcoins are weak.' },
  { icon: '🏦', title: 'Only invest what you can lose', body: 'Crypto is highly volatile. A coin can drop 90% and stay there. Never invest rent money, emergency funds, or borrowed money. Start small, learn the market, grow slowly.' },
  { icon: '📰', title: 'News moves markets', body: 'Partnership announcements, exchange listings, and regulation news can pump or crash a coin in minutes. Follow coin-specific news in the Research tab and set price alerts for your holdings.' },
]

function FearGreed({ value }) {
  const color = value >= 75 ? '#FF3D57' : value >= 55 ? '#F7931A' : value >= 45 ? '#FFD700' : value >= 25 ? '#00C853' : '#00E676'
  const label = value >= 75 ? 'Extreme Greed' : value >= 55 ? 'Greed' : value >= 45 ? 'Neutral' : value >= 25 ? 'Fear' : 'Extreme Fear'
  const hint  = value >= 75 ? 'Market is overheated. Be careful buying now.'
              : value >= 55 ? 'Optimism is high. Cautious is wise.'
              : value >= 45 ? 'Balanced market. No strong direction.'
              : value >= 25 ? 'People are scared — can be a buying opportunity.'
              : 'Panic selling. Historically good time to buy in portions.'
  const radius = 48, circ = 2 * Math.PI * radius
  const dash = (value / 100) * circ

  return (
    <div style={{ textAlign: 'center', padding: '8px 0' }}>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <svg width={120} height={120}>
          <circle cx={60} cy={60} r={radius} fill="none" stroke="#2A2A2A" strokeWidth={10} />
          <circle cx={60} cy={60} r={radius} fill="none" stroke={color} strokeWidth={10}
            strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
            transform="rotate(-90 60 60)" />
          <text x={60} y={54} textAnchor="middle" fill={color} fontSize={24} fontWeight={900}>{value}</text>
          <text x={60} y={72} textAnchor="middle" fill="#808080" fontSize={10}>/100</text>
        </svg>
      </div>
      <div style={{ fontWeight: 800, color, fontSize: 16, marginTop: 4 }}>{label}</div>
      <div className="muted" style={{ fontSize: 12, marginTop: 4, padding: '0 16px' }}>{hint}</div>
    </div>
  )
}

function MiniSignal({ coin }) {
  const chg = coin.price_change_percentage_24h || 0
  const vr  = (coin.total_volume || 0) / (coin.market_cap || 1)
  const isBuy = chg > 4 && vr > 0.05
  const color = isBuy ? '#00C853' : chg < -4 ? '#FF3D57' : '#F7931A'
  const label = isBuy ? '📈 BUY' : chg < -4 ? '📉 SELL' : '➡️ HOLD'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid #1E1E1E' }}>
      {coin.image && <img src={coin.image} width={32} height={32} style={{ borderRadius: '50%' }} />}
      <div style={{ flex: 1 }}>
        <strong style={{ fontSize: 13 }}>{coin.symbol?.toUpperCase()}</strong>
        <div className="muted" style={{ fontSize: 11 }}>${fp(coin.current_price)}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>{label}</div>
        <div className={`badge badge-${chg >= 0 ? 'green' : 'red'}`} style={{ fontSize: 10 }}>
          {chg >= 0 ? '▲' : '▼'} {Math.abs(chg).toFixed(2)}%
        </div>
      </div>
    </div>
  )
}

const QUIZ = [
  {
    q: 'What does "market cap" mean?',
    opts: ['The highest price ever', 'Price × total supply = total value', 'How much you can trade per day', 'The number of exchanges listing it'],
    ans: 1, exp: 'Market cap = current price × circulating supply. It shows the total value of all coins in circulation.',
  },
  {
    q: 'A coin drops 80% from ATH. What does that mean?',
    opts: ['It is worthless', 'It is 80% below its all-time high price', 'Volume dropped 80%', 'The project shut down'],
    ans: 1, exp: 'ATH = All-Time High. If a coin is 80% below ATH, it means it was 5× higher before. Could be oversold — or just broken. Research matters.',
  },
  {
    q: 'What is Dollar-Cost Averaging (DCA)?',
    opts: ['Buying all at once at the lowest price', 'Buying small fixed amounts regularly', 'Setting a stop-loss', 'Selling at the top'],
    ans: 1, exp: 'DCA = buy $X every week/month regardless of price. Reduces risk of buying at the worst time.',
  },
  {
    q: 'High trading volume with a big price increase means:',
    opts: ['A fake pump, ignore it', 'A real move with strong buyer interest', 'The coin will crash soon', 'Nothing — volume does not matter'],
    ans: 1, exp: 'Volume confirms price moves. High volume + price rise = real momentum. Low volume + price rise = weak, often reverses.',
  },
]

function newsSentiment(title = '') {
  const t = title.toLowerCase()
  const pos = ['surge','rally','bullish','pump','breakout','gain','high','rise','soar','ath','launch','partnership','adoption','buy','approve','etf','record']
  const neg = ['crash','drop','bear','dump','ban','hack','fraud','scam','fall','plunge','fear','warning','low','down','sell','arrest','fine','lawsuit']
  const p = pos.filter(w => t.includes(w)).length
  const n = neg.filter(w => t.includes(w)).length
  if (p > n) return { label: '🟢 Bullish', color: '#00C853' }
  if (n > p) return { label: '🔴 Bearish', color: '#FF3D57' }
  return             { label: '⚪ Neutral', color: '#808080' }
}

function NewsSection({ articles, loading }) {
  if (loading) return <Spinner text="Loading market news…" />
  if (!articles.length) return (
    <div style={{ textAlign: 'center', color: '#606060', padding: '40px 0' }}>No news loaded.</div>
  )
  return (
    <div>
      <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
        Latest crypto market news · Tap to read full article
      </div>
      {articles.map((art, i) => {
        const s = newsSentiment(art.title)
        return (
          <a key={i} href={art.url} target="_blank" rel="noreferrer"
            style={{ display: 'block', textDecoration: 'none', marginBottom: 8 }}>
            <div className="card" style={{ borderLeft: `3px solid ${s.color}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: s.color }}>{s.label}</span>
                <span className="muted" style={{ fontSize: 10 }}>
                  {new Date(art.published_on * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                </span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#E0E0E0', lineHeight: 1.5, marginBottom: 4 }}>
                {art.title}
              </div>
              {art.body && (
                <div className="muted" style={{ fontSize: 11, lineHeight: 1.5 }}>
                  {art.body.slice(0, 120)}{art.body.length > 120 ? '…' : ''}
                </div>
              )}
              <div style={{ marginTop: 6, fontSize: 10, color: '#505050' }}>
                {art.source_info?.name || art.source} ↗
              </div>
            </div>
          </a>
        )
      })}
    </div>
  )
}

export default function Guide() {
  const [global,    setGlobal]   = useState(null)
  const [fgValue,   setFG]       = useState(null)
  const [topCoins,  setTop]      = useState([])
  const [trending,  setTrend]    = useState([])
  const [news,      setNews]     = useState([])
  const [loading,   setLoading]  = useState(true)
  const [tipIdx,    setTipIdx]   = useState(() => Math.floor(Math.random() * TIPS.length))
  const [quizIdx,   setQuizIdx]  = useState(0)
  const [quizAns,   setQuizAns]  = useState(null)
  const [section,   setSection]  = useState('briefing') // briefing | news | learn | quiz
  const [fullNews,  setFullNews] = useState([])
  const [newsLoad,  setNewsLoad] = useState(false)

  useEffect(() => {
    Promise.all([
      fetchGlobal(),
      fetchTopCoins(20),
      fetchTrending(),
      fetch('https://api.alternative.me/fng/?limit=1').then(r => r.json()).catch(() => null),
      fetchCryptoNews('cryptocurrency', 4),
    ]).then(([g, coins, trend, fng, cryptoNews]) => {
      setGlobal(g)
      setTop(coins)
      setTrend(trend.slice(0, 5))
      if (fng?.data?.[0]?.value) setFG(parseInt(fng.data[0].value))
      setNews(cryptoNews)
    }).catch(console.error)
    .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (section !== 'news' || fullNews.length > 0 || newsLoad) return
    setNewsLoad(true)
    fetchCryptoNews('cryptocurrency', 20).then(articles => {
      setFullNews(articles)
    }).catch(() => {}).finally(() => setNewsLoad(false))
  }, [section])

  const topBuys = topCoins
    .filter(c => (c.price_change_percentage_24h || 0) > 4 && (c.total_volume / c.market_cap) > 0.05)
    .slice(0, 3)

  const SECTIONS = ['briefing', 'news', 'learn', 'quiz']
  const SECTION_LABELS = { briefing: '📋 Briefing', news: '📰 News', learn: '📚 Learn', quiz: '🧠 Quiz' }

  return (
    <div className="tab-content">
      <h2>🤖 Guide</h2>

      {/* Section pills */}
      <div className="pills">
        {SECTIONS.map(s => (
          <button key={s} className={`pill${section === s ? ' active' : ''}`} onClick={() => setSection(s)}>
            {SECTION_LABELS[s]}
          </button>
        ))}
      </div>

      {loading && <Spinner text="Loading market briefing…" />}

      {/* ── BRIEFING ── */}
      {!loading && section === 'briefing' && (
        <>
          {/* Fear & Greed */}
          {fgValue !== null && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>😱 Market Sentiment</div>
              <FearGreed value={fgValue} />
            </div>
          )}

          {/* Global stats */}
          {global && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>🌍 Global Market</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
                {[
                  { label: 'Total Market Cap', val: fmcap(global.mcap), sub: `${global.change >= 0 ? '▲' : '▼'} ${Math.abs(global.change).toFixed(1)}% 24h` },
                  { label: '24h Volume',        val: fmcap(global.vol) },
                  { label: 'BTC Dominance',     val: `${global.btcDom.toFixed(1)}%`, sub: global.btcDom > 55 ? '⚠️ Altcoins weak' : '✅ Altseason possible' },
                  { label: 'ETH Dominance',     val: `${global.ethDom.toFixed(1)}%` },
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

          {/* Today's opportunities */}
          {topBuys.length > 0 && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>🎯 Today's Opportunities</div>
              <div className="muted" style={{ fontSize: 11, marginBottom: 8 }}>Coins with strong momentum right now</div>
              {topBuys.map(c => <MiniSignal key={c.id} coin={c} />)}
              <div className="muted" style={{ marginTop: 8, fontSize: 10 }}>⚠️ Not financial advice. Always DYOR.</div>
            </div>
          )}

          {/* Trending */}
          {trending.length > 0 && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>🔥 Trending on CoinGecko</div>
              {trending.map((t, i) => (
                <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid #1E1E1E' }}>
                  <span style={{ color: '#404040', fontSize: 12, width: 20 }}>#{i+1}</span>
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

          {/* Market news */}
          {news.length > 0 && (
            <div className="card" style={{ marginBottom: 12 }}>
              <div className="section-title" style={{ marginTop: 0 }}>📰 Crypto Headlines</div>
              {news.map((art, i) => (
                <a key={i} href={art.url} target="_blank" rel="noreferrer"
                  style={{ display: 'block', padding: '10px 0', borderBottom: '1px solid #1E1E1E', textDecoration: 'none' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#E0E0E0', lineHeight: 1.4, marginBottom: 4 }}>{art.title}</div>
                  <div className="muted" style={{ fontSize: 10 }}>{art.source_info?.name || art.source} · {new Date(art.published_on*1000).toLocaleDateString()}</div>
                </a>
              ))}
            </div>
          )}
        </>
      )}

      {/* ── NEWS ── */}
      {section === 'news' && (
        <NewsSection articles={fullNews} loading={newsLoad} />
      )}

      {/* ── LEARN ── */}
      {!loading && section === 'learn' && (
        <>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>Tap any card to read the full tip</div>
          {TIPS.map((tip, i) => {
            const [open, setOpen] = useState(false)
            return (
              <div key={i} className="card" style={{ marginBottom: 10, cursor: 'pointer' }} onClick={() => setOpen(o => !o)}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 22 }}>{tip.icon}</span>
                  <strong style={{ fontSize: 14, flex: 1 }}>{tip.title}</strong>
                  <span className="muted">{open ? '▲' : '▼'}</span>
                </div>
                {open && (
                  <p style={{ marginTop: 10, fontSize: 13, color: '#C0C0C0', lineHeight: 1.7 }}>{tip.body}</p>
                )}
              </div>
            )
          })}
        </>
      )}

      {/* ── QUIZ ── */}
      {!loading && section === 'quiz' && (() => {
        const q = QUIZ[quizIdx % QUIZ.length]
        return (
          <div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>Question {(quizIdx % QUIZ.length) + 1} of {QUIZ.length}</div>
            <div className="card" style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 16, lineHeight: 1.5 }}>{q.q}</div>
              {q.opts.map((opt, i) => {
                const chosen  = quizAns !== null
                const correct = i === q.ans
                const wrong   = chosen && quizAns === i && !correct
                return (
                  <button key={i} onClick={() => !chosen && setQuizAns(i)}
                    style={{
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
              <button className="btn" onClick={() => { setQuizIdx(n => n + 1); setQuizAns(null) }}>
                Next Question →
              </button>
            )}
          </div>
        )
      })()}
    </div>
  )
}
