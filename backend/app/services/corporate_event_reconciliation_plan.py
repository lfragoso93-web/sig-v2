"""Plano puro de reconciliacao para eventos corporativos globais."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from app.services.corporate_event_fractional_resolution import FractionalResolutionPolicy


class CorporateEventReconciliationDecision(StrEnum):
    MATCHED = "MATCHED"
    CONFLICT = "CONFLICT"


class CorporateEventMatchEvidenceType(StrEnum):
    BROKER_STATEMENT = "BROKER_STATEMENT"
    OFFICIAL_ISSUER_DOCUMENT = "OFFICIAL_ISSUER_DOCUMENT"
    OFFICIAL_EXCHANGE_DOCUMENT = "OFFICIAL_EXCHANGE_DOCUMENT"


class CorporateEventLedgerBasis(StrEnum):
    RAW_HISTORICAL = "RAW_HISTORICAL"
    ADJUSTED_POST_EVENT = "ADJUSTED_POST_EVENT"


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
    evidence_type: CorporateEventMatchEvidenceType
    evidence_reference: str
    fractional_policy: FractionalResolutionPolicy
    fractional_quantity: str | None = None
    fractional_settlement_price: str | None = None
    cash_treatment: str | None = None
    ledger_basis: CorporateEventLedgerBasis | None = None
    ledger_transformation_reference: str | None = None
    ledger_quantity_factor: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "evidence_type": self.evidence_type.value,
            "evidence_reference": self.evidence_reference,
            "fractional_policy": self.fractional_policy.value,
            "fractional_quantity": self.fractional_quantity,
            "fractional_settlement_price": self.fractional_settlement_price,
            "cash_treatment": self.cash_treatment,
            "ledger_basis": (
                self.ledger_basis.value if self.ledger_basis is not None else None
            ),
            "ledger_transformation_reference": self.ledger_transformation_reference,
            "ledger_quantity_factor": self.ledger_quantity_factor,
        }


@dataclass(frozen=True)
class CorporateEventReconciliationDryRunReport:
    schema_version: str
    ok: bool
    decision: str
    dry_run: bool
    database_writes_executed: int
    event_ids: tuple[int, ...]
    updates: tuple[CorporateEventReconciliationUpdate, ...]
    match_resolution_evidence: CorporateEventMatchResolutionEvidence | None = None
    ledger_preflight: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
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
        if self.match_resolution_evidence is not None:
            payload["match_resolution_evidence"] = (
                self.match_resolution_evidence.to_dict()
            )
        if self.ledger_preflight is not None:
            payload["ledger_preflight"] = self.ledger_preflight
        return payload


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
    if not evidence.evidence_reference.strip():
        raise ValueError("referencia documental da evidencia e obrigatoria")

    if evidence.ledger_basis is not None and not isinstance(
        evidence.ledger_basis, CorporateEventLedgerBasis
    ):
        raise ValueError(
            f"base do ledger desconhecida: {evidence.ledger_basis}"
        )

    has_transformation_reference = bool(
        str(evidence.ledger_transformation_reference or "").strip()
    )
    has_quantity_factor = bool(str(evidence.ledger_quantity_factor or "").strip())
    if evidence.ledger_basis == CorporateEventLedgerBasis.RAW_HISTORICAL:
        if not has_transformation_reference:
            raise ValueError(
                "RAW_HISTORICAL exige referencia da transformacao do ledger"
            )
        if not has_quantity_factor:
            raise ValueError(
                "RAW_HISTORICAL exige fator quantitativo da transformacao"
            )
        try:
            quantity_factor = Decimal(str(evidence.ledger_quantity_factor))
        except (InvalidOperation, ValueError):
            raise ValueError(
                "fator quantitativo da transformacao deve ser decimal"
            ) from None
        if not quantity_factor.is_finite() or quantity_factor <= 0:
            raise ValueError(
                "fator quantitativo da transformacao deve ser positivo"
            )
    elif evidence.ledger_basis == CorporateEventLedgerBasis.ADJUSTED_POST_EVENT:
        if has_transformation_reference or has_quantity_factor:
            raise ValueError(
                "ledger ajustado nao aceita contrato de transformacao pendente"
            )

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


def _reject_unsupported_composite_cash_settlement(
    evidences: tuple[CorporateEventEvidence, ...],
    evidence: CorporateEventMatchResolutionEvidence,
) -> None:
    if evidence.fractional_policy != FractionalResolutionPolicy.CASH_SETTLEMENT:
        return

    tickers = {item.ticker.strip().upper() for item in evidences}
    if "KLBN11" in tickers:
        raise ValueError(
            "CASH_SETTLEMENT para KLBN11 exige contrato explicito de Unit composta"
        )


def _reject_unsupported_adjusted_ledger_reapplication(
    evidences: tuple[CorporateEventEvidence, ...],
    evidence: CorporateEventMatchResolutionEvidence,
) -> None:
    if evidence.fractional_policy != FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE:
        return

    has_amob3 = any(item.ticker.strip().upper() == "AMOB3" for item in evidences)
    if not has_amob3:
        return

    quantity_changing_types = {"GRUPAMENTO", "DESDOBRAMENTO"}
    has_quantity_changing_event = any(
        item.event_type.strip().upper() in quantity_changing_types
        for item in evidences
    )
    if has_quantity_changing_event:
        if evidence.ledger_basis is None:
            raise ValueError(
                "MATCHED para AMOB3 exige contrato explicito de base do ledger"
            )
        if evidence.ledger_basis == CorporateEventLedgerBasis.ADJUSTED_POST_EVENT:
            raise ValueError(
                "MATCHED para AMOB3 rejeita reaplicacao sobre ledger ajustado"
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
    match_resolution_evidence: CorporateEventMatchResolutionEvidence | None = None,
) -> CorporateEventReconciliationDryRunReport:
    if decision == CorporateEventReconciliationDecision.CONFLICT:
        if canonical_event_id is not None:
            raise ValueError("CONFLICT nao aceita canonical_event_id")
        if match_resolution_evidence is not None:
            raise ValueError("CONFLICT nao aceita evidencia de MATCHED")
        updates = plan_conflict_reconciliation(evidences, reason=reason)
    elif decision == CorporateEventReconciliationDecision.MATCHED:
        if canonical_event_id is None:
            raise ValueError("MATCHED exige canonical_event_id")
        if match_resolution_evidence is None:
            raise ValueError("MATCHED exige evidencia operacional")
        validate_match_resolution_evidence(match_resolution_evidence)
        _reject_unsupported_composite_cash_settlement(
            evidences,
            match_resolution_evidence,
        )
        _reject_unsupported_adjusted_ledger_reapplication(
            evidences,
            match_resolution_evidence,
        )
        updates = plan_matched_reconciliation(
            evidences,
            canonical_event_id=canonical_event_id,
            reason=reason,
        )
    else:
        raise ValueError(f"decisao desconhecida: {decision}")

    return CorporateEventReconciliationDryRunReport(
        schema_version=(
            "corporate-event-reconciliation-dry-run.v2"
            if match_resolution_evidence is not None
            else "corporate-event-reconciliation-dry-run.v1"
        ),
        ok=True,
        decision=decision.value,
        dry_run=True,
        database_writes_executed=0,
        event_ids=tuple(update.event_id for update in updates),
        updates=updates,
        match_resolution_evidence=match_resolution_evidence,
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
