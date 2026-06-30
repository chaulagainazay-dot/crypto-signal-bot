"""
HCG AI Crypto Trading Bot - Whale Tracker
Monitors large transactions and exchange flows using free APIs
"""

from typing import Dict, List, Optional
import aiohttp


class WhaleTracker:
    WHALE_ALERT_BASE = "https://api.whale-alert.io"

    def __init__(self, whale_alert_key: str = ""):
        self.whale_alert_key = whale_alert_key

    def get_whale_data(self, symbol: str) -> Dict:
        """Return whale snapshot (simulated; replace with real API calls)"""
        return {
            'symbol':                symbol,
            'netflow_usd_m':         450,   # positive = inflow to exchange (bearish)
            'whale_accumulation':    True,
            'exchange_reserve_chg':  -12000,
            'interpretation':        self.interpret_flows({'net': -450}),
            'large_transactions': [
                {'entity': 'BlackRock',    'action': 'buy',     'amount': 3200,   'value_usd_m': 200,  'time': '2h ago'},
                {'entity': 'Binance',      'action': 'outflow', 'amount': 32000,  'value_usd_m': 1800, 'time': '4h ago'},
                {'entity': 'MicroStrategy','action': 'hold',    'amount': 214400, 'value_usd_m': 12800,'time': 'ongoing'},
            ],
            'exchange_flows': {'inflow': 1200, 'outflow': 1650, 'net': -450},
        }

    async def fetch_exchange_flows(self, symbol: str) -> Optional[Dict]:
        """Use CoinGecko volume data as a free proxy for exchange flows"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    md = data.get('market_data', {})
                    return {
                        'volume_24h':    md.get('total_volume', {}).get('usd', 0),
                        'volume_change': md.get('volume_change_24h', 0),
                    }
        except Exception as e:
            print(f"[WhaleTracker] exchange flows error: {e}")
            return None

    async def fetch_large_transactions(
        self, symbol: str, min_value: float = 1_000_000
    ) -> List[Dict]:
        """Fetch large transactions from Whale Alert free tier"""
        if not self.whale_alert_key:
            return []
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.WHALE_ALERT_BASE}/v1/transactions"
                params = {'currency': symbol.lower(), 'min_value': min_value, 'limit': 10}
                headers = {'X-WA-API-KEY': self.whale_alert_key}
                async with session.get(
                    url, params=params, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    txs = []
                    for tx in data.get('transactions', []):
                        txs.append({
                            'from':       tx.get('from', {}).get('owner', 'Unknown'),
                            'to':         tx.get('to',   {}).get('owner', 'Unknown'),
                            'amount':     tx.get('amount', 0),
                            'value_usd':  tx.get('amount_usd', 0),
                            'timestamp':  tx.get('timestamp', 0),
                        })
                    return txs
        except Exception as e:
            print(f"[WhaleTracker] large tx error: {e}")
            return []

    def interpret_flows(self, flows: Dict) -> str:
        net = flows.get('net', 0)
        if net < -500:
            return "Strong accumulation — whales moving coins off exchanges"
        if net < -100:
            return "Moderate accumulation — net outflow from exchanges"
        if net > 500:
            return "Distribution signal — whales moving to exchanges"
        if net > 100:
            return "Moderate distribution — net inflow to exchanges"
        return "Neutral exchange flows"

    def format_card(self, data: Dict) -> str:
        sym = data.get('symbol', '?')
        lines = [f"🐋 <b>Whale Intelligence: {sym}</b>\n"]
        lines.append(f"📊 Interpretation: {data.get('interpretation', 'N/A')}\n")
        txs = data.get('large_transactions', [])
        if txs:
            lines.append("<b>Recent Large Moves:</b>")
            for tx in txs[:3]:
                lines.append(
                    f"  • {tx['entity']}: {tx['action']} "
                    f"{tx['amount']:,} {sym} "
                    f"(${tx.get('value_usd_m', tx.get('value_usd', 0))}M) "
                    f"— {tx['time']}"
                )
        return "\n".join(lines)
