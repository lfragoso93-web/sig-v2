from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

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
            logger.error("[market_data] /v2/crypto/available page=%d: %s", page, exc)
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

        all_coins.extend(items)
        logger.info(
            "[market_data] crypto catalog page=%d: %d moedas válidas (%d acumuladas)",
            page,
            len(items),
            len(all_coins),
        )

        if raw_count < limit:
            break
        page += 1

    return all_coins
