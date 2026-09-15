"""Plano puro de reconciliacao para eventos corporativos globais."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CorporateEventReconciliationDecision(StrEnum):
    MATCHED = "MATCHED"
    CONFLICT = "CONFLICT"


class FractionalResolutionPolicy(StrEnum):
    NO_FRACTIONAL_RESIDUE = "NO_FRACTIONAL_RESIDUE"
    CASH_SETTLEMENT = "CASH_SETTLEMENT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


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


@dataclass(frozen=True)
class CorporateEventMatchResolutionEvidence:
    broker_statement_reference: str
    fractional_policy: FractionalResolutionPolicy
    fractional_quantity: str | None = None
    fractional_settlement_price: str | None = None
    cash_treatment: str | None = None


@dataclass(frozen=True)
class CorporateEventReconciliationDryRunReport:
    schema_version: str
    ok: bool
    decision: str
    dry_run: bool
    database_writes_executed: int
    event_ids: tuple[int, ...]
    updates: tuple[CorporateEventReconciliationUpdate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ok": self.ok,
            "decision": self.decision,
            "dry_run": self.dry_run,
            "database_writes_executed": self.database_writes_executed,
            "event_ids": list(self.event_ids),
            "updates": [
                {
                    "event_id": update.event_id,
                    "reconciliation_status": update.reconciliation_status,
                    "requires_review": update.requires_review,
                    "is_canonical": update.is_canonical,
                    "matched_event_id": update.matched_event_id,
                    "review_reason": update.review_reason,
                }
                for update in self.updates
            ],
        }


def _validate_evidences(
    evidences: tuple[CorporateEventEvidence, ...],
) -> tuple[CorporateEventEvidence, ...]:
    if not evidences:
        raise ValueError("reconciliacao exige ao menos uma evidencia")
    ids = [evidence.event_id for evidence in evidences]
    if len(set(ids)) != len(ids):
        raise ValueError("evidencias duplicadas no plano de reconciliacao")
    return tuple(sorted(evidences, key=lambda item: item.event_id))


def validate_match_resolution_evidence(
    evidence: CorporateEventMatchResolutionEvidence,
) -> None:
    if not evidence.broker_statement_reference.strip():
        raise ValueError("referencia de extrato/corretora e obrigatoria")

    has_fraction = bool(str(evidence.fractional_quantity or "").strip())
    if evidence.fractional_policy == FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE:
        if has_fraction:
            raise ValueError(
                "NO_FRACTIONAL_RESIDUE nao aceita quantidade fracionaria"
            )
        if evidence.fractional_settlement_price or evidence.cash_treatment:
            raise ValueError(
                "NO_FRACTIONAL_RESIDUE nao aceita liquidacao fracionaria"
            )
        return

    if evidence.fractional_policy == FractionalResolutionPolicy.CASH_SETTLEMENT:
        if not has_fraction:
            raise ValueError("CASH_SETTLEMENT exige quantidade fracionaria")
        if not str(evidence.fractional_settlement_price or "").strip():
            raise ValueError("CASH_SETTLEMENT exige preco de liquidacao")
        if not str(evidence.cash_treatment or "").strip():
            raise ValueError("CASH_SETTLEMENT exige tratamento de caixa")
        return

    if evidence.fractional_policy == FractionalResolutionPolicy.MANUAL_REVIEW:
        raise ValueError("MANUAL_REVIEW nao autoriza MATCHED")

    raise ValueError(
        f"politica fracionaria desconhecida: {evidence.fractional_policy}"
    )


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


def build_reconciliation_dry_run_report(
    evidences: tuple[CorporateEventEvidence, ...],
    *,
    decision: CorporateEventReconciliationDecision,
    reason: str,
    canonical_event_id: int | None = None,
) -> CorporateEventReconciliationDryRunReport:
    if decision == CorporateEventReconciliationDecision.CONFLICT:
        updates = plan_conflict_reconciliation(evidences, reason=reason)
    elif decision == CorporateEventReconciliationDecision.MATCHED:
        if canonical_event_id is None:
            raise ValueError("MATCHED exige canonical_event_id")
        updates = plan_matched_reconciliation(
            evidences,
            canonical_event_id=canonical_event_id,
            reason=reason,
        )
    else:
        raise ValueError(f"decisao desconhecida: {decision}")

    return CorporateEventReconciliationDryRunReport(
        schema_version="corporate-event-reconciliation-dry-run.v1",
        ok=True,
        decision=decision.value,
        dry_run=True,
        database_writes_executed=0,
        event_ids=tuple(update.event_id for update in updates),
        updates=updates,
    )


def build_reconciliation_execution_report(
    updates: tuple[CorporateEventReconciliationUpdate, ...],
    *,
    decision: CorporateEventReconciliationDecision,
    database_writes_executed: int,
) -> CorporateEventReconciliationDryRunReport:
    return CorporateEventReconciliationDryRunReport(
        schema_version="corporate-event-reconciliation-execution.v1",
        ok=True,
        decision=decision.value,
        dry_run=False,
        database_writes_executed=database_writes_executed,
        event_ids=tuple(update.event_id for update in updates),
        updates=updates,
    )
