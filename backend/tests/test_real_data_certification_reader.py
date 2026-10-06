"""Fail-closed tests for the persisted real-data certification reader."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from app.models.real_data_certification_event import RealDataCertificationEvent
from app.services.real_data_certification_reader import (
    REAL_DATA_CERTIFICATION_SCHEMA_VERSION,
    RealDataCertificationIdentity,
    RealDataCertificationStatus,
    canonical_evidence_sha256,
    read_real_data_certification,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession


def _identity(**overrides: str) -> RealDataCertificationIdentity:
    values = {
        "environment": "pre-production",
        "branch": "stable-15jun",
        "commit_sha": "a" * 40,
        "dataset_reference": "dataset:2026-10-06",
        "alembic_revision": "20261005_real_data_certification",
        "gate_issue_reference": "#227",
        "pull_request_reference": "#362",
    }
    values.update(overrides)
    return RealDataCertificationIdentity(**values)


def _event(
    *,
    event_key: str,
    action: str = "PROMOTE",
    supersedes_event_id: int | None = None,
    created_at: datetime | None = None,
    evidence_payload: dict[str, object] | None = None,
    **overrides: str,
) -> RealDataCertificationEvent:
    identity = _identity()
    payload = evidence_payload or {"checks": ["migration", "dataset"]}
    values = {
        "event_key": event_key,
        "action": action,
        "schema_version": REAL_DATA_CERTIFICATION_SCHEMA_VERSION,
        "environment": identity.environment,
        "branch": identity.branch,
        "commit_sha": identity.commit_sha,
        "dataset_reference": identity.dataset_reference,
        "alembic_revision": identity.alembic_revision,
        "gate_issue_reference": identity.gate_issue_reference,
        "pull_request_reference": identity.pull_request_reference,
        "evidence_sha256": canonical_evidence_sha256(payload),
        "evidence_payload": payload,
        "actor": "test-suite",
        "reason": "contract test",
        "supersedes_event_id": supersedes_event_id,
        "created_at": created_at or datetime.now(timezone.utc),
    }
    values.update(overrides)
    return RealDataCertificationEvent(**values)


@pytest.mark.asyncio
async def test_absent_certification_fails_closed(db: AsyncSession) -> None:
    state = await read_real_data_certification(db, _identity())

    assert state.status is RealDataCertificationStatus.NOT_CERTIFIED
    assert state.ready_for_real_data is False


@pytest.mark.asyncio
async def test_exact_persisted_promotion_is_certified(db: AsyncSession) -> None:
    event = _event(event_key="promote-1")
    db.add(event)
    await db.flush()

    state = await read_real_data_certification(db, _identity())

    assert state.status is RealDataCertificationStatus.CERTIFIED
    assert state.ready_for_real_data is True
    assert state.event_id == event.id
    assert state.event_key == "promote-1"


@pytest.mark.asyncio
async def test_latest_revocation_fails_closed(db: AsyncSession) -> None:
    promoted = _event(event_key="promote-1")
    db.add(promoted)
    await db.flush()
    revoked = _event(
        event_key="revoke-1",
        action="REVOKE",
        supersedes_event_id=promoted.id,
        created_at=promoted.created_at + timedelta(seconds=1),
    )
    db.add(revoked)
    await db.flush()

    state = await read_real_data_certification(db, _identity())

    assert state.status is RealDataCertificationStatus.REVOKED
    assert state.ready_for_real_data is False
    assert state.event_key == "revoke-1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "unexpected"),
        ("branch", "main"),
        ("commit_sha", "b" * 40),
        ("dataset_reference", "dataset:other"),
        ("alembic_revision", "older_revision"),
        ("gate_issue_reference", "#999"),
        ("pull_request_reference", "#999"),
    ],
)
async def test_identity_mismatch_fails_closed(
    db: AsyncSession,
    field: str,
    value: str,
) -> None:
    db.add(_event(event_key=f"mismatch-{field}", **{field: value}))
    await db.flush()

    state = await read_real_data_certification(db, _identity())

    assert state.status is RealDataCertificationStatus.IDENTITY_MISMATCH
    assert state.ready_for_real_data is False
    assert state.detail == field


@pytest.mark.asyncio
async def test_corrupted_evidence_hash_fails_closed(db: AsyncSession) -> None:
    db.add(_event(event_key="bad-hash", evidence_sha256="0" * 64))
    await db.flush()

    state = await read_real_data_certification(db, _identity())

    assert state.status is RealDataCertificationStatus.INVALID_EVIDENCE
    assert state.ready_for_real_data is False


@pytest.mark.asyncio
async def test_broken_supersession_chain_fails_closed(db: AsyncSession) -> None:
    first = _event(event_key="promote-1")
    db.add(first)
    await db.flush()
    db.add(
        _event(
            event_key="promote-2",
            supersedes_event_id=None,
            created_at=first.created_at + timedelta(seconds=1),
        )
    )
    await db.flush()

    state = await read_real_data_certification(db, _identity())

    assert state.status is RealDataCertificationStatus.INVALID_EVENT_CHAIN
    assert state.ready_for_real_data is False


@pytest.mark.asyncio
async def test_database_read_error_fails_closed() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.side_effect = OperationalError("select", {}, Exception("offline"))

    state = await read_real_data_certification(session, _identity())

    assert state.status is RealDataCertificationStatus.READ_ERROR
    assert state.ready_for_real_data is False
    assert state.detail == "OperationalError"
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()
