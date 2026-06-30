"""
HCG AI Crypto Trading Bot - Psychology Tracker
Analyzes trading behavior and surfaces insights
"""

from typing import Dict, List
from datetime import datetime


class PsychologyTracker:
    def analyze_trades(self, trades: List[Dict]) -> Dict:
        mistakes = {
            'late_entry': 0,
            'hold_too_long': 0,
            'fomo': 0,
            'no_stop_loss': 0,
            'revenge_trading': 0,
            'ignored_signal': 0,
        }

        for i, trade in enumerate(trades):
            # Late entry: entered >1h after optimal entry
            oe = trade.get('optimal_entry_time')
            et = trade.get('entry_time')
            if oe and et and et > oe + 3600:
                mistakes['late_entry'] += 1

            # Held too long: exited below 90% of target
            ep = trade.get('exit_price', 0)
            tp = trade.get('target_price', 0)
            if ep and tp and tp > 0 and ep < tp * 0.9:
                mistakes['hold_too_long'] += 1

            # FOMO: entered within 1h of local top
            lt = trade.get('local_top_time')
            if lt and et and abs(et - lt) < 3600:
                mistakes['fomo'] += 1

            # No stop loss set
            if not trade.get('stop_loss'):
                mistakes['no_stop_loss'] += 1

            # Revenge trading: entered <2h after a losing trade
            if i > 0:
                prev = trades[i - 1]
                if (prev.get('pnl', 0) < 0
                        and et and prev.get('exit_time')
                        and et - prev['exit_time'] < 7200):
                    mistakes['revenge_trading'] += 1

        total_mistakes = sum(mistakes.values())
        score = max(0, 100 - total_mistakes * 5)

        return {
            'score': score,
            'mistakes': mistakes,
            'insights': self._generate_insights(trades, mistakes),
            'patterns': self._find_patterns(trades),
            'strengths': self._find_strengths(trades, mistakes),
        }

    def _generate_insights(self, trades: List[Dict], mistakes: Dict) -> List[str]:
        insights = []
        if mistakes['late_entry'] > 2:
            insights.append(
                "You tend to enter 2–3 hours after optimal entry. "
                "Set price alerts at support levels instead of watching charts continuously."
            )
        if mistakes['fomo'] > 1:
            insights.append(
                "FOMO detected in your history. "
                "Wait 24 hours after a pump before considering entry."
            )
        if mistakes['hold_too_long'] > 2:
            insights.append(
                "You often hold past the optimal exit. "
                "Try taking 40% off at Target 1, 30% at Target 2, hold 30%."
            )
        if mistakes['no_stop_loss'] > 0:
            insights.append(
                "Some trades had no stop loss. "
                "Always set a stop before entering — it is your insurance."
            )
        if mistakes['revenge_trading'] > 0:
            insights.append(
                "Revenge trading detected. "
                "Take a 24-hour break after two consecutive losses."
            )
        return insights

    def _find_patterns(self, trades: List[Dict]) -> Dict:
        if not trades:
            return {}

        profitable_hours: Dict[int, int] = {}
        setups: Dict[str, Dict] = {}

        for trade in trades:
            if trade.get('pnl', 0) > 0 and trade.get('entry_time'):
                h = datetime.fromtimestamp(trade['entry_time']).hour
                profitable_hours[h] = profitable_hours.get(h, 0) + 1

            st = trade.get('setup_type')
            if st:
                if st not in setups:
                    setups[st] = {'wins': 0, 'total': 0}
                setups[st]['total'] += 1
                if trade.get('pnl', 0) > 0:
                    setups[st]['wins'] += 1

        best_hour = max(profitable_hours, key=profitable_hours.get) if profitable_hours else None
        best_setup = (
            max(setups, key=lambda s: setups[s]['wins'] / max(setups[s]['total'], 1))
            if setups else None
        )

        return {'best_hour': best_hour, 'best_setup': best_setup}

    def _find_strengths(self, trades: List[Dict], mistakes: Dict) -> List[str]:
        strengths = []
        if mistakes['no_stop_loss'] == 0:
            strengths.append("Consistent use of stop losses")

        if trades:
            wins = [t for t in trades if t.get('pnl', 0) > 0]
            win_rate = len(wins) / len(trades)
            if win_rate > 0.6:
                strengths.append(f"Strong win rate: {win_rate * 100:.0f}%")

            losses = [t for t in trades if t.get('pnl', 0) < 0]
            if wins and losses:
                avg_win = sum(t['pnl'] for t in wins) / len(wins)
                avg_loss = abs(sum(t['pnl'] for t in losses) / len(losses))
                if avg_loss > 0 and avg_win / avg_loss >= 2:
                    strengths.append("Good risk/reward ratio — winners 2× larger than losers")

        if not strengths:
            strengths.append("Consistent trader — keep learning and improving")
        return strengths

    def format_report(self, result: Dict) -> str:
        score = result['score']
        lines = [
            f"🧠 <b>Trade Psychology Report</b>\n",
            f"Psychology Score: <b>{score}/100</b>\n",
        ]

        if result['insights']:
            lines.append("💡 <b>AI Insights:</b>")
            for ins in result['insights']:
                lines.append(f"  • {ins}")
            lines.append("")

        if result['strengths']:
            lines.append("✅ <b>Strengths:</b>")
            for s in result['strengths']:
                lines.append(f"  ✔ {s}")
            lines.append("")

        m = result['mistakes']
        if any(v > 0 for v in m.values()):
            lines.append("❌ <b>Recurring Mistakes:</b>")
            labels = {
                'late_entry': 'Late entry',
                'hold_too_long': 'Held too long',
                'fomo': 'FOMO buying',
                'no_stop_loss': 'Missing stop loss',
                'revenge_trading': 'Revenge trading',
            }
            for k, label in labels.items():
                if m.get(k, 0) > 0:
                    lines.append(f"  ⚡ {label} ({m[k]}×)")

        return "\n".join(lines)
