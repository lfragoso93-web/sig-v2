"""Dry-run planning for historical BRAPI corporate-event semantic repair."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from app.models.corporate_event import CorporateEvent
from app.services.corporate_action_engine import (
    CorporateActionKind,
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
    old_event_type: str
    new_event_type: str
    old_source_event_id: str | None
    new_source_event_id: str
    old_source_payload_hash: str | None
    new_source_payload_hash: str
    event_date: date
    quantity_factor: Decimal


@dataclass(frozen=True)
class CorporateEventSemanticRepairReport:
    candidates: tuple[CorporateEventSemanticRepairCandidate, ...]

    @property
    def total_candidates(self) -> int:
        return len(self.candidates)


def _raw_label(raw_metadata: object) -> str:
    if not isinstance(raw_metadata, dict):
        raise CorporateEventSemanticRepairError("raw_metadata deve ser objeto")
    return str(raw_metadata.get("label") or "").strip().upper()


def _brapi_single_event_payload(ticker: str, raw_metadata: dict[str, Any]) -> dict[str, Any]:
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
    if event.source_provider != "brapi":
        raise CorporateEventSemanticRepairError(f"evento {event_id}: provider nao e brapi")
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
    return event.raw_metadata


def _build_candidate(
    event: CorporateEvent,
    *,
    existing_identities: set[tuple[str, str]],
) -> CorporateEventSemanticRepairCandidate:
    raw_metadata = _require_event_contract(event)
    ticker = str(event.ticker or "").strip().upper()
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
    if new_identity in existing_identities:
        raise CorporateEventSemanticRepairError(
            f"evento {event.id}: nova identidade ja existe: {new_identity}"
        )

    new_payload_hash = source_payload_hash(action)
    if (
        event.event_type == action.kind.value
        and event.source_event_id == action.source_event_id
        and event.source_payload_hash == new_payload_hash
    ):
        raise CorporateEventSemanticRepairError(
            f"evento {event.id}: sem mudanca semantica real"
        )

    return CorporateEventSemanticRepairCandidate(
        event_id=int(event.id),
        ticker=ticker,
        old_event_type=str(event.event_type),
        new_event_type=action.kind.value,
        old_source_event_id=event.source_event_id,
        new_source_event_id=action.source_event_id,
        old_source_payload_hash=event.source_payload_hash,
        new_source_payload_hash=new_payload_hash,
        event_date=action.event_date,
        quantity_factor=action.quantity_factor,
    )


def build_corporate_event_semantic_repair_plan(
    events: Iterable[CorporateEvent],
    *,
    existing_source_identities: Iterable[tuple[str | None, str | None]] | None = None,
) -> CorporateEventSemanticRepairReport:
    existing_identities = _identity_set(existing_source_identities)
    candidates = tuple(
        _build_candidate(event, existing_identities=existing_identities)
        for event in events
    )
    return CorporateEventSemanticRepairReport(candidates=candidates)
