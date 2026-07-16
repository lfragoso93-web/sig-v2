"""Backfill resiliente do histórico diário de preços do Tesouro Direto.

O endpoint de histórico pode devolver listas, mapas indexados por símbolo ou
estruturas aninhadas. Este serviço percorre o payload preservando o contexto do
símbolo e extrai somente pares válidos de data/preço antes de persistir.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.integrations.brapi_treasury import (
    canonical_treasury_symbol_from_text,
    is_brapi_treasury_symbol,
)
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

_HISTORY_URL = "https://brapi.dev/api/v2/treasury/indicators/history"
_SOURCE = "brapi_treasury"
_CHUNK_SIZE = 20
_DEFAULT_YEARS = 10
_LOOKBACK_DAYS = 10

_DATE_FIELDS = (
    "date",
    "baseDate",
    "base_date",
    "timestamp",
    "datetime",
    "referenceDate",
    "reference_date",
    "updatedAt",
    "updated_at",
    "data",
)
_PRICE_FIELDS = (
    "buyPrice",
    "basePrice",
    "sellPrice",
    "price",
    "unitPrice",
    "purchasePrice",
    "redemptionPrice",
    "value",
    "valorUnitario",
    "puCompra",
    "puVenda",
    "puBase",
)
_SYMBOL_FIELDS = ("symbol", "slug", "ticker", "id")
_HISTORY_CONTAINER_FIELDS = (
    "historicalDataPrice",
    "historicalData",
    "history",
    "prices",
    "series",
    "items",
    "results",
    "data",
)


def _headers() -> dict[str, str]:
    token = getattr(settings, "BRAPI_TOKEN", None)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _canonical_symbol(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if is_brapi_treasury_symbol(raw):
        return raw
    candidate = canonical_treasury_symbol_from_text(raw)
    return candidate if candidate and is_brapi_treasury_symbol(candidate) else None


def _parse_date(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric > 10_000_000_000:
            numeric /= 1000
        try:
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _parse_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            raw = value.strip().replace("R$", "").replace(" ", "")
            if not raw:
                return None
            if "," in raw:
                raw = raw.replace(".", "").replace(",", ".")
            numeric = float(raw)
        else:
            numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return numeric if 0 < numeric < 100_000_000 else None


def _row_date(item: dict) -> datetime | None:
    for field in _DATE_FIELDS:
        parsed = _parse_date(item.get(field))
        if parsed is not None:
            return parsed
    return None


def _row_price(item: dict) -> float | None:
    for field in _PRICE_FIELDS:
        parsed = _parse_number(item.get(field))
        if parsed is not None:
            return parsed
    return None


def extract_treasury_history(
    payload: object,
    requested_symbols: Iterable[str],
) -> dict[str, list[tuple[datetime, float]]]:
    """Extrai séries de payloads heterogêneos sem depender de um envelope único."""
    requested = {_canonical_symbol(symbol) for symbol in requested_symbols}
    requested.discard(None)
    output: dict[str, list[tuple[datetime, float]]] = defaultdict(list)

    def visit(node: object, inherited_symbol: str | None = None) -> None:
        if isinstance(node, list):
            for child in node:
                visit(child, inherited_symbol)
            return
        if not isinstance(node, dict):
            return

        current_symbol = inherited_symbol
        for field in _SYMBOL_FIELDS:
            candidate = _canonical_symbol(node.get(field))
            if candidate:
                current_symbol = candidate
                break

        dt = _row_date(node)
        price = _row_price(node)
        target_symbol = current_symbol
        if target_symbol is None and len(requested) == 1:
            target_symbol = next(iter(requested))
        if dt is not None and price is not None and target_symbol in requested:
            output[target_symbol].append((dt, price))

        visited_ids: set[int] = set()
        for key, value in node.items():
            child_symbol = current_symbol
            key_symbol = _canonical_symbol(key)
            if key_symbol:
                child_symbol = key_symbol
            if key in _HISTORY_CONTAINER_FIELDS or isinstance(value, (dict, list)):
                value_id = id(value)
                if value_id in visited_ids:
                    continue
                visited_ids.add(value_id)
                visit(value, child_symbol)

    visit(payload)

    normalized: dict[str, list[tuple[datetime, float]]] = {}
    for symbol in sorted(requested):
        unique = {(ts.astimezone(timezone.utc), float(price)) for ts, price in output.get(symbol, [])}
        normalized[symbol] = sorted(unique, key=lambda item: item[0])
    return normalized


async def _treasury_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(
        select(Asset)
        .where(Asset.asset_type == AssetType.TESOURO_DIRETO.value)
        .order_by(Asset.ticker.asc())
    )
    return list(result.scalars().all())


async def _last_saved_date(db: AsyncSession, asset_id: int) -> date | None:
    result = await db.execute(
        select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
    )
    value = result.scalar_one_or_none()
    return value.date() if value else None


async def _persist_rows(
    db: AsyncSession,
    asset: Asset,
    rows: list[tuple[datetime, float]],
) -> int:
    changed = 0
    for timestamp, close in rows:
        value = Decimal(str(round(close, 8)))
        stmt = (
            pg_insert(AssetPrice)
            .values(asset_id=asset.id, timestamp=timestamp, close=value, source=_SOURCE)
            .on_conflict_do_update(
                constraint="uq_price_asset_timestamp",
                set_={"close": value, "source": _SOURCE},
            )
        )
        await db.execute(stmt)
        changed += 1

    if rows:
        latest_ts, latest_price = max(rows, key=lambda item: item[0])
        asset.last_price = Decimal(str(round(latest_price, 8)))
        asset.last_price_updated_at = latest_ts
    return changed


async def rebuild_treasury_history() -> dict[str, object]:
    """Busca e persiste o histórico reconhecido, reportando payloads sem linhas."""
    async with AsyncSessionLocal() as db:
        assets = await _treasury_assets(db)
        assets_by_symbol: dict[str, Asset] = {}
        windows: dict[tuple[date, date], list[str]] = defaultdict(list)
        skipped = 0
        today = date.today()

        for asset in assets:
            symbol = _canonical_symbol(asset.ticker)
            if not symbol:
                skipped += 1
                continue
            assets_by_symbol[symbol] = asset
            last_date = await _last_saved_date(db, asset.id)
            start = today - timedelta(days=_DEFAULT_YEARS * 365)
            if last_date:
                start = max(last_date - timedelta(days=2), today - timedelta(days=_LOOKBACK_DAYS))
            windows[(start, today)].append(symbol)

        stats: dict[str, int] = {symbol: 0 for symbol in assets_by_symbol}
        empty_payloads = 0
        payload_shapes: set[str] = set()

        async with httpx.AsyncClient(timeout=60.0) as client:
            for (start, end), symbols in windows.items():
                for offset in range(0, len(symbols), _CHUNK_SIZE):
                    chunk = symbols[offset:offset + _CHUNK_SIZE]
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
                    payload_shapes.add(type(payload).__name__)
                    extracted = extract_treasury_history(payload, chunk)
                    if not any(extracted.values()):
                        empty_payloads += 1
                        if empty_payloads <= 2:
                            if isinstance(payload, dict):
                                sample = {key: type(value).__name__ for key, value in list(payload.items())[:12]}
                            else:
                                sample = {"root": type(payload).__name__}
                            logger.warning(
                                "[treasury_history_v2] payload sem linhas chunk=%s shape=%s",
                                chunk[:3],
                                sample,
                            )
                    for symbol, rows in extracted.items():
                        asset = assets_by_symbol.get(symbol)
                        if asset is None or not rows:
                            continue
                        stats[symbol] += await _persist_rows(db, asset, rows)
                    await db.commit()

        imported = sum(stats.values())
        logger.info(
            "[treasury_history_v2] concluido assets=%d imported=%d empty_payloads=%d skipped=%d shapes=%s",
            len(assets_by_symbol), imported, empty_payloads, skipped, sorted(payload_shapes),
        )
        return {
            "assets": len(assets_by_symbol),
            "imported": imported,
            "empty_payloads": empty_payloads,
            "skipped_non_canonical": skipped,
            "payload_shapes": sorted(payload_shapes),
            "history": stats,
        }
