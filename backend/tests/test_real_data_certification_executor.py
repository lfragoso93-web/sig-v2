"""Transactional tests for guarded certification persistence."""

from typing import Any

import pytest
from app.models.real_data_certification_event import RealDataCertificationEvent
from app.services.real_data_certification_contract import (
    REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION,
    REQUIRED_PROMOTION_CHECKS,
    RealDataCertificationAction,
    RealDataCertificationValidationError,
)
from app.services.real_data_certification_executor import (
    StaleRealDataCertificationPlanError,
    execute_real_data_certification_plan,
    mark_certification_result_committed,
    prepare_real_data_certification_plan,
)
from app.services.real_data_certification_reader import (
    RealDataCertificationIdentity,
    RealDataCertificationStatus,
    read_real_data_certification,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _identity() -> RealDataCertificationIdentity:
    return RealDataCertificationIdentity(
        environment="local-canonical",
        branch="stable-15jun",
        commit_sha="a" * 40,
        dataset_reference="dataset:2026-10-06",
        alembic_revision="20261005_real_data_certification",
        gate_issue_reference="#227",
        pull_request_reference="#362",
    )


def _promotion_evidence(**extra: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION,
        "status": "GO",
        "dataset_reference": "dataset:2026-10-06",
        "ready_for_real_data": False,
        "database_writes_executed": 0,
        "blockers": [],
        "warnings": [],
        "checks": {check: True for check in REQUIRED_PROMOTION_CHECKS},
    }
    payload.update(extra)
    return payload


async def _prepare(
    db: AsyncSession,
    *,
    action: RealDataCertificationAction = RealDataCertificationAction.PROMOTE,
    evidence: dict[str, Any] | None = None,
):
    return await prepare_real_data_certification_plan(
        db,
        action=action,
        identity=_identity(),
        evidence_payload=evidence or _promotion_evidence(),
        actor="operator@example.test",
        reason="formal decision",
    )


async def _event_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(RealDataCertificationEvent.id)))
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_prepare_is_read_only_and_bound_to_current_chain(
    db: AsyncSession,
) -> None:
    plan = await _prepare(db)

    assert plan.dry_run is True
    assert plan.database_writes_executed == 0
    assert plan.supersedes_event_id is None
    assert await _event_count(db) == 0
    assert not db.new
    assert not db.dirty


@pytest.mark.asyncio
async def test_confirmation_is_checked_before_database_access(
    db: AsyncSession,
) -> None:
    plan = await _prepare(db)
    await db.close()

    with pytest.raises(RealDataCertificationValidationError, match="does not match"):
        await execute_real_data_certification_plan(
            db,
            plan=plan,
            confirmation="yes",
        )


@pytest.mark.asyncio
async def test_execute_flushes_one_promotion_without_committing(
    db: AsyncSession,
) -> None:
    plan = await _prepare(db)

    result = await execute_real_data_certification_plan(
        db,
        plan=plan,
        confirmation=plan.confirmation,
    )

    assert result.database_writes_executed == 1
    assert result.transaction_committed is False
    assert result.idempotent is False
    assert await _event_count(db) == 1
    state = await read_real_data_certification(db, _identity())
    assert state.status is RealDataCertificationStatus.CERTIFIED
    assert mark_certification_result_committed(result).transaction_committed is True


@pytest.mark.asyncio
async def test_repeated_exact_promotion_is_idempotent(db: AsyncSession) -> None:
    first_plan = await _prepare(db)
    await execute_real_data_certification_plan(
        db,
        plan=first_plan,
        confirmation=first_plan.confirmation,
    )
    repeated_plan = await _prepare(db)

    repeated = await execute_real_data_certification_plan(
        db,
        plan=repeated_plan,
        confirmation=repeated_plan.confirmation,
    )

    assert repeated.idempotent is True
    assert repeated.database_writes_executed == 0
    assert await _event_count(db) == 1


@pytest.mark.asyncio
async def test_stale_dry_run_is_rejected(db: AsyncSession) -> None:
    stale = await _prepare(db, evidence=_promotion_evidence(run="stale"))
    current = await _prepare(db, evidence=_promotion_evidence(run="current"))
    await execute_real_data_certification_plan(
        db,
        plan=current,
        confirmation=current.confirmation,
    )

    with pytest.raises(StaleRealDataCertificationPlanError, match="changed"):
        await execute_real_data_certification_plan(
            db,
            plan=stale,
            confirmation=stale.confirmation,
        )
    assert await _event_count(db) == 1


@pytest.mark.asyncio
async def test_revocation_appends_event_and_reader_fails_closed(
    db: AsyncSession,
) -> None:
    promotion = await _prepare(db)
    await execute_real_data_certification_plan(
        db,
        plan=promotion,
        confirmation=promotion.confirmation,
    )
    revocation = await _prepare(
        db,
        action=RealDataCertificationAction.REVOKE,
        evidence={"blockers": ["operator_requested"]},
    )

    result = await execute_real_data_certification_plan(
        db,
        plan=revocation,
        confirmation=revocation.confirmation,
    )

    assert result.database_writes_executed == 1
    assert await _event_count(db) == 2
    state = await read_real_data_certification(db, _identity())
    assert state.status is RealDataCertificationStatus.REVOKED
    assert state.ready_for_real_data is False


@pytest.mark.asyncio
async def test_caller_rollback_removes_uncommitted_event(db: AsyncSession) -> None:
    plan = await _prepare(db)
    await execute_real_data_certification_plan(
        db,
        plan=plan,
        confirmation=plan.confirmation,
    )

    await db.rollback()

    assert await _event_count(db) == 0
