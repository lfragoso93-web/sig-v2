"""Contrato bloqueado para a futura execução de eventos corporativos complexos."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from app.models.corporate_event import CorporateEvent
from app.services.corporate_exchange_projection_service import (
    CorporateExchangeProjectionPlan,
)


class ComplexEventExecutionIntentStatus(StrEnum):
    BLOCKED_EVENT_NOT_REVIEWED = "BLOCKED_EVENT_NOT_REVIEWED"
    BLOCKED_PLAN = "BLOCKED_PLAN"
    BLOCKED_FEATURE_DISABLED = "BLOCKED_FEATURE_DISABLED"
    READY = "READY"


@dataclass(frozen=True)
class ComplexEventExecutionIntent:
    event_id: int
    portfolio_id: int
    idempotency_key: str
    status: ComplexEventExecutionIntentStatus
    writable: bool
    blocking_reasons: tuple[str, ...]


def _idempotency_key(
    event: CorporateEvent,
    *,
    portfolio_id: int,
    plan: CorporateExchangeProjectionPlan,
) -> str:
    payload = {
        "event_id": int(event.id),
        "portfolio_id": int(portfolio_id),
        "economic_identity_hash": event.economic_identity_hash,
        "reviewed_at": event.reviewed_at.isoformat() if event.reviewed_at else None,
        "plan": {
            key: str(value) if key != "blocking_reasons" else list(value)
            for key, value in asdict(plan).items()
        },
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"complex-event:{digest}"


def build_complex_event_execution_intent(
    event: CorporateEvent,
    *,
    portfolio_id: int,
    plan: CorporateExchangeProjectionPlan,
    execution_enabled: bool,
) -> ComplexEventExecutionIntent:
    """Avalia gates e gera identidade estável; nunca escreve no banco."""

    reasons: list[str] = []
    status_value = str(getattr(event.status, "value", event.status))
    reconciliation_value = str(
        getattr(event.reconciliation_status, "value", event.reconciliation_status)
    )
    manually_reviewed = (
        status_value == "VALIDATED"
        and reconciliation_value == "MANUALLY_VALIDATED"
        and event.reviewed_by_user_id is not None
        and not event.requires_review
    )
    if not manually_reviewed:
        status = ComplexEventExecutionIntentStatus.BLOCKED_EVENT_NOT_REVIEWED
        reasons.append("event_not_manually_reviewed")
    elif not plan.executable:
        status = ComplexEventExecutionIntentStatus.BLOCKED_PLAN
        reasons.extend(plan.blocking_reasons or ("projection_plan_incomplete",))
    elif not execution_enabled:
        status = ComplexEventExecutionIntentStatus.BLOCKED_FEATURE_DISABLED
        reasons.append("feature_disabled")
    else:
        status = ComplexEventExecutionIntentStatus.READY

    return ComplexEventExecutionIntent(
        event_id=int(event.id),
        portfolio_id=int(portfolio_id),
        idempotency_key=_idempotency_key(event, portfolio_id=portfolio_id, plan=plan),
        status=status,
        writable=False,
        blocking_reasons=tuple(reasons),
    )
