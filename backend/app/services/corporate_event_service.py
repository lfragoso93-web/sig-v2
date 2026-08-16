"""Coleta e persistência do catálogo global de eventos corporativos."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import warnings
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

import httpx
from pandas.errors import Pandas4Warning
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi import BRAPI_BASE, _auth_headers
from app.models.asset import Asset
from app.models.corporate_event import (
    CorporateEvent,
    CorporateEventStatus,
)
from app.services.corporate_action_engine import (
    NormalizedCorporateAction,
    normalize_brapi_corporate_actions,
    normalize_yahoo_splits,
)
from app.services.dividend_history_seed_service import _yf_symbol

logger = logging.getLogger(__name__)

BrapiPayloadFetcher = Callable[[str], Awaitable[dict[str, Any]]]
YahooSplitsFetcher = Callable[[str], Awaitable[list[tuple[date, float]]]]
_SUPPORTED_ASSET_TYPES = {"ACAO", "BDR", "ETF_NACIONAL"}


class CorporateActionCollectionError(RuntimeError):
    """Falha bloqueante na coleta do catálogo corporativo."""


async def fetch_brapi_corporate_actions_payload(ticker: str) -> dict[str, Any]:
    """Consulta a rota Pro tipada de dividendos e eventos de ações."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BRAPI_BASE}/v2/stocks/dividends",
                headers=_auth_headers(),
                params={"symbols": ticker.upper()},
            )
    except httpx.HTTPError as exc:
        raise CorporateActionCollectionError(
            f"{ticker}/brapi: falha de transporte"
        ) from exc

    if response.status_code in {400, 404}:
        return {"results": []}
    if response.status_code in {401, 403}:
        raise CorporateActionCollectionError(
            f"{ticker}/brapi: autorização recusada ({response.status_code})"
        )
    try:
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CorporateActionCollectionError(
            f"{ticker}/brapi: resposta inválida"
        ) from exc
    if not isinstance(payload, dict):
        raise CorporateActionCollectionError(f"{ticker}/brapi: payload inválido")
    return payload


async def fetch_yahoo_splits(symbol: str) -> list[tuple[date, float]]:
    """Consulta somente os fatores de split/grupamento publicados pelo Yahoo."""

    def _sync() -> list[tuple[date, float]]:
        import yfinance as yf

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*Timestamp\.utcnow is deprecated.*",
                category=Pandas4Warning,
            )
            actions = yf.Ticker(symbol).actions.copy(deep=True)
        if actions.empty or "Stock Splits" not in actions.columns:
            return []

        rows: list[tuple[date, float]] = []
        for timestamp, value in actions["Stock Splits"].items():
            factor = float(value or 0)
            if factor <= 0:
                continue
            event_date = (
                timestamp.date()
                if hasattr(timestamp, "date")
                else date.fromisoformat(str(timestamp)[:10])
            )
            rows.append((event_date, factor))
        return rows

    try:
        return await asyncio.to_thread(_sync)
    except Exception as exc:
        raise CorporateActionCollectionError(
            f"{symbol}/yahoo: provedor indisponível"
        ) from exc


def _source_payload_hash(action: NormalizedCorporateAction) -> str:
    payload = json.dumps(
        action.raw_payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def sync_corporate_events_for_asset(
    db: AsyncSession,
    asset: Asset,
    *,
    brapi_fetcher: BrapiPayloadFetcher | None = None,
    yahoo_fetcher: YahooSplitsFetcher | None = None,
) -> list[CorporateEvent]:
    """Coleta fontes explícitas e persiste somente eventos globais idempotentes."""

    raw_asset_type = asset.asset_type
    asset_type = str(getattr(raw_asset_type, "value", raw_asset_type)).upper()
    if asset_type not in _SUPPORTED_ASSET_TYPES:
        return []

    ticker = str(asset.brapi_ticker or asset.ticker).strip().upper()
    if not ticker:
        raise CorporateActionCollectionError("ativo sem ticker corporativo")

    brapi_fetcher = brapi_fetcher or fetch_brapi_corporate_actions_payload
    yahoo_fetcher = yahoo_fetcher or fetch_yahoo_splits
    brapi_payload = await brapi_fetcher(ticker)
    yahoo_rows = await yahoo_fetcher(_yf_symbol(ticker, asset_type))
    actions = (
        *normalize_brapi_corporate_actions(ticker, brapi_payload),
        *normalize_yahoo_splits(ticker, yahoo_rows),
    )
    if not actions:
        return []

    identities = [(action.source, action.source_event_id) for action in actions]
    existing_result = await db.execute(
        select(
            CorporateEvent.source_provider,
            CorporateEvent.source_event_id,
        ).where(
            tuple_(
                CorporateEvent.source_provider,
                CorporateEvent.source_event_id,
            ).in_(identities)
        )
    )
    existing_identities = {
        (source_provider, source_event_id)
        for source_provider, source_event_id in existing_result.all()
        if source_provider and source_event_id
    }

    created: list[CorporateEvent] = []
    for action in sorted(actions, key=lambda item: (item.event_date, item.source_event_id)):
        identity = (action.source, action.source_event_id)
        if identity in existing_identities:
            continue
        event = CorporateEvent(
            asset_id=asset.id,
            ticker=ticker,
            event_type=action.kind.value,
            status=CorporateEventStatus.PENDENTE.value,
            effective_date=action.event_date,
            quantity_factor=action.quantity_factor,
            source_provider=action.source,
            source_event_id=action.source_event_id,
            source_payload_hash=_source_payload_hash(action),
            raw_metadata=action.raw_payload,
            description=(
                f"{action.kind.value} global coletado de {action.source} "
                f"(fator {action.quantity_factor})"
            ),
            # Espelhos obrigatórios de schema legado; sem uso funcional.
            event_date=action.event_date,
            ratio=action.quantity_factor,
        )
        db.add(event)
        created.append(event)
        existing_identities.add(identity)

    if created:
        await db.flush()
    return created
