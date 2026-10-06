"""Tests for the persisted readiness report."""

from datetime import datetime, timezone

import pytest
from app.models.real_data_certification_event import RealDataCertificationEvent
from app.services.real_data_certification_reader import (
    REAL_DATA_CERTIFICATION_SCHEMA_VERSION,
    RealDataCertificationIdentity,
    canonical_evidence_sha256,
)
from app.services.real_data_readiness_report import build_real_data_readiness_report
from app.services.system_readiness_service import (
    BootstrapReadiness,
    BootstrapReadinessState,
)
from sqlalchemy.ext.asyncio import AsyncSession


def _identity() -> RealDataCertificationIdentity:
    return RealDataCertificationIdentity(
        environment="pre-production",
        branch="stable-15jun",
        commit_sha="a" * 40,
        dataset_reference="dataset:2026-10-06",
        alembic_revision="20261005_real_data_certification",
        gate_issue_reference="#227",
        pull_request_reference="#362",
    )


def _promotion(identity: RealDataCertificationIdentity) -> RealDataCertificationEvent:
    evidence = {"checks": ["migration", "dataset"]}
    return RealDataCertificationEvent(
        event_key="promote-1",
        action="PROMOTE",
        schema_version=REAL_DATA_CERTIFICATION_SCHEMA_VERSION,
        environment=identity.environment,
        branch=identity.branch,
        commit_sha=identity.commit_sha,
        dataset_reference=identity.dataset_reference,
        alembic_revision=identity.alembic_revision,
        gate_issue_reference=identity.gate_issue_reference,
        pull_request_reference=identity.pull_request_reference,
        evidence_sha256=canonical_evidence_sha256(evidence),
        evidence_payload=evidence,
        actor="test-suite",
        reason="contract test",
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_valid_promotion_survives_process_bootstrap_reset(
    db: AsyncSession,
) -> None:
    identity = _identity()
    db.add(_promotion(identity))
    await db.flush()

    report = await build_real_data_readiness_report(
        db,
        identity,
        bootstrap=BootstrapReadiness(),
    )

    assert report.bootstrap_complete is False
    assert report.certification.ready_for_real_data is True
    assert report.eligible_for_activation is True
    assert report.activation_required is False
    assert report.ready_for_real_data is True


@pytest.mark.asyncio
async def test_valid_promotion_with_bootstrap_is_ready(
    db: AsyncSession,
) -> None:
    identity = _identity()
    db.add(_promotion(identity))
    await db.flush()

    report = await build_real_data_readiness_report(
        db,
        identity,
        bootstrap=BootstrapReadiness(state=BootstrapReadinessState.READY),
    )

    assert report.eligible_for_activation is True
    assert report.activation_required is False
    assert report.ready_for_real_data is True
    assert report.to_dict()["certification"]["status"] == "certified"


@pytest.mark.asyncio
async def test_missing_promotion_remains_fail_closed(db: AsyncSession) -> None:
    report = await build_real_data_readiness_report(
        db,
        _identity(),
        bootstrap=BootstrapReadiness(state=BootstrapReadinessState.READY),
    )

    assert report.eligible_for_activation is False
    assert report.activation_required is False
    assert report.ready_for_real_data is False
