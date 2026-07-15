"""Histórico do Tesouro limitado aos símbolos oficiais retornados pela BRAPI.

Evita consultar aliases e títulos sintéticos que não existem no endpoint de
histórico. O serviço também registra apenas a estrutura do primeiro item do
payload quando nenhuma linha é reconhecida.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.integrations.brapi_treasury import is_brapi_treasury_symbol
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.asset_last_price_refresh_service import refresh_asset_last_prices
from app.services.treasury_history_rebuild_service import (
    _last_saved_date,
    extract_treasury_history,
)

logger = logging.getLogger(__name__)

_LIST_URL = "https://brapi.dev/api/v2/treasury/list"
_HISTORY_URL = "https://brapi.dev/api/v2/treasury/indicators/history"
_SOURCE = "brapi_treasury"
_CHUNK_SIZE = 20
_DEFAULT_YEARS = 10
_LOOKBACK_DAYS = 10


def _headers() -> dict[str, str]:
    token = getattr(settings, "BRAPI_TOKEN", None)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _payload_items(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("results", "data", "items", "treasury", "treasuries", "bonds"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _symbol_from_item(item: dict) -> str | None:
    raw = str(item.get("symbol") or item.get("slug") or item.get("ticker") or "").strip().lower()
    return raw if is_brapi_treasury_symbol(raw) else None


def _payload_diagnostics(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {"root_type": type(payload).__name__}
    results = payload.get("results")
    diagnostics: dict[str, object] = {
        "root_keys": sorted(str(key) for key in payload.keys())[:20],
        "results_type": type(results).__name__,
    }
    if isinstance(results, list):
        diagnostics["results_count"] = len(results)
        if results and isinstance(results[0], dict):
            diagnostics["first_item_keys"] = sorted(str(key) for key in results[0].keys())[:30]
            for key, value in results[0].items():
                if isinstance(value, list):
                    diagnostics[f"first_item_{key}_count"] = len(value)
                    if value and isinstance(value[0], dict):
                        diagnostics[f"first_item_{key}_keys"] = sorted(
                            str(child_key) for child_key in value[0].keys()
                        )[:30]
    return diagnostics


async def _official_symbols(client: httpx.AsyncClient) -> list[str]:
    response = await client.get(_LIST_URL, headers=_headers())
    response.raise_for_status()
    symbols = {
        symbol
        for item in _payload_items(response.json())
        if (symbol := _symbol_from_item(item)) is not None
    }
    return sorted(symbols)


async def _persist_history_rows(
    db,
    asset_id: int,
    rows: list[tuple[datetime, float]],
) -> int:
    """Persiste apenas ``asset_prices`` sem alterar a linha de ``assets``."""
    changed = 0
    for timestamp, close in rows:
        value = Decimal(str(round(close, 8)))
        stmt = (
            pg_insert(AssetPrice)
            .values(
                asset_id=asset_id,
                timestamp=timestamp,
                close=value,
                source=_SOURCE,
            )
            .on_conflict_do_update(
                constraint="uq_price_asset_timestamp",
                set_={"close": value, "source": _SOURCE},
            )
        )
        await db.execute(stmt)
        changed += 1
    return changed


async def rebuild_official_treasury_history() -> dict[str, object]:
    today = date.today()
    async with httpx.AsyncClient(timeout=60.0) as client:
        official_symbols = await _official_symbols(client)
        if not official_symbols:
            logger.warning("[treasury_history_official] catálogo oficial sem símbolos")
            return {
                "official_symbols": 0,
                "matched_assets": 0,
                "imported": 0,
                "empty_payloads": 0,
                "last_prices_refreshed": 0,
                "history": {},
            }

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Asset).where(
                    Asset.asset_type == AssetType.TESOURO_DIRETO.value,
                    Asset.ticker.in_(official_symbols),
                )
            )
            assets = list(result.scalars().all())
            assets_by_symbol = {str(asset.ticker).lower(): asset for asset in assets}
            windows: dict[tuple[date, date], list[str]] = defaultdict(list)
            for symbol, asset in assets_by_symbol.items():
                last_date = await _last_saved_date(db, asset.id)
                start = today - timedelta(days=_DEFAULT_YEARS * 365)
                if last_date:
                    start = max(last_date - timedelta(days=2), today - timedelta(days=_LOOKBACK_DAYS))
                windows[(start, today)].append(symbol)

            stats = {symbol: 0 for symbol in assets_by_symbol}
            empty_payloads = 0
            diagnostics: list[dict[str, object]] = []
            touched_asset_ids: set[int] = set()

            for (start, end), symbols in windows.items():
                unique_symbols = sorted(set(symbols))
                for offset in range(0, len(unique_symbols), _CHUNK_SIZE):
                    chunk = unique_symbols[offset:offset + _CHUNK_SIZE]
                    response = await client.get(
                        _HISTORY_URL,
                        headers=_headers(),
                        params={
                            "symbols": ",".join(chunk),
                            "startDate": start.isoformat(),
                            "endDate": end.isoformat(),
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    extracted = extract_treasury_history(payload, chunk)
                    if not any(extracted.values()):
                        empty_payloads += 1
                        detail = _payload_diagnostics(payload)
                        diagnostics.append(detail)
                        if empty_payloads <= 2:
                            logger.warning(
                                "[treasury_history_official] payload sem linhas chunk=%s diagnostics=%s",
                                chunk[:3],
                                detail,
                            )
                    for symbol, rows in extracted.items():
                        asset = assets_by_symbol.get(symbol)
                        if asset is None or not rows:
                            continue
                        stats[symbol] += await _persist_history_rows(db, int(asset.id), rows)
                        touched_asset_ids.add(int(asset.id))
                    await db.commit()

            last_prices_refreshed = 0
            if touched_asset_ids:
                last_prices_refreshed = await refresh_asset_last_prices(db, touched_asset_ids)
                await db.commit()

    imported = sum(stats.values())
    logger.info(
        "[treasury_history_official] concluido official=%d matched=%d imported=%d empty=%d refreshed=%d",
        len(official_symbols),
        len(assets_by_symbol),
        imported,
        empty_payloads,
        last_prices_refreshed,
    )
    return {
        "official_symbols": len(official_symbols),
        "matched_assets": len(assets_by_symbol),
        "imported": imported,
        "empty_payloads": empty_payloads,
        "last_prices_refreshed": last_prices_refreshed,
        "diagnostics": diagnostics[:2],
        "history": stats,
    }
