"""Adaptador read-only entre o catálogo global e o projetor de posições."""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)

_SUPPORTED_KINDS = {kind.value: kind for kind in CorporateActionKind}


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

        raw_payload: dict = {}
        source = "catalog"
        source_event_id = str(event.brapi_event_id or f"corporate-event:{event.id}")
        if event.raw_data:
            try:
                parsed = json.loads(event.raw_data)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                raw_payload = parsed
                source = str(parsed.get("source") or source)
                source_event_id = str(parsed.get("source_event_id") or source_event_id)

        ticker = str(event.ticker).strip().upper()
        actions.setdefault(ticker, []).append(
            NormalizedCorporateAction(
                source=source,
                source_event_id=source_event_id,
                ticker=ticker,
                event_date=event.event_date,
                kind=kind,
                quantity_factor=Decimal(str(event.ratio)),
                raw_payload=raw_payload,
            )
        )

    return {
        ticker: tuple(sorted(rows, key=lambda item: (item.event_date, item.source_event_id)))
        for ticker, rows in actions.items()
    }
