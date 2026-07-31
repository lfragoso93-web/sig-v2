"""Seleção estrita de eventos autorizados para projeções de posição."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import (
    CorporateEvent,
    CorporateEventReconciliationStatus,
    CorporateEventStatus,
    CorporateEventType,
)

_AUTO_QUANTITY_TYPES = (
    CorporateEventType.DESDOBRAMENTO.value,
    CorporateEventType.GRUPAMENTO.value,
    CorporateEventType.BONIFICACAO.value,
)


@dataclass(frozen=True, slots=True)
class EligibleQuantityAction:
    event_id: int
    ticker: str
    effective_date: date
    event_type: str
    quantity_factor: Decimal


async def load_eligible_quantity_actions(
    db: AsyncSession,
    *,
    tickers: Sequence[str],
    through_date: date,
) -> dict[str, tuple[EligibleQuantityAction, ...]]:
    """Carrega somente eventos globais canônicos, reconciliados e validados."""
    normalized = sorted(
        {ticker.strip().upper() for ticker in tickers if ticker.strip()}
    )
    if not normalized:
        return {}

    result = await db.execute(
        select(CorporateEvent)
        .where(
            CorporateEvent.ticker.in_(normalized),
            CorporateEvent.portfolio_id.is_(None),
            CorporateEvent.is_canonical.is_(True),
            or_(
                CorporateEvent.reconciliation_status
                == CorporateEventReconciliationStatus.MATCHED.value,
                (
                    CorporateEvent.reconciliation_status
                    == CorporateEventReconciliationStatus.MANUALLY_VALIDATED.value
                )
                & CorporateEvent.reviewed_by_user_id.is_not(None),
            ),
            CorporateEvent.status == CorporateEventStatus.VALIDATED.value,
            CorporateEvent.requires_review.is_(False),
            CorporateEvent.event_type.in_(_AUTO_QUANTITY_TYPES),
            CorporateEvent.effective_date <= through_date,
        )
        .order_by(
            CorporateEvent.ticker,
            CorporateEvent.effective_date,
            CorporateEvent.id,
        )
    )
    grouped: dict[str, list[EligibleQuantityAction]] = defaultdict(list)
    for event in result.scalars().all():
        factor = Decimal(str(event.quantity_factor))
        if not factor.is_finite() or factor <= 0:
            raise ValueError(f"evento corporativo {event.id} possui fator inválido")
        grouped[str(event.ticker).upper()].append(
            EligibleQuantityAction(
                event_id=int(event.id),
                ticker=str(event.ticker).upper(),
                effective_date=event.effective_date,
                event_type=str(getattr(event.event_type, "value", event.event_type)),
                quantity_factor=factor,
            )
        )
    return {ticker: tuple(actions) for ticker, actions in grouped.items()}


def consume_quantity_actions(
    actions: Sequence[EligibleQuantityAction],
    *,
    cursor: int,
    through_date: date,
    quantity: Decimal,
) -> tuple[Decimal, int, tuple[int, ...]]:
    """Aplica ações ainda não consumidas até a data, preservando custo total."""
    applied: list[int] = []
    while cursor < len(actions) and actions[cursor].effective_date <= through_date:
        action = actions[cursor]
        quantity *= action.quantity_factor
        applied.append(action.event_id)
        cursor += 1
    return quantity, cursor, tuple(applied)
