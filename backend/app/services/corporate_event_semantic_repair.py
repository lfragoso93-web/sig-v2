"""Dry-run planning for historical BRAPI/B3 corporate-event repair."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.services.corporate_action_engine import (
    CorporateActionKind,
    normalize_b3_corporate_actions,
    normalize_brapi_corporate_actions,
    source_payload_hash,
)

_REPAIRABLE_LABELS = {
    CorporateActionKind.REVERSE_SPLIT.value,
    CorporateActionKind.SPLIT.value,
}


class CorporateEventSemanticRepairError(ValueError):
    """Evento fora do contrato do reparo semantico dry-run."""


@dataclass(frozen=True)
class CorporateEventSemanticRepairCandidate:
    event_id: int
    ticker: str
    source_provider: str
    old_event_type: str
    new_event_type: str
    old_source_event_id: str | None
    new_source_event_id: str
    old_source_payload_hash: str | None
    new_source_payload_hash: str
    event_date: date
    old_quantity_factor: Decimal
    quantity_factor: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "ticker": self.ticker,
            "source_provider": self.source_provider,
            "old_event_type": self.old_event_type,
            "new_event_type": self.new_event_type,
            "old_source_event_id": self.old_source_event_id,
            "new_source_event_id": self.new_source_event_id,
            "old_source_payload_hash": self.old_source_payload_hash,
            "new_source_payload_hash": self.new_source_payload_hash,
            "event_date": self.event_date.isoformat(),
            "old_quantity_factor": str(self.old_quantity_factor),
            "quantity_factor": str(self.quantity_factor),
        }


@dataclass(frozen=True)
class CorporateEventSemanticRepairReport:
    candidates: tuple[CorporateEventSemanticRepairCandidate, ...]
    dry_run: bool = True
    database_writes_executed: int = 0
    schema_version: str = "corporate-event-semantic-repair.v1"

    @property
    def total_candidates(self) -> int:
        return len(self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "dry_run": self.dry_run,
            "database_writes_executed": self.database_writes_executed,
            "total_candidates": self.total_candidates,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def _raw_label(raw_metadata: object) -> str:
    if not isinstance(raw_metadata, dict):
        raise CorporateEventSemanticRepairError("raw_metadata deve ser objeto")
    return str(raw_metadata.get("label") or "").strip().upper()


def _brapi_single_event_payload(
    ticker: str,
    raw_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "results": [
            {
                "symbol": ticker,
                "data": {
                    "stockDividends": [dict(raw_metadata)],
                    "subscriptions": [],
                },
            }
        ]
    }


def _identity_set(
    existing_source_identities: Iterable[tuple[str | None, str | None]] | None,
) -> set[tuple[str, str]]:
    return {
        (str(source), str(source_event_id))
        for source, source_event_id in existing_source_identities or ()
        if source and source_event_id
    }


def _require_event_contract(event: CorporateEvent) -> dict[str, Any]:
    event_id = getattr(event, "id", None)
    if event_id is None:
        raise CorporateEventSemanticRepairError("evento sem id")
    provider = str(event.source_provider or "").strip().lower()
    if provider not in {"brapi", "b3"}:
        raise CorporateEventSemanticRepairError(
            f"evento {event_id}: provider fora do escopo do reparo: {provider}"
        )
    if event.reconciliation_status != "UNRECONCILED":
        raise CorporateEventSemanticRepairError(
            f"evento {event_id}: reconciliation_status deve ser UNRECONCILED"
        )
    if event.requires_review is not True:
        raise CorporateEventSemanticRepairError(
            f"evento {event_id}: requires_review deve ser true"
        )
    if event.matched_event_id is not None:
        raise CorporateEventSemanticRepairError(
            f"evento {event_id}: matched_event_id deve ser null"
        )
    if not isinstance(event.raw_metadata, dict):
        raise CorporateEventSemanticRepairError(
            f"evento {event_id}: raw_metadata deve ser objeto"
        )
    label = _raw_label(event.raw_metadata)
    if label not in _REPAIRABLE_LABELS:
        raise CorporateEventSemanticRepairError(
            f"evento {event_id}: label fora do escopo do reparo: {label or '<vazio>'}"
        )
    if provider == "b3":
        raw_isin = str(event.raw_metadata.get("isinCode") or "").strip().upper()
        event_isin = str(event.isin_code or "").strip().upper()
        if not raw_isin or not event_isin or raw_isin != event_isin:
            raise CorporateEventSemanticRepairError(
                f"evento {event_id}: ISIN B3 ausente ou divergente"
            )
        if event.record_date is None or (event.effective_date and event.record_date != event.effective_date):
            raise CorporateEventSemanticRepairError(
                f"evento {event_id}: record_date B3 divergente do evento"
            )
        try:
            raw_factor = Decimal(str(event.raw_metadata.get("factor")))
            stored_factor = Decimal(str(event.quantity_factor))
        except (InvalidOperation, ValueError) as exc:
            raise CorporateEventSemanticRepairError(
                f"evento {event_id}: fator B3 invalido"
            ) from exc
        if (
            not raw_factor.is_finite()
            or raw_factor <= 0
            or raw_factor != stored_factor
        ):
            raise CorporateEventSemanticRepairError(
                f"evento {event_id}: fator B3 bruto diverge do fator persistido"
            )
    return event.raw_metadata


def _build_candidate(
    event: CorporateEvent,
    *,
    existing_identities: set[tuple[str, str]],
) -> CorporateEventSemanticRepairCandidate:
    raw_metadata = _require_event_contract(event)
    ticker = str(event.ticker or "").strip().upper()
    provider = str(event.source_provider).strip().lower()
    if provider == "b3":
        actions = normalize_b3_corporate_actions(
            ticker,
            {
                "code": raw_metadata.get("sourceIssuer"),
                "stockDividends": [dict(raw_metadata)],
                "subscriptions": [],
            },
            expected_isin=str(event.isin_code),
        )
    else:
        actions = normalize_brapi_corporate_actions(
            ticker,
            _brapi_single_event_payload(ticker, raw_metadata),
        )
    if len(actions) != 1:
        raise CorporateEventSemanticRepairError(
            f"evento {event.id}: normalizacao deve produzir exatamente uma acao"
        )

    action = actions[0]
    new_identity = (action.source, action.source_event_id)
    new_payload_hash = source_payload_hash(action)
    if (
        event.event_type == action.kind.value
        and event.source_event_id == action.source_event_id
        and event.source_payload_hash == new_payload_hash
    ):
        raise CorporateEventSemanticRepairError(
            f"evento {event.id}: sem mudanca semantica real"
        )
    current_identity = (str(event.source_provider), str(event.source_event_id))
    if new_identity != current_identity and new_identity in existing_identities:
        raise CorporateEventSemanticRepairError(
            f"evento {event.id}: nova identidade ja existe: {new_identity}"
        )

    return CorporateEventSemanticRepairCandidate(
        event_id=int(event.id),
        ticker=ticker,
        old_event_type=str(event.event_type),
        new_event_type=action.kind.value,
        source_provider=provider,
        old_source_event_id=event.source_event_id,
        new_source_event_id=action.source_event_id,
        old_source_payload_hash=event.source_payload_hash,
        new_source_payload_hash=new_payload_hash,
        event_date=action.event_date,
        old_quantity_factor=Decimal(str(event.quantity_factor)),
        quantity_factor=action.quantity_factor,
    )


def build_corporate_event_semantic_repair_plan(
    events: Iterable[CorporateEvent],
    *,
    existing_source_identities: Iterable[tuple[str | None, str | None]] | None = None,
) -> CorporateEventSemanticRepairReport:
    existing_identities = _identity_set(existing_source_identities)
    candidates = []
    for event in events:
        candidate = _build_candidate(event, existing_identities=existing_identities)
        existing_identities.add(
            (candidate.source_provider, candidate.new_source_event_id)
        )
        candidates.append(candidate)
    candidates = tuple(candidates)
    return CorporateEventSemanticRepairReport(candidates=candidates)


async def _load_events_for_repair(
    db: AsyncSession,
    *,
    event_ids: tuple[int, ...],
    lock: bool,
) -> tuple[CorporateEvent, ...]:
    if not event_ids:
        raise CorporateEventSemanticRepairError("event_ids e obrigatorio")
    if len(set(event_ids)) != len(event_ids):
        raise CorporateEventSemanticRepairError("event_ids contem duplicidade")

    statement = select(CorporateEvent).where(CorporateEvent.id.in_(event_ids))
    if lock:
        statement = statement.with_for_update()
    result = await db.execute(statement)
    events = tuple(sorted(result.scalars().all(), key=lambda item: int(item.id)))
    found_ids = {int(event.id) for event in events}
    missing = sorted(set(event_ids) - found_ids)
    if missing:
        raise CorporateEventSemanticRepairError(f"eventos nao encontrados: {missing}")
    return events


async def _existing_source_identities(
    db: AsyncSession,
    *,
    exclude_event_ids: tuple[int, ...],
) -> set[tuple[str, str]]:
    statement = (
        select(CorporateEvent.source_provider, CorporateEvent.source_event_id)
        .where(CorporateEvent.source_provider.is_not(None))
        .where(CorporateEvent.source_event_id.is_not(None))
    )
    if exclude_event_ids:
        statement = statement.where(CorporateEvent.id.not_in(exclude_event_ids))
    result = await db.execute(
        statement
    )
    return {
        (str(source_provider), str(source_event_id))
        for source_provider, source_event_id in result.all()
        if source_provider and source_event_id
    }


async def build_corporate_event_semantic_repair_dry_run(
    db: AsyncSession,
    *,
    event_ids: tuple[int, ...],
) -> CorporateEventSemanticRepairReport:
    events = await _load_events_for_repair(db, event_ids=event_ids, lock=False)
    return build_corporate_event_semantic_repair_plan(
        events,
        existing_source_identities=await _existing_source_identities(
            db,
            exclude_event_ids=event_ids,
        ),
    )


def _apply_candidate(
    event: CorporateEvent,
    candidate: CorporateEventSemanticRepairCandidate,
) -> None:
    event.event_type = candidate.new_event_type
    event.source_event_id = candidate.new_source_event_id
    event.source_payload_hash = candidate.new_source_payload_hash
    event.quantity_factor = candidate.quantity_factor
    event.ratio = candidate.quantity_factor


async def execute_corporate_event_semantic_repair(
    db: AsyncSession,
    *,
    event_ids: tuple[int, ...],
) -> CorporateEventSemanticRepairReport:
    events = await _load_events_for_repair(db, event_ids=event_ids, lock=True)
    events_by_id = {int(event.id): event for event in events}
    report = build_corporate_event_semantic_repair_plan(
        events,
        existing_source_identities=await _existing_source_identities(
            db,
            exclude_event_ids=event_ids,
        ),
    )
    for candidate in report.candidates:
        event = events_by_id.get(candidate.event_id)
        if event is None:
            raise CorporateEventSemanticRepairError(
                f"evento nao encontrado durante execucao: {candidate.event_id}"
            )
        _apply_candidate(event, candidate)
    await db.flush()
    return CorporateEventSemanticRepairReport(
        candidates=report.candidates,
        dry_run=False,
        database_writes_executed=len(report.candidates),
    )
