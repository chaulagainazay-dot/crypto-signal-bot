"""CoinGecko + GeckoTerminal free APIs — no key required."""
from __future__ import annotations
import aiohttp
import logging
import re

log = logging.getLogger(__name__)

BASE = "https://api.coingecko.com/api/v3"
GT_BASE = "https://api.geckoterminal.com/api/v2"

# Common symbol → CoinGecko ID map
SYMBOL_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "AVAX": "avalanche-2",
    "DOT": "polkadot", "MATIC": "matic-network", "LINK": "chainlink",
    "UNI": "uniswap", "LTC": "litecoin", "BCH": "bitcoin-cash", "ATOM": "cosmos",
    "FIL": "filecoin", "ICP": "internet-computer", "APT": "aptos", "ARB": "arbitrum",
    "OP": "optimism", "SUI": "sui", "INJ": "injective-protocol", "TIA": "celestia",
    "SEI": "sei-network", "PEPE": "pepe", "WIF": "dogwifcoin", "BONK": "bonk",
    "JUP": "jupiter-exchange-solana", "PYTH": "pyth-network", "W": "wormhole",
    "NEAR": "near", "FTM": "fantom", "ALGO": "algorand", "VET": "vechain",
    "SAND": "the-sandbox", "MANA": "decentraland", "AXS": "axie-infinity",
    "HBAR": "hedera-hashgraph", "XLM": "stellar", "TRX": "tron",
    "CRO": "crypto-com-chain", "SHIB": "shiba-inu", "TON": "the-open-network",
    "NOT": "notcoin", "STRK": "starknet", "MANTA": "manta-network",
    "ZK": "zksync", "BLUR": "blur", "PENDLE": "pendle",
}


def get_coin_id(symbol: str) -> str | None:
    return SYMBOL_MAP.get(symbol.upper())


async def _get(path: str, params: dict = None) -> dict | list:
    url = f"{BASE}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            r.raise_for_status()
            return await r.json()


async def fetch_global_data() -> dict:
    data = await _get("/global")
    d = data["data"]
    return {
        "total_market_cap_usd": d["total_market_cap"].get("usd", 0),
        "total_volume_24h_usd": d["total_volume"].get("usd", 0),
        "btc_dominance": d["market_cap_percentage"].get("btc", 0),
        "eth_dominance": d["market_cap_percentage"].get("eth", 0),
        "market_cap_change_24h": d.get("market_cap_change_percentage_24h_usd", 0),
        "active_coins": d.get("active_cryptocurrencies", 0),
    }


def format_global_data(d: dict) -> str:
    mcap = d["total_market_cap_usd"]
    vol = d["total_volume_24h_usd"]
    change = d["market_cap_change_24h"]
    arrow = "🟢" if change >= 0 else "🔴"
    mcap_str = f"${mcap/1e12:.2f}T" if mcap >= 1e12 else f"${mcap/1e9:.0f}B"
    vol_str = f"${vol/1e9:.1f}B"
    return (
        f"🌍 <b>Global Crypto Market</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Market Cap:</b>  {mcap_str}  {arrow} <code>{change:+.2f}%</code>\n"
        f"📊 <b>24h Volume:</b>  {vol_str}\n"
        f"₿ <b>BTC Dominance:</b> <code>{d['btc_dominance']:.1f}%</code>\n"
        f"Ξ <b>ETH Dominance:</b> <code>{d['eth_dominance']:.1f}%</code>\n"
        f"🪙 <b>Active Coins:</b>  {d['active_coins']:,}\n"
    )


async def fetch_top_movers(limit: int = 10) -> list[dict]:
    data = await _get("/coins/markets", {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "price_change_percentage": "24h",
    })
    return data


async def format_gainers(limit: int = 10) -> str:
    coins = await fetch_top_movers()
    gainers = sorted(coins, key=lambda x: x.get("price_change_percentage_24h") or 0, reverse=True)[:limit]
    text = "🚀 <b>Top Gainers (24h)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for c in gainers:
        pct = c.get("price_change_percentage_24h") or 0
        price = c.get("current_price", 0)
        text += f"🟢 <b>{c['symbol'].upper()}</b>  <code>${_fp(price)}</code>  <code>+{pct:.2f}%</code>\n"
    return text


async def format_losers(limit: int = 10) -> str:
    coins = await fetch_top_movers()
    losers = sorted(coins, key=lambda x: x.get("price_change_percentage_24h") or 0)[:limit]
    text = "📉 <b>Top Losers (24h)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for c in losers:
        pct = c.get("price_change_percentage_24h") or 0
        price = c.get("current_price", 0)
        text += f"🔴 <b>{c['symbol'].upper()}</b>  <code>${_fp(price)}</code>  <code>{pct:.2f}%</code>\n"
    return text


async def fetch_trending() -> list[dict]:
    data = await _get("/search/trending")
    return data.get("coins", [])


async def format_trending() -> str:
    coins = await fetch_trending()
    text = "🔥 <b>Trending on CoinGecko</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for i, item in enumerate(coins[:10], 1):
        c = item["item"]
        text += f"{i}. <b>{c['symbol'].upper()}</b>  {c['name']}  🏆 #{c.get('market_cap_rank','?')}\n"
    return text


async def format_high_volume(limit: int = 10) -> str:
    coins = await fetch_top_movers()
    by_vol = sorted(coins, key=lambda x: x.get("total_volume") or 0, reverse=True)[:limit]
    text = "💰 <b>Highest Volume (24h)</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for c in by_vol:
        vol = c.get("total_volume", 0)
        pct = c.get("price_change_percentage_24h") or 0
        arrow = "🟢" if pct >= 0 else "🔴"
        vol_str = f"${vol/1e9:.1f}B" if vol >= 1e9 else f"${vol/1e6:.0f}M"
        text += f"{arrow} <b>{c['symbol'].upper()}</b>  <code>${_fp(c['current_price'])}</code>  Vol: {vol_str}\n"
    return text


async def fetch_coin_detail(coin_id: str) -> dict:
    return await _get(f"/coins/{coin_id}", {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
    })


def format_coin_detail(d: dict) -> str:
    md = d.get("market_data", {})
    price = md.get("current_price", {}).get("usd", 0)
    change_24h = md.get("price_change_percentage_24h") or 0
    change_7d = md.get("price_change_percentage_7d") or 0
    change_30d = md.get("price_change_percentage_30d") or 0
    mcap = md.get("market_cap", {}).get("usd", 0)
    vol = md.get("total_volume", {}).get("usd", 0)
    ath = md.get("ath", {}).get("usd", 0)
    ath_change = md.get("ath_change_percentage", {}).get("usd", 0)
    supply = md.get("circulating_supply") or 0
    max_supply = md.get("max_supply")
    rank = d.get("market_cap_rank", "?")

    arrow24 = "🟢" if change_24h >= 0 else "🔴"
    mcap_str = f"${mcap/1e9:.2f}B" if mcap >= 1e9 else f"${mcap/1e6:.0f}M"
    vol_str = f"${vol/1e9:.2f}B" if vol >= 1e9 else f"${vol/1e6:.0f}M"

    text = (
        f"🪙 <b>{d['name']} ({d['symbol'].upper()})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Price:</b>  <code>${_fp(price)}</code>  {arrow24} <code>{change_24h:+.2f}%</code>\n"
        f"📊 <b>7d:</b>  <code>{change_7d:+.2f}%</code>   <b>30d:</b>  <code>{change_30d:+.2f}%</code>\n\n"
        f"🏆 <b>Rank:</b>  #{rank}\n"
        f"💎 <b>Market Cap:</b>  {mcap_str}\n"
        f"📈 <b>24h Volume:</b>  {vol_str}\n\n"
        f"🔝 <b>ATH:</b>  <code>${_fp(ath)}</code>  (<code>{ath_change:.1f}% from ATH</code>)\n"
        f"🔄 <b>Circulating:</b>  {supply:,.0f}"
    )
    if max_supply:
        text += f"\n📦 <b>Max Supply:</b>  {max_supply:,.0f}"

    desc = d.get("description", {}).get("en", "")
    if desc:
        # First sentence only
        first = desc.split(".")[0][:200]
        text += f"\n\n📝 {first}."

    return text


async def search_coins(query: str) -> list[dict]:
    data = await _get("/search", {"query": query})
    return data.get("coins", [])[:5]


# All EVM-compatible + major non-EVM platforms CoinGecko supports
_CONTRACT_PLATFORMS = [
    # Tier 1 — highest TVL / most tokens
    "ethereum", "binance-smart-chain", "polygon-pos", "arbitrum-one",
    "base", "optimistic-ethereum", "solana", "tron", "avalanche", "fantom",
    # Tier 2
    "zksync", "linea", "scroll", "blast", "manta-pacific", "mode",
    "mantle", "celo", "gnosis", "moonbeam", "moonriver", "cronos",
    "kava", "harmony-shard-0", "aurora", "boba", "metis-andromeda",
    "okex-chain", "huobi-token", "xdc-network", "thundercore",
    # Tier 3 — newer L2s / alt-L1s
    "sei-network", "injective", "near-protocol", "sui", "aptos",
    "stacks", "hedera-hashgraph", "tomochain", "wanchain",
    "bitgert", "dogechain", "kardiachain", "oasis",
    "zora-network", "cyber", "mint-blockchain",
]


def detect_contract_address(text: str) -> str | None:
    """Return the address if text looks like a contract address, else None."""
    text = text.strip()
    # EVM: 0x + 40 hex chars
    if re.fullmatch(r"0x[0-9a-fA-F]{40}", text):
        return text
    # Solana / Aptos / Sui / Near: base58 or base64-ish, 32–88 chars, no spaces
    if re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,88}", text):
        return text
    return None


def parse_coingecko_url(text: str) -> str | None:
    """Extract coin ID from a CoinGecko URL.
    e.g. https://www.coingecko.com/en/coins/bitcoin  → 'bitcoin'
    """
    m = re.search(r"coingecko\.com(?:/[a-z]{2})?/coins/([a-z0-9\-]+)", text)
    return m.group(1) if m else None


def parse_geckoterminal_url(text: str) -> tuple[str, str, str] | None:
    """Extract (network, kind, address) from a GeckoTerminal URL.
    e.g. https://www.geckoterminal.com/bsc/pools/0xABC…  → ('bsc', 'pools', '0xABC…')
         https://www.geckoterminal.com/eth/tokens/0xDEF… → ('eth', 'tokens', '0xDEF…')
    """
    m = re.search(r"geckoterminal\.com/([^/]+)/(pools|tokens)/([0-9a-zA-Z]+)", text)
    return (m.group(1), m.group(2), m.group(3)) if m else None


async def _gt_get(path: str) -> dict:
    url = f"{GT_BASE}{path}"
    headers = {"Accept": "application/json;version=20230302"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=12)) as r:
            r.raise_for_status()
            return await r.json()


async def fetch_geckoterminal_token(network: str, address: str) -> dict | None:
    """Fetch token info from GeckoTerminal by network + token address."""
    try:
        data = await _gt_get(f"/networks/{network}/tokens/{address.lower()}")
        return data.get("data", {}).get("attributes")
    except Exception as e:
        log.warning("GeckoTerminal token %s/%s: %s", network, address, e)
        return None


async def fetch_geckoterminal_pool(network: str, pool_address: str) -> dict | None:
    """Fetch pool info from GeckoTerminal; extracts base token details."""
    try:
        data = await _gt_get(f"/networks/{network}/pools/{pool_address.lower()}")
        return data.get("data", {}).get("attributes")
    except Exception as e:
        log.warning("GeckoTerminal pool %s/%s: %s", network, pool_address, e)
        return None


def format_geckoterminal_token(attrs: dict, network: str = "") -> str:
    name = attrs.get("name", "Unknown")
    symbol = attrs.get("symbol", "?").upper()
    price = float(attrs.get("price_usd") or 0)
    change_24h = float(attrs.get("price_change_percentage", {}).get("h24") or 0)
    vol_24h = float(attrs.get("volume_usd", {}).get("h24") or 0)
    mcap = float(attrs.get("market_cap_usd") or attrs.get("fdv_usd") or 0)
    address = attrs.get("address", "")

    arrow = "🟢" if change_24h >= 0 else "🔴"
    vol_str = f"${vol_24h/1e6:.2f}M" if vol_24h >= 1e6 else f"${vol_24h:,.0f}"
    mcap_str = f"${mcap/1e6:.2f}M" if mcap >= 1e6 else (f"${mcap:,.0f}" if mcap else "N/A")
    chain_label = f" · <i>{network.upper()}</i>" if network else ""

    return (
        f"🪙 <b>{name} ({symbol})</b>{chain_label}\n━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Price:</b>  <code>${_fp(price)}</code>  {arrow} <code>{change_24h:+.2f}%</code>\n"
        f"📊 <b>24h Volume:</b>  {vol_str}\n"
        f"💎 <b>Market Cap / FDV:</b>  {mcap_str}\n\n"
        f"🔗 <b>Contract:</b>  <code>{address}</code>\n\n"
        f"<i>Data: GeckoTerminal · not on CoinGecko main index</i>"
    )


def format_geckoterminal_pool(attrs: dict, network: str = "") -> str:
    name = attrs.get("name", "Unknown Pool")
    price = float(attrs.get("base_token_price_usd") or 0)
    change_24h = float(attrs.get("price_change_percentage", {}).get("h24") or 0)
    vol_24h = float(attrs.get("volume_usd", {}).get("h24") or 0)
    liq = float(attrs.get("reserve_in_usd") or 0)
    dex = attrs.get("dex_id", "")
    address = attrs.get("address", "")

    arrow = "🟢" if change_24h >= 0 else "🔴"
    vol_str = f"${vol_24h/1e3:.1f}K" if vol_24h < 1e6 else f"${vol_24h/1e6:.2f}M"
    liq_str = f"${liq/1e3:.1f}K" if liq < 1e6 else f"${liq/1e6:.2f}M"
    chain_label = f" · <i>{network.upper()}</i>" if network else ""

    return (
        f"🏊 <b>{name}</b>{chain_label}\n━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>Price:</b>  <code>${_fp(price)}</code>  {arrow} <code>{change_24h:+.2f}%</code>\n"
        f"📊 <b>24h Volume:</b>  {vol_str}\n"
        f"💧 <b>Liquidity:</b>  {liq_str}\n"
        f"🔄 <b>DEX:</b>  {dex}\n\n"
        f"🔗 <b>Pool:</b>  <code>{address}</code>\n\n"
        f"<i>Data: GeckoTerminal</i>"
    )


async def fetch_coin_by_contract(address: str) -> dict | None:
    """Try CoinGecko platforms first, then fall back to GeckoTerminal."""
    import asyncio
    address_lower = address.lower()

    async def _try_cg(platform: str) -> dict | None:
        try:
            data = await _get(f"/coins/{platform}/contract/{address_lower}")
            if data.get("id"):
                return data
        except Exception:
            pass
        return None

    batch_size = 6
    for i in range(0, len(_CONTRACT_PLATFORMS), batch_size):
        batch = _CONTRACT_PLATFORMS[i:i + batch_size]
        results = await asyncio.gather(*[_try_cg(p) for p in batch])
        for r in results:
            if r:
                return r

    # CoinGecko didn't have it — try GeckoTerminal (covers small/new tokens)
    gt_networks = ["bsc", "eth", "polygon_pos", "arbitrum", "base", "solana",
                   "optimism", "avalanche", "fantom", "cronos", "tron"]
    for net in gt_networks:
        attrs = await fetch_geckoterminal_token(net, address_lower)
        if attrs and attrs.get("price_usd"):
            # Wrap in a dict that format_coin_detail won't choke on
            # We flag it as a GeckoTerminal result with a special key
            return {"_geckoterminal": True, "_network": net, "_attrs": attrs}
    return None


async def build_live_market_message(action: str) -> str:
    if action == "live_gainers":
        return await format_gainers()
    elif action == "live_losers":
        return await format_losers()
    elif action == "live_trending":
        return await format_trending()
    elif action == "live_volume":
        return await format_high_volume()
    elif action in ("live_whale_buy", "live_volatile", "live_new"):
        # Fallback: show trending for these
        return await format_trending()
    elif action in ("market_btc", "market_eth", "market_alts", "market_trend", "market_volume", "market_liq"):
        cg_map = {
            "market_btc": "bitcoin", "market_eth": "ethereum", "market_alts": "solana",
            "market_trend": "binancecoin", "market_volume": "ripple", "market_liq": "bitcoin",
        }
        coin_id = cg_map.get(action, "bitcoin")
        d = await fetch_coin_detail(coin_id)
        return format_coin_detail(d)
    return "⚠️ Unknown action."


def _fp(price: float) -> str:
    if price == 0:
        return "0"
    if price >= 1000:
        return f"{price:,.2f}"
    if price >= 1:
        return f"{price:.4f}"
    if price >= 0.01:
        return f"{price:.6f}"
    return f"{price:.8f}"
