from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.integrations.brapi_crypto_catalog import fetch_crypto_catalog_all
from app.integrations.coingecko_crypto_market_cap import (
    TOP_CRYPTO_LIMIT,
    fetch_top_crypto_by_market_cap,
)


@dataclass(frozen=True)
class SupportedCrypto:
    ticker: str
    name: str
    market_cap_rank: int
    market_cap: int | float | None
    ranking_source_id: str | None


def _brapi_symbols(items: list[dict]) -> set[str]:
    symbols: set[str] = set()
    for item in items:
        symbol = str(item.get("coin") or item.get("symbol") or "").strip().upper()
        if symbol:
            symbols.add(symbol)
    return symbols


async def fetch_supported_crypto_universe(limit: int = TOP_CRYPTO_LIMIT) -> list[SupportedCrypto]:
    """Interseção determinística: Top market cap ∩ catálogo CRIPTO disponível na BRAPI."""
    ranking, brapi_catalog = await asyncio.gather(
        fetch_top_crypto_by_market_cap(limit=limit),
        fetch_crypto_catalog_all(),
    )
    available = _brapi_symbols(brapi_catalog)

    supported: list[SupportedCrypto] = []
    seen: set[str] = set()
    for item in ranking:
        ticker = str(item["symbol"]).upper()
        if ticker not in available or ticker in seen:
            continue
        seen.add(ticker)
        supported.append(
            SupportedCrypto(
                ticker=ticker,
                name=str(item.get("name") or ticker),
                market_cap_rank=int(item["market_cap_rank"]),
                market_cap=item.get("market_cap"),
                ranking_source_id=item.get("source_id"),
            )
        )
    return supported


async def fetch_supported_crypto_tickers(limit: int = TOP_CRYPTO_LIMIT) -> set[str]:
    return {item.ticker for item in await fetch_supported_crypto_universe(limit=limit)}
