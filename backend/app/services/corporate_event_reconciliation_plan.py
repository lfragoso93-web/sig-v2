"""Plano puro de reconciliacao para eventos corporativos globais."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CorporateEventReconciliationDecision(StrEnum):
    MATCHED = "MATCHED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class CorporateEventEvidence:
    event_id: int
    ticker: str
    event_type: str
    source_provider: str
    source_event_id: str | None


@dataclass(frozen=True)
class CorporateEventReconciliationUpdate:
    event_id: int
    reconciliation_status: str
    requires_review: bool
    is_canonical: bool
    matched_event_id: int | None
    review_reason: str


def _validate_evidences(
    evidences: tuple[CorporateEventEvidence, ...],
) -> tuple[CorporateEventEvidence, ...]:
    if not evidences:
        raise ValueError("reconciliacao exige ao menos uma evidencia")
    ids = [evidence.event_id for evidence in evidences]
    if len(set(ids)) != len(ids):
        raise ValueError("evidencias duplicadas no plano de reconciliacao")
    return tuple(sorted(evidences, key=lambda item: item.event_id))


def plan_conflict_reconciliation(
    evidences: tuple[CorporateEventEvidence, ...],
    *,
    reason: str,
) -> tuple[CorporateEventReconciliationUpdate, ...]:
    """Mantem evidencias conflitantes fora da projecao financeira."""

    normalized = _validate_evidences(evidences)
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("motivo de conflito e obrigatorio")

    return tuple(
        CorporateEventReconciliationUpdate(
            event_id=evidence.event_id,
            reconciliation_status=CorporateEventReconciliationDecision.CONFLICT.value,
            requires_review=True,
            is_canonical=False,
            matched_event_id=None,
            review_reason=clean_reason,
        )
        for evidence in normalized
    )


def plan_matched_reconciliation(
    evidences: tuple[CorporateEventEvidence, ...],
    *,
    canonical_event_id: int,
    reason: str,
) -> tuple[CorporateEventReconciliationUpdate, ...]:
    """Escolhe uma evidencia canonica e vincula as demais como conflito revisavel."""

    normalized = _validate_evidences(evidences)
    event_ids = {evidence.event_id for evidence in normalized}
    if canonical_event_id not in event_ids:
        raise ValueError("evento canonico deve pertencer ao grupo reconciliado")
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("motivo de reconciliacao e obrigatorio")

    updates: list[CorporateEventReconciliationUpdate] = []
    for evidence in normalized:
        is_canonical = evidence.event_id == canonical_event_id
        updates.append(
            CorporateEventReconciliationUpdate(
                event_id=evidence.event_id,
                reconciliation_status=(
                    CorporateEventReconciliationDecision.MATCHED.value
                    if is_canonical
                    else CorporateEventReconciliationDecision.CONFLICT.value
                ),
                requires_review=not is_canonical,
                is_canonical=is_canonical,
                matched_event_id=None if is_canonical else canonical_event_id,
                review_reason=clean_reason,
            )
        )
    return tuple(updates)
