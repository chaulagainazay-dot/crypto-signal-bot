"""
HCG AI Crypto Trading Bot - AI Mentor
Provides contextual guidance, not just signals
Uses Baadar AI if available, otherwise local rules
"""

from typing import Dict, List, Optional
import aiohttp
import os


class AIMentor:
    def __init__(self):
        self.baadar_url = os.getenv("BAADAR_API_URL", "")
        self.baadar_key = os.getenv("BAADAR_API_KEY", "")
        self.use_baadar = bool(self.baadar_url and self.baadar_key)

    def analyze(self, symbol: str, user_profile: Dict) -> Dict:
        """Generate contextual analysis for a symbol (sync wrapper)"""
        return self._analyze_with_rules(symbol, user_profile)

    async def analyze_async(self, symbol: str, user_profile: Dict) -> Dict:
        """Async version — uses Baadar if configured, else rules"""
        if self.use_baadar:
            return await self._analyze_with_baadar(symbol, user_profile)
        return self._analyze_with_rules(symbol, user_profile)

    def _analyze_with_rules(self, symbol: str, user_profile: Dict) -> Dict:
        """Local rule-based analysis (free, no external AI API)"""
        analysis = {
            'recommendation': 'WAIT',
            'reasons': [],
            'entry_conditions': [],
            'allocation': {},
            'risk_warnings': [],
            'entry_zone': None,
            'stop_loss': None,
            'targets': [],
        }

        # BTC dominance / resistance context
        analysis['reasons'].append(
            "BTC is at key resistance. Wait for confirmed breakout before entering alts."
        )

        # Portfolio concentration check
        portfolio = user_profile.get('portfolio', {})
        alt_ratio = self._calculate_alt_ratio(portfolio)
        risk = user_profile.get('risk_profile', 'medium')

        if alt_ratio > 0.7 and risk == 'medium':
            analysis['risk_warnings'].append(
                f"Your portfolio is {alt_ratio * 100:.0f}% altcoins. "
                "Consider reducing to 60% for a medium-risk profile."
            )
        elif alt_ratio > 0.8 and risk == 'conservative':
            analysis['risk_warnings'].append(
                f"Portfolio is {alt_ratio * 100:.0f}% altcoins — too risky for conservative profile. "
                "Target: 30% altcoins max."
            )

        # Entry conditions
        analysis['entry_conditions'] = [
            "BTC closes above resistance on 4h timeframe",
            f"{symbol} retests support with volume confirmation",
            "Volume increases 30%+ vs 7-day average",
        ]

        # Suggest allocation
        capital = user_profile.get('capital', 1000)
        analysis['allocation'] = self._suggest_allocation(capital, risk)

        return analysis

    async def _analyze_with_baadar(self, symbol: str, user_profile: Dict) -> Dict:
        """Use Baadar AI for richer analysis"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.baadar_key}"}
                payload = {"symbol": symbol, "user_profile": user_profile, "mode": "mentor"}
                async with session.post(
                    f"{self.baadar_url}/api/mentor",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"Baadar AI error: {e}")
        return self._analyze_with_rules(symbol, user_profile)

    def _calculate_alt_ratio(self, portfolio: Dict) -> float:
        """Altcoin share of portfolio (BTC + ETH treated as large caps)"""
        if not portfolio:
            return 0.0
        large_caps = {'BTC', 'ETH'}
        total = sum(portfolio.values())
        if total == 0:
            return 0.0
        large_cap_value = sum(v for k, v in portfolio.items() if k.upper() in large_caps)
        return 1.0 - (large_cap_value / total)

    def _suggest_allocation(self, capital: float, risk: str) -> Dict:
        """Return dollar amounts for each asset class"""
        templates = {
            'conservative': {'BTC': 0.50, 'ETH': 0.30, 'SOL': 0.10, 'cash': 0.10},
            'medium':       {'BTC': 0.40, 'ETH': 0.30, 'SOL': 0.20, 'cash': 0.10},
            'aggressive':   {'BTC': 0.30, 'ETH': 0.30, 'SOL': 0.30, 'cash': 0.10},
        }
        alloc = templates.get(risk, templates['medium'])
        return {k: round(v * capital, 2) for k, v in alloc.items()}

    def format_analysis(self, symbol: str, analysis: Dict, capital: float) -> str:
        """Format analysis as a Telegram-ready message"""
        lines = [
            f"🤖 <b>AI Mentor: {symbol} Analysis</b>\n",
            f"📌 <b>Recommendation:</b> {analysis['recommendation']}\n",
        ]

        if analysis['reasons']:
            lines.append("❓ <b>Why:</b>")
            for r in analysis['reasons']:
                lines.append(f"  • {r}")
            lines.append("")

        if analysis['risk_warnings']:
            lines.append("⚠️ <b>Risk Warnings:</b>")
            for w in analysis['risk_warnings']:
                lines.append(f"  ⚡ {w}")
            lines.append("")

        if analysis['entry_conditions']:
            lines.append("✅ <b>Wait for:</b>")
            for c in analysis['entry_conditions']:
                lines.append(f"  ✔ {c}")
            lines.append("")

        if analysis['allocation']:
            lines.append(f"💼 <b>Suggested Allocation (${capital:,.0f}):</b>")
            for asset, amount in analysis['allocation'].items():
                pct = int(amount / capital * 100)
                lines.append(f"  {asset}: ${amount:,.0f} ({pct}%)")
            lines.append("")

        lines.append("⚠️ <i>Educational only. Not financial advice.</i>")
        return "\n".join(lines)

    def get_daily_brief(self) -> str:
        """Morning market brief"""
        return (
            "☀️ <b>Good Morning! Your 30-second brief:</b>\n\n"
            "₿ BTC: Cautiously bullish — ETF inflows continue\n"
            "Ξ ETH: Neutral — waiting for catalyst\n"
            "🌐 Alts: Mixed — SOL showing strength\n\n"
            "⚡ <b>Top Event:</b> Watch Fed language today\n\n"
            "<b>Key Levels:</b>\n"
            "  BTC Support: $105,000\n"
            "  ETH Support: $3,800\n"
            "  SOL Support: $178\n\n"
            "Have a great trading day! 🎯"
        )
