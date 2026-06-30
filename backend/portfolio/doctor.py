"""
HCG AI Crypto Trading Bot - Portfolio Doctor
Diagnoses portfolio health and provides fix recommendations
"""

from typing import Dict, List


class PortfolioDoctor:
    MEME_COINS = {'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'BABYDOGE'}
    LARGE_CAPS = {'BTC', 'ETH'}
    SOL_ECO = {'SOL', 'JUP', 'RAY', 'BONK', 'ORCA'}
    ETH_ECO = {'ETH', 'OP', 'ARB', 'MATIC', 'LDO'}

    def diagnose(self, portfolio: Dict) -> Dict:
        scores = {
            'diversification':        self._diversification_score(portfolio),
            'risk_balance':           self._risk_balance_score(portfolio),
            'market_cap_distribution': self._mcap_score(portfolio),
            'correlation':            self._correlation_score(portfolio),
            'cash_reserve':           self._cash_score(portfolio),
        }
        total = sum(scores.values()) / len(scores)

        return {
            'overall_score': int(total),
            'health_status': (
                'HEALTHY' if total > 70 else
                'NEEDS_ATTENTION' if total > 40 else
                'CRITICAL'
            ),
            'breakdown': scores,
            'problems': self._find_problems(portfolio, scores),
            'recommendations': self._generate_recommendations(portfolio, scores),
            'target_allocation': self._suggest_target(),
        }

    def _diversification_score(self, p: Dict) -> float:
        total = sum(p.values())
        if total == 0:
            return 50.0
        weights = [v / total for v in p.values() if v > 0]
        hhi = sum(w ** 2 for w in weights)
        return round((1 - hhi) * 100, 1)

    def _risk_balance_score(self, p: Dict) -> float:
        meme_val = sum(v for k, v in p.items() if k.upper() in self.MEME_COINS)
        total = sum(p.values())
        if total == 0:
            return 50.0
        ratio = meme_val / total
        if ratio > 0.3: return 30.0
        if ratio > 0.2: return 50.0
        if ratio > 0.1: return 70.0
        return 90.0

    def _mcap_score(self, p: Dict) -> float:
        lc_val = sum(v for k, v in p.items() if k.upper() in self.LARGE_CAPS)
        total = sum(p.values())
        if total == 0:
            return 50.0
        ratio = lc_val / total
        if ratio < 0.2: return 30.0
        if ratio < 0.4: return 60.0
        return 85.0

    def _correlation_score(self, p: Dict) -> float:
        sol_val = sum(v for k, v in p.items() if k.upper() in self.SOL_ECO)
        eth_val = sum(v for k, v in p.items() if k.upper() in self.ETH_ECO)
        total = sum(p.values())
        if total == 0:
            return 50.0
        max_eco = max(sol_val, eth_val) / total
        if max_eco > 0.5: return 40.0
        if max_eco > 0.3: return 65.0
        return 85.0

    def _cash_score(self, p: Dict) -> float:
        cash = p.get('cash', p.get('USDT', p.get('USDC', 0)))
        total = sum(p.values())
        if total == 0:
            return 50.0
        ratio = cash / total
        if ratio < 0.05: return 30.0
        if ratio < 0.10: return 60.0
        if ratio < 0.20: return 80.0
        return 90.0

    def _find_problems(self, p: Dict, scores: Dict) -> List[str]:
        problems = []
        if scores['risk_balance'] < 50:
            problems.append("Too much meme coin exposure (>20%)")
        if scores['market_cap_distribution'] < 50:
            problems.append("No large cap stability (BTC/ETH <20%)")
        if scores['cash_reserve'] < 30:
            problems.append("No cash reserve for dips")
        if scores['correlation'] < 50:
            problems.append("High ecosystem correlation — diversify across chains")
        if scores['diversification'] < 50:
            problems.append("Portfolio too concentrated in one asset")
        return problems

    def _generate_recommendations(self, p: Dict, scores: Dict) -> List[str]:
        recs = []
        if scores['risk_balance'] < 50:
            recs.append("Reduce meme coin exposure to <20% of portfolio")
        if scores['market_cap_distribution'] < 50:
            recs.append("Increase BTC + ETH to at least 40% for stability")
        if scores['cash_reserve'] < 30:
            recs.append("Build a 10–20% cash reserve (USDT/USDC) for buying dips")
        if scores['correlation'] < 50:
            recs.append("Diversify across ecosystems: SOL, ETH L2s, BTC layer-2")
        return recs

    def _suggest_target(self) -> Dict:
        return {'BTC': 0.40, 'ETH': 0.30, 'SOL': 0.20, 'cash': 0.10}

    def format_report(self, result: Dict) -> str:
        score = result['overall_score']
        status = result['health_status']
        emoji = '✅' if status == 'HEALTHY' else '⚠️' if status == 'NEEDS_ATTENTION' else '🚨'

        lines = [
            f"🏥 <b>Portfolio Doctor Report</b>\n",
            f"{emoji} Overall Health: <b>{status}</b>",
            f"Score: {score}/100\n",
        ]

        if result['problems']:
            lines.append("❌ <b>Problems Found:</b>")
            for p in result['problems']:
                lines.append(f"  • {p}")
            lines.append("")

        if result['recommendations']:
            lines.append("💡 <b>Recommendations:</b>")
            for i, r in enumerate(result['recommendations'], 1):
                lines.append(f"  {i}. {r}")
            lines.append("")

        lines.append("📊 <b>Target Allocation:</b>")
        for asset, pct in result['target_allocation'].items():
            lines.append(f"  {asset.upper()}: {int(pct * 100)}%")

        return "\n".join(lines)
