"""BTC dominance, ETH dominance, altcoin season indicator from CoinGecko."""
import aiohttp
from utils.fmt import header, SEP, SEP2, pct, footer, npt_time, score_grade, trend_icon

def _make_session() -> aiohttp.ClientSession:
    resolver = aiohttp.AsyncResolver(nameservers=["8.8.8.8", "8.8.4.4"])
    connector = aiohttp.TCPConnector(resolver=resolver, ssl=False)
    return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=10))


async def fetch_dominance() -> dict:
    try:
        async with _make_session() as session:
            async with session.get("https://api.coingecko.com/api/v3/global") as r:
                data = await r.json()
        d = data["data"]
        mcp = d.get("market_cap_percentage", {})
        btc_d   = mcp.get("btc", 0)
        eth_d   = mcp.get("eth", 0)
        others  = 100 - btc_d - eth_d
        total_mc = d.get("total_market_cap", {}).get("usd", 0)
        total_vol = d.get("total_volume", {}).get("usd", 0)
        btc_mc_chg = d.get("market_cap_change_percentage_24h_usd", 0)
        active_coins = d.get("active_cryptocurrencies", 0)
        return dict(
            btc_d=btc_d, eth_d=eth_d, others=others,
            total_mc=total_mc, total_vol=total_vol,
            btc_mc_chg=btc_mc_chg, active_coins=active_coins,
        )
    except Exception:
        return None


def _altcoin_season(btc_d: float) -> tuple[str, str]:
    """Return (phase_label, description)."""
    if btc_d >= 60:
        return ("🔵 Bitcoin Season", "BTC leads — altcoins underperform · Accumulate alts")
    if btc_d >= 55:
        return ("⚪ BTC Dominant", "BTC still strong but altcoins starting to move")
    if btc_d >= 48:
        return ("🟡 Rotation Zone", "Capital rotating — selective altcoins outperforming")
    if btc_d >= 42:
        return ("🟢 Altcoin Season", "Alts pumping across the board · Aggressive positions")
    return ("🔥 Full Alt Season", "Peak euphoria — extreme greed · Take profits")


def _btc_d_trend(btc_d: float) -> str:
    if btc_d >= 58:  return "BTC very dominant — prefer BTC/ETH over alts"
    if btc_d >= 52:  return "BTC dominant — large-cap alts safe"
    if btc_d >= 46:  return "Transitioning — mid-cap alts gaining"
    return "Low BTC.D — altcoin rally in progress"


def format_dominance(data: dict) -> str:
    if not data:
        return "❌ Could not fetch market data. Try again later."
    btc_d  = data["btc_d"]
    eth_d  = data["eth_d"]
    others = data["others"]
    season_label, season_desc = _altcoin_season(btc_d)
    lines = [
        header("🌐", "Market Dominance"),
        "",
        f"*{season_label}*",
        f"_{season_desc}_",
        "",
        f"*BTC Dominance*",
        f"  `{btc_d:.1f}%` {'▓' * int(btc_d / 5)}",
        f"*ETH Dominance*",
        f"  `{eth_d:.1f}%` {'▓' * int(eth_d / 5)}",
        f"*Altcoins*",
        f"  `{others:.1f}%` {'▓' * int(others / 5)}",
        "",
        f"*Total Market Cap:* `${data['total_mc']/1e9:.0f}B`  {trend_icon(data['btc_mc_chg'])} `{data['btc_mc_chg']:+.1f}%` (24h)",
        f"*24h Volume:* `${data['total_vol']/1e9:.0f}B`",
        f"*Active Coins:* `{data['active_coins']:,}`",
        "",
        f"📌 _{_btc_d_trend(btc_d)}_",
        "",
        footer("Dominance shifts every few weeks — use for positioning bias"),
    ]
    return "\n".join(lines)
