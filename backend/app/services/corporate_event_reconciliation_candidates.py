"""Read-only candidate discovery for cross-provider corporate events."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent


@dataclass(frozen=True)
class CorporateEventCandidate:
    event_id: int
    ticker: str
    event_type: str
    source_provider: str
    source_event_id: str | None
    effective_date: date
    quantity_factor: Decimal


@dataclass(frozen=True)
class CorporateEventCandidateGroup:
    ticker: str
    event_type: str
    effective_date: date
    quantity_factor: Decimal
    events: tuple[CorporateEventCandidate, ...]
    review_required: bool = True
    automatic_match_allowed: bool = False


def _candidate(event: CorporateEvent) -> CorporateEventCandidate | None:
    ticker = str(event.ticker or "").strip().upper()
    event_type = str(event.event_type or "").strip().upper()
    source = str(event.source_provider or "").strip().lower()
    effective_date = event.effective_date
    try:
        factor = Decimal(str(event.quantity_factor))
    except (InvalidOperation, ValueError):
        return None
    if (
        not ticker
        or not event_type
        or not source
        or effective_date is None
        or not factor.is_finite()
        or factor <= 0
    ):
        return None
    return CorporateEventCandidate(
        event_id=int(event.id),
        ticker=ticker,
        event_type=event_type,
        source_provider=source,
        source_event_id=event.source_event_id,
        effective_date=effective_date,
        quantity_factor=factor.normalize(),
    )


def discover_cross_provider_candidates(
    events: Iterable[CorporateEvent],
) -> tuple[CorporateEventCandidateGroup, ...]:
    """Group exact economic identities across providers for human review only."""
    grouped: dict[tuple[str, str, date, Decimal], list[CorporateEventCandidate]] = (
        defaultdict(list)
    )
    for event in events:
        if str(event.reconciliation_status or "").strip().upper() != "UNRECONCILED":
            continue
        if str(event.source_provider or "").strip().lower() in {"", "legacy"}:
            continue
        candidate = _candidate(event)
        if candidate is None:
            continue
        key = (
            candidate.ticker,
            candidate.event_type,
            candidate.effective_date,
            candidate.quantity_factor,
        )
        grouped[key].append(candidate)

    result: list[CorporateEventCandidateGroup] = []
    for (ticker, event_type, effective_date, factor), members in grouped.items():
        if len({member.source_provider for member in members}) < 2:
            continue
        result.append(
            CorporateEventCandidateGroup(
                ticker=ticker,
                event_type=event_type,
                effective_date=effective_date,
                quantity_factor=factor,
                events=tuple(sorted(members, key=lambda item: item.event_id)),
            )
        )
    return tuple(
        sorted(
            result,
            key=lambda group: (
                group.effective_date,
                group.ticker,
                group.event_type,
                group.quantity_factor,
            ),
        )
    )


async def load_cross_provider_candidates(
    db: AsyncSession,
    *,
    ticker: str | None = None,
) -> tuple[CorporateEventCandidateGroup, ...]:
    """Read-only database lookup; candidate discovery never reconciles rows."""
    statement = select(CorporateEvent).where(
        CorporateEvent.reconciliation_status == "UNRECONCILED",
        CorporateEvent.source_provider.notin_(("", "legacy")),
    )
    if ticker is not None:
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            raise ValueError("ticker deve ser preenchido")
        statement = statement.where(
            func.upper(func.trim(CorporateEvent.ticker)) == normalized_ticker
        )
    statement = statement.order_by(
        CorporateEvent.effective_date,
        CorporateEvent.ticker,
        CorporateEvent.id,
    )
    result = await db.execute(statement)
    return discover_cross_provider_candidates(result.scalars().all())
