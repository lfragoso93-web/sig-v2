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
_MATCHED_RECONCILIATION_STATUS = "MATCHED"
_IGNORED_EVENT_STATUS = "IGNORADO"
_LEGACY_SOURCE_PROVIDER = "legacy"


def _normalized_text(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    return str(raw or "").strip()


def _is_projection_eligible(event: CorporateEvent) -> bool:
    """Autoriza somente evidências reconciliadas ou compatibilidade histórica.

    Registros produzidos pelo catálogo novo precisam ser a representação canônica
    de um grupo reconciliado e não podem exigir revisão. Linhas históricas globais
    com provedor ``legacy`` permanecem projetáveis durante a contração incremental,
    exceto quando foram explicitamente ignoradas.
    """

    if _normalized_text(event.status).upper() == _IGNORED_EVENT_STATUS:
        return False

    source_provider = _normalized_text(event.source_provider).lower()
    if source_provider in {"", _LEGACY_SOURCE_PROVIDER}:
        return True

    return (
        event.is_canonical is True
        and _normalized_text(event.reconciliation_status).upper()
        == _MATCHED_RECONCILIATION_STATUS
        and event.requires_review is False
    )


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
    """Carrega eventos globais elegíveis para o motor puro.

    Linhas vinculadas a carteira, conflitos, evidências não canônicas e eventos
    pendentes de revisão ficam fora da projeção. A única exceção é a compatibilidade
    explícita para registros históricos globais marcados como ``legacy``.
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
        if not _is_projection_eligible(event):
            continue

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
