"""
HCG AI Crypto Trading Bot - Risk Meter
Position sizing, risk/reward, and scenario analysis
"""

from typing import Dict, Optional


class RiskMeter:
    def calculate(
        self,
        signal: Dict,
        portfolio_value: float,
        risk_per_trade: float = 0.02,
    ) -> Dict:
        entry  = signal.get('entry', signal.get('price', 0))
        stop   = signal.get('stop')
        target = signal.get('target')

        if not stop or not target or entry <= 0:
            return {
                'risk_level': 'UNKNOWN', 'reward_level': 'UNKNOWN',
                'risk_reward_ratio': 0, 'position_size': 0,
                'position_size_percent': 0, 'max_loss': 0, 'max_gain': 0,
                'scenarios': {},
            }

        risk_amount   = portfolio_value * risk_per_trade
        risk_pct      = abs(entry - stop) / entry
        reward_pct    = abs(target - entry) / entry
        position_size = risk_amount / risk_pct if risk_pct > 0 else 0
        rr_ratio      = reward_pct / risk_pct if risk_pct > 0 else 0
        max_gain      = position_size * reward_pct

        return {
            'risk_level':            self._risk_level(risk_pct),
            'reward_level':          self._reward_level(reward_pct),
            'risk_reward_ratio':     round(rr_ratio, 2),
            'position_size':         round(position_size, 2),
            'position_size_percent': round(position_size / portfolio_value * 100, 1) if portfolio_value else 0,
            'max_loss':              round(risk_amount, 2),
            'max_gain':              round(max_gain, 2),
            'scenarios': {
                'best_case':  round(max_gain * 1.5, 2),
                'base_case':  round(max_gain, 2),
                'worst_case': round(-risk_amount, 2),
            },
        }

    def calculate_portfolio_risk(self, portfolio: Dict) -> Dict:
        """Rough portfolio-wide risk estimate"""
        total = sum(portfolio.values())
        if total == 0:
            return {'portfolio_risk': 'UNKNOWN', 'var_95': 0}

        # Simplified: assume 50% annualised volatility for crypto
        vol = 0.50
        var_95 = total * vol * 1.65

        return {
            'portfolio_risk': 'High' if vol > 0.4 else 'Medium' if vol > 0.2 else 'Low',
            'volatility_estimate_pct': round(vol * 100, 1),
            'var_95': round(var_95, 2),
            'max_drawdown_estimate': round(var_95 * 1.5, 2),
        }

    def _risk_level(self, risk_pct: float) -> str:
        if risk_pct < 0.03: return 'Low'
        if risk_pct < 0.06: return 'Medium'
        return 'High'

    def _reward_level(self, reward_pct: float) -> str:
        if reward_pct > 0.15: return 'High'
        if reward_pct > 0.08: return 'Medium'
        return 'Low'

    def format_card(self, signal: Dict, result: Dict) -> str:
        sym = signal.get('symbol', '?')
        lines = [
            f"⚖️ <b>Risk Meter: {sym}</b>\n",
            f"Risk:   <b>{result['risk_level']}</b>  |  Reward: <b>{result['reward_level']}</b>",
            f"R:R     1:{result['risk_reward_ratio']}\n",
            "<b>Position Sizing:</b>",
            f"  Position Size: ${result['position_size']:,.0f} ({result['position_size_percent']}%)",
            f"  Max Loss:  -${result['max_loss']:,.0f}",
            f"  Max Gain:  +${result['max_gain']:,.0f}\n",
            "<b>Scenario Analysis:</b>",
            f"  Best case:  +${result['scenarios'].get('best_case', 0):,.0f}",
            f"  Base case:  +${result['scenarios'].get('base_case', 0):,.0f}",
            f"  Worst case: -${abs(result['scenarios'].get('worst_case', 0)):,.0f}",
        ]
        return "\n".join(lines)
