"""
Integração BRAPI — Tesouro Direto.

Fluxo oficial:
- GET /api/v2/treasury/list
- GET /api/v2/treasury/indicators
- GET /api/v2/treasury/indicators/history

Os títulos usam `symbol` em formato slug minúsculo, ex.:
`tesouro-selic-01032031`.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Iterable, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_TREASURY_BASE = "https://brapi.dev/api/v2/treasury"
BRAPI_TREASURY_CHUNK = 20


def _auth_headers() -> dict:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


def _items_from_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    for key in (
        "results",
        "treasury",
        "treasuries",
        "bonds",
        "items",
        "data",
        "list",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    # Alguns endpoints retornam um objeto por símbolo.
    maybe_values = [v for v in payload.values() if isinstance(v, dict)]
    if maybe_values:
        return maybe_values
    return []


def _symbol_from_item(item: dict) -> str:
    return str(
        item.get("symbol")
        or item.get("slug")
        or item.get("ticker")
        or item.get("id")
        or ""
    ).strip().lower()


def _price_from_item(item: dict) -> Optional[float]:
    for field in (
        "buyPrice",
        "basePrice",
        "sellPrice",
        "price",
        "unitPrice",
        "valorUnitario",
    ):
        value = item.get(field)
        if value is None:
            continue
        try:
            parsed = float(value)
            if parsed > 0:
                return parsed
        except (TypeError, ValueError):
            continue
    return None


def _history_date(value: object) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    raw = str(value)[:10]
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def fetch_treasury_list(
    indexer: Optional[str] = None,
    coupon_type: Optional[str] = None,
) -> list[dict]:
    """Lista títulos disponíveis do Tesouro Direto na BRAPI."""
    params: dict[str, str] = {}
    if indexer:
        params["indexer"] = indexer.lower()
    if coupon_type:
        params["couponType"] = coupon_type.lower()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BRAPI_TREASURY_BASE}/list",
            headers=_auth_headers(),
            params=params,
        )
        response.raise_for_status()
        payload = response.json()

    items = _items_from_payload(payload)
    logger.info("[treasury] BRAPI list retornou %d títulos", len(items))
    return items


async def fetch_treasury_indicators(symbols: Iterable[str]) -> dict[str, dict]:
    """Consulta indicadores atuais por symbol canônico da BRAPI."""
    selected = [s.strip().lower() for s in symbols if s and s.strip()]
    if not selected:
        return {}

    result: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(selected), BRAPI_TREASURY_CHUNK):
            chunk = selected[i:i + BRAPI_TREASURY_CHUNK]
            try:
                response = await client.get(
                    f"{BRAPI_TREASURY_BASE}/indicators",
                    headers=_auth_headers(),
                    params={"symbols": ",".join(chunk)},
                )
                response.raise_for_status()
                items = _items_from_payload(response.json())
                for item in items:
                    symbol = _symbol_from_item(item)
                    if symbol:
                        result[symbol] = item
            except Exception as exc:
                logger.warning("[treasury] indicators falhou para %s: %s", chunk, exc)

    return result


async def fetch_treasury_prices(symbols: Iterable[str]) -> dict[str, float]:
    """Retorna preço unitário atual por symbol canônico."""
    indicators = await fetch_treasury_indicators(symbols)
    prices: dict[str, float] = {}
    for symbol, item in indicators.items():
        price = _price_from_item(item)
        if price is not None:
            prices[symbol] = price
    return prices


async def fetch_treasury_history(
    symbols: Iterable[str],
    start_date: date,
    end_date: date,
) -> dict[str, list[tuple[datetime, float]]]:
    """Busca histórico diário de preços unitários para títulos do Tesouro."""
    selected = [s.strip().lower() for s in symbols if s and s.strip()]
    if not selected:
        return {}

    output: dict[str, list[tuple[datetime, float]]] = {s: [] for s in selected}
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(selected), BRAPI_TREASURY_CHUNK):
            chunk = selected[i:i + BRAPI_TREASURY_CHUNK]
            try:
                response = await client.get(
                    f"{BRAPI_TREASURY_BASE}/indicators/history",
                    headers=_auth_headers(),
                    params={
                        "symbols": ",".join(chunk),
                        "startDate": start_date.isoformat(),
                        "endDate": end_date.isoformat(),
                    },
                )
                response.raise_for_status()
                items = _items_from_payload(response.json())
            except Exception as exc:
                logger.warning("[treasury] history falhou para %s: %s", chunk, exc)
                continue

            for item in items:
                symbol = _symbol_from_item(item)
                if not symbol:
                    continue
                raw_history = (
                    item.get("historicalDataPrice")
                    or item.get("history")
                    or item.get("data")
                    or item.get("prices")
                    or []
                )
                rows: list[tuple[datetime, float]] = []
                if isinstance(raw_history, list):
                    for row in raw_history:
                        if not isinstance(row, dict):
                            continue
                        dt = _history_date(row.get("date") or row.get("timestamp"))
                        price = _price_from_item(row)
                        if dt and price is not None:
                            rows.append((dt, price))
                rows.sort(key=lambda x: x[0])
                output[symbol] = rows

    return output
