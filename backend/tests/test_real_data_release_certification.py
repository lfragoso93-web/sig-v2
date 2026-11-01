from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.real_data_certification_event import RealDataCertificationEvent
from app.services.real_data_certification_reader import (
    REAL_DATA_CERTIFICATION_SCHEMA_VERSION,
    canonical_evidence_sha256,
)
from app.services.real_data_release_certification import (
    RealDataReleaseCertificationError,
    build_release_promotion_evidence,
)

SHA = "a" * 40
DATASET = "pre-prod-backup.v3:sha256:" + "b" * 64


def _production_settings(**overrides: str) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "APP_BRANCH": "main",
        "APP_COMMIT_SHA": SHA,
        "REAL_DATASET_REFERENCE": DATASET,
        "SECRET_KEY": "strong-test-secret-key-" + "x" * 32,
        "SUPERADMIN_PASSWORD": "StrongAdmin!456",
    }
    values.update(overrides)
    return Settings(**values)


async def _add_prior_promotion(
    db: AsyncSession,
    *,
    branch: str = "stable-15jun",
    commit_sha: str = "c" * 40,
    alembic_revision: str = "previous_revision",
) -> None:
    evidence = {
        "schema_version": "real-data-promotion-evidence.v1",
        "status": "GO",
        "dataset_reference": DATASET,
        "ready_for_real_data": False,
        "database_writes_executed": 0,
        "blockers": [],
        "warnings": [],
        "checks": {
            "readiness": True,
            "inventory": True,
            "services": True,
            "schema": True,
            "dataset_identity": True,
        },
    }
    db.add(
        RealDataCertificationEvent(
            event_key="previous-promotion-key",
            action="PROMOTE",
            schema_version=REAL_DATA_CERTIFICATION_SCHEMA_VERSION,
            environment="production",
            branch=branch,
            commit_sha=commit_sha,
            dataset_reference=DATASET,
            alembic_revision=alembic_revision,
            gate_issue_reference="#227",
            pull_request_reference="#362",
            evidence_sha256=canonical_evidence_sha256(evidence),
            evidence_payload=evidence,
            actor="test-suite",
            reason="previously approved dataset anchor",
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_release_evidence_requires_ci_runtime_and_valid_dataset_anchor(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await db.execute(
        text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)")
    )
    await db.execute(
        text("INSERT INTO alembic_version (version_num) VALUES ('release_revision')")
    )
    await _add_prior_promotion(db)
    monkeypatch.setattr(
        "app.services.real_data_release_certification.get_redis",
        AsyncMock(return_value=SimpleNamespace(ping=AsyncMock())),
    )
    monkeypatch.setattr(
        "app.services.real_data_release_certification.build_pre_prod_inventory",
        AsyncMock(
            return_value=SimpleNamespace(
                totals={
                    "blocking_findings": 0,
                    "unclassified_tables": 0,
                    "tables": 42,
                }
            )
        ),
    )

    evidence, already_certified = await build_release_promotion_evidence(
        db,
        expected_sha=SHA,
        workflow_run_id="123456789",
        workflow_run_conclusion="success",
        workflow_run_event="push",
        workflow_run_branch="main",
        smoke_test_passed=True,
        runtime_settings=_production_settings(),
    )

    assert already_certified is False
    assert evidence is not None
    assert evidence["status"] == "GO"
    assert evidence["ready_for_real_data"] is False
    assert evidence["database_writes_executed"] == 0
    assert all(evidence["checks"].values())
    assert evidence["release_provenance"]["commit_sha"] == SHA
    assert evidence["release_provenance"]["workflow_run_conclusion"] == "success"
    assert evidence["release_provenance"]["previous_event_key"] == (
        "previous-promotion-key"
    )


@pytest.mark.asyncio
async def test_release_evidence_rejects_changed_dataset_reference(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await db.execute(
        text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)")
    )
    await db.execute(
        text("INSERT INTO alembic_version (version_num) VALUES ('release_revision')")
    )
    await _add_prior_promotion(db)
    monkeypatch.setattr(
        "app.services.real_data_release_certification.get_redis",
        AsyncMock(return_value=SimpleNamespace(ping=AsyncMock())),
    )
    monkeypatch.setattr(
        "app.services.real_data_release_certification.build_pre_prod_inventory",
        AsyncMock(
            return_value=SimpleNamespace(
                totals={
                    "blocking_findings": 0,
                    "unclassified_tables": 0,
                    "tables": 42,
                }
            )
        ),
    )

    with pytest.raises(RealDataReleaseCertificationError, match="dataset reference"):
        await build_release_promotion_evidence(
            db,
            expected_sha=SHA,
            workflow_run_id="123456789",
            workflow_run_conclusion="success",
            workflow_run_event="push",
            workflow_run_branch="main",
            smoke_test_passed=True,
            runtime_settings=_production_settings(
                REAL_DATASET_REFERENCE="pre-prod-backup.v3:sha256:" + "d" * 64
            ),
        )


@pytest.mark.asyncio
async def test_release_evidence_is_idempotent_for_already_certified_sha(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await db.execute(
        text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)")
    )
    await db.execute(
        text("INSERT INTO alembic_version (version_num) VALUES ('release_revision')")
    )
    await _add_prior_promotion(
        db,
        branch="main",
        commit_sha=SHA,
        alembic_revision="release_revision",
    )
    monkeypatch.setattr(
        "app.services.real_data_release_certification.get_redis",
        AsyncMock(return_value=SimpleNamespace(ping=AsyncMock())),
    )
    monkeypatch.setattr(
        "app.services.real_data_release_certification.build_pre_prod_inventory",
        AsyncMock(
            return_value=SimpleNamespace(
                totals={
                    "blocking_findings": 0,
                    "unclassified_tables": 0,
                    "tables": 42,
                }
            )
        ),
    )

    evidence, already_certified = await build_release_promotion_evidence(
        db,
        expected_sha=SHA,
        workflow_run_id="123456789",
        workflow_run_conclusion="success",
        workflow_run_event="push",
        workflow_run_branch="main",
        smoke_test_passed=True,
        runtime_settings=_production_settings(),
    )

    assert evidence is None
    assert already_certified is True


@pytest.mark.asyncio
async def test_release_evidence_rejects_incomplete_smoke_checks(
    db: AsyncSession,
) -> None:
    with pytest.raises(RealDataReleaseCertificationError, match="smoke checks"):
        await build_release_promotion_evidence(
            db,
            expected_sha=SHA,
            workflow_run_id="123456789",
            workflow_run_conclusion="success",
            workflow_run_event="push",
            workflow_run_branch="main",
            smoke_test_passed=False,
            runtime_settings=_production_settings(),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("conclusion", "event", "branch", "error"),
    [
        ("failure", "push", "main", "must have succeeded"),
        ("success", "workflow_dispatch", "main", "push to main"),
        ("success", "push", "stable-15jun", "push to main"),
    ],
)
async def test_release_evidence_rejects_unapproved_ci_provenance(
    db: AsyncSession,
    conclusion: str,
    event: str,
    branch: str,
    error: str,
) -> None:
    with pytest.raises(RealDataReleaseCertificationError, match=error):
        await build_release_promotion_evidence(
            db,
            expected_sha=SHA,
            workflow_run_id="123456789",
            workflow_run_conclusion=conclusion,
            workflow_run_event=event,
            workflow_run_branch=branch,
            smoke_test_passed=True,
            runtime_settings=_production_settings(),
        )
