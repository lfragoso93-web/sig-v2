"""Pure authorization contract for real-data promotion and revocation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from app.services.real_data_certification_reader import (
    REAL_DATA_CERTIFICATION_SCHEMA_VERSION,
    RealDataCertificationIdentity,
    canonical_evidence_sha256,
)

REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION = "real-data-promotion-evidence.v1"
REQUIRED_GATE_ISSUE_REFERENCE = "#227"
REQUIRED_PULL_REQUEST_REFERENCE = "#362"
REQUIRED_PROMOTION_CHECKS = frozenset(
    {
        "readiness",
        "inventory",
        "services",
        "schema",
        "dataset_identity",
    }
)


class RealDataCertificationAction(StrEnum):
    PROMOTE = "PROMOTE"
    REVOKE = "REVOKE"


class RealDataCertificationValidationError(ValueError):
    """A certification request failed before any database write."""


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise RealDataCertificationValidationError(f"{field} is required")
    return normalized


def _validate_commit_sha(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 40 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise RealDataCertificationValidationError(
            "commit_sha must be a full 40-character hexadecimal SHA"
        )
    return normalized


def validate_certification_identity(
    identity: RealDataCertificationIdentity,
) -> RealDataCertificationIdentity:
    """Normalize and validate the immutable target identity."""

    if identity.schema_version != REAL_DATA_CERTIFICATION_SCHEMA_VERSION:
        raise RealDataCertificationValidationError(
            "unsupported certification schema_version"
        )
    if identity.gate_issue_reference != REQUIRED_GATE_ISSUE_REFERENCE:
        raise RealDataCertificationValidationError(
            "promotion must reference formal gate #227"
        )
    if identity.pull_request_reference != REQUIRED_PULL_REQUEST_REFERENCE:
        raise RealDataCertificationValidationError(
            "promotion must reference structural PR #362"
        )
    return RealDataCertificationIdentity(
        environment=_required_text(identity.environment, "environment"),
        branch=_required_text(identity.branch, "branch"),
        commit_sha=_validate_commit_sha(identity.commit_sha),
        dataset_reference=_required_text(
            identity.dataset_reference,
            "dataset_reference",
        ),
        alembic_revision=_required_text(
            identity.alembic_revision,
            "alembic_revision",
        ),
        gate_issue_reference=identity.gate_issue_reference,
        pull_request_reference=identity.pull_request_reference,
        schema_version=identity.schema_version,
    )


def validate_promotion_evidence(
    payload: Mapping[str, Any],
    identity: RealDataCertificationIdentity,
) -> None:
    """Reject assisted, incomplete, stale, or write-producing evidence."""

    if payload.get("schema_version") != REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION:
        raise RealDataCertificationValidationError(
            "unsupported promotion evidence schema_version"
        )
    if payload.get("status") != "GO":
        raise RealDataCertificationValidationError("promotion evidence status must be GO")
    if payload.get("dataset_reference") != identity.dataset_reference:
        raise RealDataCertificationValidationError(
            "promotion evidence dataset_reference differs from target identity"
        )
    if payload.get("ready_for_real_data") is not False:
        raise RealDataCertificationValidationError(
            "promotion evidence must record the closed pre-promotion state"
        )
    if payload.get("database_writes_executed") != 0:
        raise RealDataCertificationValidationError(
            "promotion evidence must record zero database writes"
        )
    if payload.get("blockers") != []:
        raise RealDataCertificationValidationError(
            "promotion evidence must contain zero blockers"
        )
    if payload.get("warnings") != []:
        raise RealDataCertificationValidationError(
            "promotion evidence must contain zero warnings"
        )

    checks = payload.get("checks")
    if not isinstance(checks, Mapping):
        raise RealDataCertificationValidationError(
            "promotion evidence checks must be an object"
        )
    if set(checks) != REQUIRED_PROMOTION_CHECKS:
        raise RealDataCertificationValidationError(
            "promotion evidence checks differ from the required check set"
        )
    if any(value is not True for value in checks.values()):
        raise RealDataCertificationValidationError(
            "all required promotion evidence checks must pass"
        )


@dataclass(frozen=True)
class RealDataCertificationPlan:
    """Immutable, dry-run-first plan consumed by the transactional executor."""

    action: RealDataCertificationAction
    identity: RealDataCertificationIdentity
    evidence_payload: Mapping[str, Any]
    evidence_sha256: str
    actor: str
    reason: str
    supersedes_event_id: int | None
    supersedes_event_key: str | None
    event_key: str
    confirmation: str
    dry_run: bool = True
    database_writes_executed: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


def _event_key(
    *,
    action: RealDataCertificationAction,
    identity: RealDataCertificationIdentity,
    evidence_sha256: str,
    supersedes_event_key: str | None,
) -> str:
    material = {
        "action": action.value,
        "identity": asdict(identity),
        "evidence_sha256": evidence_sha256,
        "supersedes_event_key": supersedes_event_key,
    }
    return canonical_evidence_sha256(material)


def _confirmation(
    action: RealDataCertificationAction,
    identity: RealDataCertificationIdentity,
    event_key: str,
) -> str:
    return (
        f"{action.value} REAL DATA ON {identity.environment} AT "
        f"{identity.commit_sha} DATASET {identity.dataset_reference} EVENT {event_key}"
    )


def build_real_data_certification_plan(
    *,
    action: RealDataCertificationAction,
    identity: RealDataCertificationIdentity,
    evidence_payload: Mapping[str, Any],
    actor: str,
    reason: str,
    supersedes_event_id: int | None = None,
    supersedes_event_key: str | None = None,
) -> RealDataCertificationPlan:
    """Build a deterministic plan without touching a database."""

    normalized_identity = validate_certification_identity(identity)
    normalized_actor = _required_text(actor, "actor")
    normalized_reason = _required_text(reason, "reason")
    if action is RealDataCertificationAction.PROMOTE:
        validate_promotion_evidence(evidence_payload, normalized_identity)
    elif action is RealDataCertificationAction.REVOKE:
        if supersedes_event_id is None or not supersedes_event_key:
            raise RealDataCertificationValidationError(
                "revocation must supersede an existing certification event"
            )
        blockers = evidence_payload.get("blockers")
        if not isinstance(blockers, Sequence) or isinstance(blockers, (str, bytes)):
            raise RealDataCertificationValidationError(
                "revocation evidence blockers must be a sequence"
            )
    else:
        raise RealDataCertificationValidationError("unsupported certification action")

    evidence_sha256 = canonical_evidence_sha256(evidence_payload)
    event_key = _event_key(
        action=action,
        identity=normalized_identity,
        evidence_sha256=evidence_sha256,
        supersedes_event_key=supersedes_event_key,
    )
    return RealDataCertificationPlan(
        action=action,
        identity=normalized_identity,
        evidence_payload=dict(evidence_payload),
        evidence_sha256=evidence_sha256,
        actor=normalized_actor,
        reason=normalized_reason,
        supersedes_event_id=supersedes_event_id,
        supersedes_event_key=supersedes_event_key,
        event_key=event_key,
        confirmation=_confirmation(action, normalized_identity, event_key),
    )


def validate_execution_confirmation(
    plan: RealDataCertificationPlan,
    confirmation: str,
) -> None:
    if confirmation != plan.confirmation:
        raise RealDataCertificationValidationError(
            "certification execution confirmation does not match"
        )
