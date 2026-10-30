from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

BRAPI_BASE = "https://brapi.dev/api"


def _auth_headers() -> dict[str, str]:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


def _extract_items(data: Any) -> list[dict]:
    if isinstance(data, dict):
        raw_items = data.get("coins") or data.get("available") or []
    elif isinstance(data, list):
        raw_items = data
    else:
        raw_items = []

    if not isinstance(raw_items, list):
        return []

    normalized: list[dict] = []
    for item in raw_items:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        if isinstance(item, str):
            coin = item.strip().upper()
            if coin:
                normalized.append({"coin": coin})
    return normalized


async def fetch_crypto_catalog_all(limit: int = 500) -> list[dict]:
    """Busca e normaliza o catálogo BRAPI de cripto para registros estruturados."""
    headers = _auth_headers()
    all_coins: list[dict] = []
    seen_coins: set[str] = set()
    page = 1

    while True:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/crypto/available",
                    headers=headers,
                    params={"limit": limit, "page": page},
                )
                resp.raise_for_status()
                raw_data = resp.json()
        except Exception as exc:
            logger.error("[market_data] /v2/crypto/available page=%d: %s", page, sanitize_log_value(exc))
            break

        raw_count = 0
        if isinstance(raw_data, dict):
            raw_items = raw_data.get("coins") or raw_data.get("available") or []
            if isinstance(raw_items, list):
                raw_count = len(raw_items)
        elif isinstance(raw_data, list):
            raw_count = len(raw_data)

        items = _extract_items(raw_data)
        dropped = raw_count - len(items)
        if dropped:
            logger.warning(
                "[market_data] crypto catalog page=%d: %d item(ns) inválido(s) ignorado(s)",
                page,
                dropped,
            )

        if not items:
            break

        new_items: list[dict] = []
        for item in items:
            coin = str(item.get("coin") or item.get("symbol") or "").strip().upper()
            if coin and coin not in seen_coins:
                seen_coins.add(coin)
                new_items.append(item)

        if not new_items:
            # Nenhuma moeda nova nesta página — fim da paginação ou endpoint estático
            break

        all_coins.extend(new_items)
        logger.info(
            "[market_data] crypto catalog page=%d: %d moedas válidas (%d acumuladas)",
            page,
            len(new_items),
            len(all_coins),
        )

        if raw_count < limit:
            break
        page += 1

    return all_coins


async def fetch_crypto_quote_and_metrics(coin: str) -> Optional[dict[str, Any]]:
    """Consulta cotação, variação, volume e indicadores de criptoativo via BRAPI /v2/crypto.

    Complementa opcionalmente com o ranking global de market cap via CoinGecko.
    """
    clean_coin = (coin or "").strip().upper()
    for sep in ("-", "/"):
        if sep in clean_coin:
            clean_coin = clean_coin.split(sep, 1)[0]
    for suffix in ("USDT", "USDC", "BRL", "USD"):
        if clean_coin.endswith(suffix) and len(clean_coin) > len(suffix):
            clean_coin = clean_coin[: -len(suffix)]
            break

    if not clean_coin:
        return None

    headers = _auth_headers()
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/crypto",
                headers=headers,
                params={"coin": clean_coin, "currency": "BRL"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
    except Exception as exc:
        logger.warning(
            "[crypto] Falha ao consultar /v2/crypto para %s: %s",
            sanitize_log_value(clean_coin),
            sanitize_log_value(exc),
        )
        return None

    if not isinstance(data, dict):
        return None

    coins = data.get("coins")
    if not isinstance(coins, list) or not coins:
        return None

    raw_item = coins[0]
    if not isinstance(raw_item, dict):
        return None

    def _flt(val: Any) -> Optional[float]:
        return float(val) if isinstance(val, (int, float)) else None

    price_brl = _flt(raw_item.get("regularMarketPrice"))
    rate_usd = _flt(raw_item.get("currencyRateFromUSD"))
    price_usd = None
    if price_brl is not None and rate_usd is not None and rate_usd > 0:
        price_usd = round(price_brl / rate_usd, 4)

    # Consulta ranking CoinGecko
    market_cap_rank: Optional[int] = None
    try:
        from app.integrations.coingecko_crypto_market_cap import fetch_top_crypto_by_market_cap
        top_coins = await fetch_top_crypto_by_market_cap(limit=50)
        for item in top_coins:
            if str(item.get("symbol", "")).upper() == clean_coin:
                raw_rank = item.get("market_cap_rank")
                if isinstance(raw_rank, int):
                    market_cap_rank = raw_rank
                break
    except Exception as exc:
        logger.debug("[crypto] CoinGecko rank ranking indisponível para %s: %s", sanitize_log_value(clean_coin), sanitize_log_value(exc))

    return {
        "coin": clean_coin,
        "coin_name": str(raw_item.get("coinName") or clean_coin),
        "logo_url": raw_item.get("coinImageUrl"),
        "price_brl": price_brl,
        "price_usd": price_usd,
        "change_24h_pct": _flt(raw_item.get("regularMarketChangePercent")),
        "volume_24h": _flt(raw_item.get("regularMarketVolume")),
        "market_cap_brl": _flt(raw_item.get("marketCap")),
        "market_cap_rank": market_cap_rank,
        "day_low": _flt(raw_item.get("regularMarketDayLow")),
        "day_high": _flt(raw_item.get("regularMarketDayHigh")),
        "currency_rate_usd": rate_usd,
    }
