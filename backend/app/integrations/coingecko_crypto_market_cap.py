from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
TOP_CRYPTO_LIMIT = 100


def _normalize_market_item(item: Any) -> dict | None:
    if not isinstance(item, dict):
        return None

    symbol = str(item.get("symbol") or "").strip().upper()
    rank = item.get("market_cap_rank")
    market_cap = item.get("market_cap")
    if not symbol or not isinstance(rank, int) or rank <= 0:
        return None

    return {
        "symbol": symbol,
        "name": str(item.get("name") or symbol).strip() or symbol,
        "market_cap_rank": rank,
        "market_cap": market_cap,
        "source_id": str(item.get("id") or "").strip() or None,
    }


async def fetch_top_crypto_by_market_cap(limit: int = TOP_CRYPTO_LIMIT) -> list[dict]:
    """Retorna ranking CoinGecko por market cap, limitado ao universo suportado."""
    requested = max(1, min(int(limit), TOP_CRYPTO_LIMIT))
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": requested,
        "page": 1,
        "sparkline": "false",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(COINGECKO_MARKETS_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    if not isinstance(payload, list):
        raise TypeError("CoinGecko retornou payload inválido para ranking CRIPTO")

    normalized = [item for raw in payload if (item := _normalize_market_item(raw)) is not None]
    normalized.sort(key=lambda item: (int(item["market_cap_rank"]), str(item["symbol"])))
    return normalized[:requested]
