"""Read-only resolution of the persisted real-data certification state."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.real_data_certification_event import RealDataCertificationEvent

REAL_DATA_CERTIFICATION_SCHEMA_VERSION = "real-data-certification.v1"


class RealDataCertificationStatus(StrEnum):
    """Fail-closed outcomes produced by the persisted-state reader."""

    CERTIFIED = "certified"
    NOT_CERTIFIED = "not_certified"
    REVOKED = "revoked"
    INVALID_EVENT_CHAIN = "invalid_event_chain"
    INVALID_EVIDENCE = "invalid_evidence"
    IDENTITY_MISMATCH = "identity_mismatch"
    READ_ERROR = "read_error"


@dataclass(frozen=True)
class RealDataCertificationIdentity:
    """Runtime identity that a persisted promotion must certify exactly."""

    environment: str
    branch: str
    commit_sha: str
    dataset_reference: str
    alembic_revision: str
    gate_issue_reference: str
    pull_request_reference: str
    schema_version: str = REAL_DATA_CERTIFICATION_SCHEMA_VERSION


@dataclass(frozen=True)
class RealDataCertificationState:
    """Resolved certification state; only CERTIFIED may be ready."""

    status: RealDataCertificationStatus
    ready_for_real_data: bool
    event_id: int | None = None
    event_key: str | None = None
    detail: str | None = None


def canonical_evidence_sha256(payload: Mapping[str, Any]) -> str:
    """Hash evidence using the stable JSON representation used by this contract."""

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state(
    status: RealDataCertificationStatus,
    event: RealDataCertificationEvent | None = None,
    *,
    detail: str | None = None,
) -> RealDataCertificationState:
    return RealDataCertificationState(
        status=status,
        ready_for_real_data=status is RealDataCertificationStatus.CERTIFIED,
        event_id=cast(int, event.id) if event is not None else None,
        event_key=cast(str, event.event_key) if event is not None else None,
        detail=detail,
    )


def _has_valid_chain(events: list[RealDataCertificationEvent]) -> bool:
    previous_id: int | None = None
    for event in events:
        if event.supersedes_event_id != previous_id:
            return False
        previous_id = cast(int, event.id)
    return True


def _identity_mismatches(
    event: RealDataCertificationEvent,
    expected: RealDataCertificationIdentity,
) -> list[str]:
    fields = (
        "schema_version",
        "environment",
        "branch",
        "commit_sha",
        "dataset_reference",
        "alembic_revision",
        "gate_issue_reference",
        "pull_request_reference",
    )
    return [field for field in fields if getattr(event, field) != getattr(expected, field)]


async def read_real_data_certification(
    session: AsyncSession,
    expected: RealDataCertificationIdentity,
) -> RealDataCertificationState:
    """Resolve one environment's append-only log without modifying the session."""

    try:
        result = await session.execute(
            select(RealDataCertificationEvent)
            .where(RealDataCertificationEvent.environment == expected.environment)
            .order_by(
                RealDataCertificationEvent.created_at.asc(),
                RealDataCertificationEvent.id.asc(),
            )
        )
        events = list(result.scalars().all())
    except SQLAlchemyError as exc:
        return _state(
            RealDataCertificationStatus.READ_ERROR,
            detail=type(exc).__name__,
        )

    if not events:
        return _state(RealDataCertificationStatus.NOT_CERTIFIED)

    latest = events[-1]
    if not _has_valid_chain(events):
        return _state(
            RealDataCertificationStatus.INVALID_EVENT_CHAIN,
            latest,
            detail="supersedes_event_id",
        )

    if latest.action == "REVOKE":
        return _state(RealDataCertificationStatus.REVOKED, latest)
    if latest.action != "PROMOTE":
        return _state(
            RealDataCertificationStatus.INVALID_EVENT_CHAIN,
            latest,
            detail="action",
        )

    if not isinstance(latest.evidence_payload, Mapping):
        return _state(
            RealDataCertificationStatus.INVALID_EVIDENCE,
            latest,
            detail="evidence_payload",
        )
    try:
        evidence_sha256 = canonical_evidence_sha256(latest.evidence_payload)
    except (TypeError, ValueError):
        return _state(
            RealDataCertificationStatus.INVALID_EVIDENCE,
            latest,
            detail="evidence_payload",
        )
    if latest.evidence_sha256 != evidence_sha256:
        return _state(
            RealDataCertificationStatus.INVALID_EVIDENCE,
            latest,
            detail="evidence_sha256",
        )

    mismatches = _identity_mismatches(latest, expected)
    if mismatches:
        return _state(
            RealDataCertificationStatus.IDENTITY_MISMATCH,
            latest,
            detail=",".join(mismatches),
        )

    return _state(RealDataCertificationStatus.CERTIFIED, latest)
