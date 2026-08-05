"""Adaptador read-only entre o catálogo global e o projetor de posições."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)

_SUPPORTED_KINDS = {kind.value: kind for kind in CorporateActionKind}


def _effective_date(event: CorporateEvent) -> date:
    """Resolve a data canônica com fallback temporário para a coluna legada."""

    value = event.effective_date or event.event_date
    if value is None:
        raise ValueError(f"evento corporativo {event.id!r} sem data efetiva")
    return value


def _quantity_factor(event: CorporateEvent) -> Decimal:
    """Resolve o fator canônico com fallback temporário para ``ratio``."""

    value = event.quantity_factor
    if value is None:
        value = event.ratio
    if value is None:
        raise ValueError(f"evento corporativo {event.id!r} sem fator de quantidade")
    return Decimal(str(value))


def _source_identity(event: CorporateEvent) -> tuple[str, str]:
    """Prioriza a identidade neutra e reconhece registros históricos."""

    source = str(event.source_provider or "catalog")
    source_event_id = str(
        event.source_event_id
        or event.brapi_event_id
        or f"corporate-event:{event.id}"
    )
    return source, source_event_id


def _raw_payload(event: CorporateEvent) -> dict[str, Any]:
    """Prioriza metadados canônicos e lê o envelope legado somente como fallback."""

    if isinstance(event.raw_metadata, dict):
        return dict(event.raw_metadata)
    if not event.raw_data:
        return {}
    try:
        parsed = json.loads(event.raw_data)
    except (TypeError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    provider_payload = parsed.get("provider_payload")
    if isinstance(provider_payload, dict):
        return dict(provider_payload)
    return parsed


async def load_global_corporate_actions_by_ticker(
    db: AsyncSession,
    tickers: list[str],
) -> dict[str, tuple[NormalizedCorporateAction, ...]]:
    """Carrega apenas eventos globais compatíveis com o motor puro.

    Linhas antigas vinculadas a carteira são ignoradas até a contração física do
    modelo legado. Eventos desconhecidos também ficam fora da projeção em vez de
    serem inferidos silenciosamente.
    """

    normalized_tickers = sorted({ticker.strip().upper() for ticker in tickers if ticker})
    if not normalized_tickers:
        return {}

    result = await db.execute(
        select(CorporateEvent).where(
            CorporateEvent.ticker.in_(normalized_tickers),
            CorporateEvent.portfolio_id.is_(None),
        )
    )

    actions: dict[str, list[NormalizedCorporateAction]] = {}
    for event in result.scalars().all():
        kind = _SUPPORTED_KINDS.get(str(event.event_type).upper())
        if kind is None:
            continue

        source, source_event_id = _source_identity(event)
        ticker = str(event.ticker).strip().upper()
        actions.setdefault(ticker, []).append(
            NormalizedCorporateAction(
                source=source,
                source_event_id=source_event_id,
                ticker=ticker,
                event_date=_effective_date(event),
                kind=kind,
                quantity_factor=_quantity_factor(event),
                raw_payload=_raw_payload(event),
            )
        )

    return {
        ticker: tuple(sorted(rows, key=lambda item: (item.event_date, item.source_event_id)))
        for ticker, rows in actions.items()
    }
