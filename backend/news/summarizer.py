"""
HCG AI Crypto Trading Bot - News Summarizer
Aggregates crypto news and generates AI-style daily briefs
Uses CryptoCompare (free, no key required)
"""

from typing import Dict, List, Optional
import aiohttp


class NewsSummarizer:
    CRYPTOCOMPARE_URL = "https://min-api.cryptocompare.com/data/v2/news/"

    async def fetch_articles(self, limit: int = 20) -> List[Dict]:
        """Fetch latest crypto news (no API key needed for basic tier)"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.CRYPTOCOMPARE_URL,
                    params={'lang': 'EN', 'limit': limit},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get('Data', [])
        except Exception as e:
            print(f"[NewsSummarizer] fetch error: {e}")
            return []

    def _keyword_sentiment(self, text: str) -> str:
        text = text.lower()
        bullish = ['surge', 'rally', 'all-time high', 'ath', 'bullish', 'inflow',
                   'adoption', 'etf', 'approve', 'buy', 'growth', 'positive']
        bearish = ['crash', 'dump', 'sell', 'bear', 'decline', 'hack', 'ban',
                   'lawsuit', 'sec', 'regulation', 'fear', 'outflow', 'loss']
        b = sum(1 for w in bullish if w in text)
        d = sum(1 for w in bearish if w in text)
        if b > d + 1: return 'Bullish 📈'
        if d > b + 1: return 'Bearish 📉'
        return 'Neutral ➡️'

    def _filter_for_symbol(self, articles: List[Dict], symbol: str) -> List[Dict]:
        sym_lower = symbol.lower()
        return [
            a for a in articles
            if sym_lower in (a.get('title', '') + a.get('body', '')).lower()
        ]

    def generate_daily_brief(self, articles: List[Dict]) -> Dict:
        btc_arts = self._filter_for_symbol(articles, 'BTC')
        eth_arts = self._filter_for_symbol(articles, 'ETH')
        alt_arts = [a for a in articles if a not in btc_arts and a not in eth_arts]

        btc_text = ' '.join(a.get('title', '') for a in btc_arts[:5])
        eth_text = ' '.join(a.get('title', '') for a in eth_arts[:5])
        alt_text = ' '.join(a.get('title', '') for a in alt_arts[:5])

        top_event = articles[0].get('title', 'No major events today') if articles else 'No articles available'

        return {
            'btc_sentiment': self._keyword_sentiment(btc_text),
            'eth_sentiment': self._keyword_sentiment(eth_text),
            'alt_sentiment': self._keyword_sentiment(alt_text),
            'top_event': top_event,
            'key_levels': {'BTC': '105,000', 'ETH': '3,800', 'SOL': '178'},
            'article_count': len(articles),
        }

    def format_brief(self, brief: Dict) -> str:
        lines = [
            "📰 <b>AI News Summary</b>",
            f"<i>{brief.get('article_count', 0)} articles analysed</i>\n",
            f"₿ BTC: {brief['btc_sentiment']}",
            f"Ξ ETH: {brief['eth_sentiment']}",
            f"🌐 Alts: {brief['alt_sentiment']}\n",
            f"⚡ Top Event: {brief['top_event']}\n",
            "<b>Key Levels to Watch:</b>",
        ]
        for asset, level in brief.get('key_levels', {}).items():
            lines.append(f"  {asset}: ${level}")
        return "\n".join(lines)

    def format_articles(self, articles: List[Dict], limit: int = 5) -> str:
        if not articles:
            return "No news articles available."
        lines = ["📰 <b>Latest Crypto News</b>\n"]
        for art in articles[:limit]:
            title = art.get('title', 'No title')
            url   = art.get('url', '')
            src   = art.get('source', '')
            lines.append(f"• <a href='{url}'>{title}</a> — {src}")
        return "\n".join(lines)
