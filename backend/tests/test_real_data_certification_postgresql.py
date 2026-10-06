"""Opt-in PostgreSQL proofs for persisted real-data certification.

The suite is skipped unless REAL_DATA_CERTIFICATION_TEST_DATABASE_URL points to
an explicitly named test database. It never targets the canonical SGI database.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Any, cast

import pytest
import pytest_asyncio
from app.core.config import Settings
from app.models.real_data_certification_event import RealDataCertificationEvent
from app.services.real_data_certification_contract import (
    REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION,
    REQUIRED_PROMOTION_CHECKS,
    RealDataCertificationAction,
)
from app.services.real_data_certification_executor import (
    StaleRealDataCertificationPlanError,
    execute_real_data_certification_plan,
    prepare_real_data_certification_plan,
)
from app.services.real_data_certification_reader import (
    RealDataCertificationIdentity,
    RealDataCertificationStatus,
    read_real_data_certification,
)
from app.services.real_data_readiness_report import build_real_data_readiness_report
from app.services.real_data_runtime_identity import resolve_real_data_runtime_identity
from sqlalchemy import Table, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_DATABASE_URL_ENV = "REAL_DATA_CERTIFICATION_TEST_DATABASE_URL"


def _test_database_url() -> str:
    value = os.getenv(_DATABASE_URL_ENV)
    if not value:
        pytest.skip(f"{_DATABASE_URL_ENV} is not configured")
    url = make_url(value)
    if not url.drivername.startswith("postgresql+"):
        pytest.fail(f"{_DATABASE_URL_ENV} must use an async PostgreSQL driver")
    database = (url.database or "").lower()
    if not (database.startswith("test_") or database.endswith("_test")):
        pytest.fail(f"{_DATABASE_URL_ENV} must name an explicit test database")
    return value


@pytest_asyncio.fixture
async def postgres_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_test_database_url(), pool_size=4, max_overflow=0)
    table = cast(Table, RealDataCertificationEvent.__table__)
    async with engine.begin() as connection:
        await connection.run_sync(table.create, checkfirst=True)
        await connection.execute(table.delete())
        await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(64))")
        )
        await connection.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('20261005_real_data_certification')"
            )
        )
    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(table.drop, checkfirst=True)
            await connection.execute(text("DROP TABLE alembic_version"))
        await engine.dispose()


def _identity() -> RealDataCertificationIdentity:
    return RealDataCertificationIdentity(
        environment="postgresql-certification-test",
        branch="stable-15jun",
        commit_sha="a" * 40,
        dataset_reference="dataset:postgresql-test",
        alembic_revision="20261005_real_data_certification",
        gate_issue_reference="#227",
        pull_request_reference="#362",
    )


def _evidence(run: str) -> dict[str, Any]:
    return {
        "schema_version": REAL_DATA_PROMOTION_EVIDENCE_SCHEMA_VERSION,
        "status": "GO",
        "dataset_reference": _identity().dataset_reference,
        "ready_for_real_data": False,
        "database_writes_executed": 0,
        "blockers": [],
        "warnings": [],
        "checks": {check: True for check in REQUIRED_PROMOTION_CHECKS},
        "run": run,
    }


async def _plan(session: AsyncSession, run: str):
    return await prepare_real_data_certification_plan(
        session,
        action=RealDataCertificationAction.PROMOTE,
        identity=_identity(),
        evidence_payload=_evidence(run),
        actor="postgresql-test",
        reason="isolated integration proof",
    )


@pytest.mark.asyncio
async def test_postgresql_lock_serializes_identical_concurrent_promotions(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with sessions() as first, sessions() as second:
        first_plan, second_plan = await asyncio.gather(
            _plan(first, "concurrent"),
            _plan(second, "concurrent"),
        )

        async def execute_and_commit(session: AsyncSession, plan: Any):
            result = await execute_real_data_certification_plan(
                session,
                plan=plan,
                confirmation=plan.confirmation,
            )
            await session.commit()
            return result

        results = await asyncio.gather(
            execute_and_commit(first, first_plan),
            execute_and_commit(second, second_plan),
        )

    assert sorted(result.database_writes_executed for result in results) == [0, 1]
    assert sorted(result.idempotent for result in results) == [False, True]
    async with sessions() as verification:
        count = await verification.scalar(
            select(func.count(RealDataCertificationEvent.id))
        )
    assert count == 1


@pytest.mark.asyncio
async def test_postgresql_rejects_stale_plan_after_committed_competitor(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with sessions() as stale_session, sessions() as winner_session:
        stale = await _plan(stale_session, "stale")
        winner = await _plan(winner_session, "winner")
        await execute_real_data_certification_plan(
            winner_session,
            plan=winner,
            confirmation=winner.confirmation,
        )
        await winner_session.commit()

        with pytest.raises(StaleRealDataCertificationPlanError, match="changed"):
            await execute_real_data_certification_plan(
                stale_session,
                plan=stale,
                confirmation=stale.confirmation,
            )
        await stale_session.rollback()


@pytest.mark.asyncio
async def test_postgresql_reader_reconstructs_state_after_engine_restart(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with sessions() as session:
        plan = await _plan(session, "restart")
        await execute_real_data_certification_plan(
            session,
            plan=plan,
            confirmation=plan.confirmation,
        )
        await session.commit()

    await postgres_engine.dispose()
    restarted_engine = create_async_engine(_test_database_url())
    try:
        restarted_sessions = async_sessionmaker(
            restarted_engine,
            expire_on_commit=False,
        )
        async with restarted_sessions() as restarted:
            state = await read_real_data_certification(restarted, _identity())
    finally:
        await restarted_engine.dispose()

    assert state.status is RealDataCertificationStatus.CERTIFIED
    assert state.ready_for_real_data is True


@pytest.mark.asyncio
async def test_postgresql_runtime_identity_and_report_survive_engine_restart(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with sessions() as session:
        plan = await _plan(session, "runtime-restart")
        await execute_real_data_certification_plan(
            session,
            plan=plan,
            confirmation=plan.confirmation,
        )
        await session.commit()

    await postgres_engine.dispose()
    restarted_engine = create_async_engine(_test_database_url())
    runtime_settings = Settings.model_validate(
        {
            "ENVIRONMENT": _identity().environment,
            "APP_BRANCH": _identity().branch,
            "APP_COMMIT_SHA": _identity().commit_sha,
            "REAL_DATASET_REFERENCE": _identity().dataset_reference,
        }
    )
    try:
        restarted_sessions = async_sessionmaker(
            restarted_engine,
            expire_on_commit=False,
        )
        async with restarted_sessions() as restarted:
            runtime_identity = await resolve_real_data_runtime_identity(
                restarted,
                runtime_settings=runtime_settings,
            )
            report = await build_real_data_readiness_report(
                restarted,
                runtime_identity,
            )
    finally:
        await restarted_engine.dispose()

    assert runtime_identity == _identity()
    assert report.bootstrap_complete is False
    assert report.ready_for_real_data is True
