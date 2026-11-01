"""Collect fail-closed evidence for an exact CI-approved production release."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis
from app.core.config import Settings, settings
from app.models.real_data_certification_event import RealDataCertificationEvent
from app.services.pre_prod_inventory_service import build_pre_prod_inventory
from app.services.real_data_certification_reader import (
    RealDataCertificationIdentity,
    RealDataCertificationStatus,
    read_real_data_certification,
)
from app.services.real_data_runtime_identity import (
    resolve_real_data_runtime_identity,
)

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_WORKFLOW_RUN_ID = re.compile(r"^[1-9][0-9]*$")


class RealDataReleaseCertificationError(RuntimeError):
    """A release did not meet the automatic promotion evidence contract."""


def _prior_identity(event: RealDataCertificationEvent) -> RealDataCertificationIdentity:
    return RealDataCertificationIdentity(
        environment=event.environment,
        branch=event.branch,
        commit_sha=event.commit_sha,
        dataset_reference=event.dataset_reference,
        alembic_revision=event.alembic_revision,
        gate_issue_reference=event.gate_issue_reference,
        pull_request_reference=event.pull_request_reference,
        schema_version=event.schema_version,
    )


async def build_release_promotion_evidence(
    session: AsyncSession,
    *,
    expected_sha: str,
    workflow_run_id: str,
    workflow_run_conclusion: str,
    workflow_run_event: str,
    workflow_run_branch: str,
    smoke_test_passed: bool,
    runtime_settings: Settings = settings,
) -> tuple[dict[str, Any] | None, bool]:
    """Prove release and production preconditions without writing to the DB."""

    if not _FULL_SHA.fullmatch(expected_sha):
        raise RealDataReleaseCertificationError(
            "CI-approved commit must be a full lowercase 40-character SHA"
        )
    if not _WORKFLOW_RUN_ID.fullmatch(workflow_run_id):
        raise RealDataReleaseCertificationError(
            "successful CI workflow run id is required"
        )
    if workflow_run_conclusion != "success":
        raise RealDataReleaseCertificationError(
            "CI workflow run must have succeeded"
        )
    if workflow_run_event != "push" or workflow_run_branch != "main":
        raise RealDataReleaseCertificationError(
            "CI provenance must be a push to main"
        )
    if not smoke_test_passed:
        raise RealDataReleaseCertificationError(
            "production health and smoke checks must pass before certification"
        )
    if runtime_settings.ENVIRONMENT.strip().lower() != "production":
        raise RealDataReleaseCertificationError(
            "automatic release certification is production-only"
        )
    if runtime_settings.APP_BRANCH.strip() != "main":
        raise RealDataReleaseCertificationError(
            "production runtime branch must be main"
        )
    if runtime_settings.APP_COMMIT_SHA.strip() != expected_sha:
        raise RealDataReleaseCertificationError(
            "running APP_COMMIT_SHA differs from the CI-approved SHA"
        )

    # Use a consistent, read-only view for inventory and certification history.
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        )
    await session.execute(text("SELECT 1"))
    runtime_identity = await resolve_real_data_runtime_identity(
        session,
        runtime_settings=runtime_settings,
    )

    redis_client = await get_redis()
    if redis_client is None:
        raise RealDataReleaseCertificationError(
            "Redis is unavailable; release certification is blocked"
        )
    try:
        await redis_client.ping()
    except Exception as exc:
        raise RealDataReleaseCertificationError(
            f"Redis health check failed: {type(exc).__name__}"
        ) from exc

    inventory = await build_pre_prod_inventory(
        session,
        rollback_supplied_session=False,
    )
    if (
        inventory.totals["blocking_findings"] != 0
        or inventory.totals["unclassified_tables"] != 0
    ):
        raise RealDataReleaseCertificationError(
            "production inventory contains blocking or unclassified findings"
        )

    latest_result = await session.execute(
        select(RealDataCertificationEvent)
        .where(RealDataCertificationEvent.environment == runtime_identity.environment)
        .order_by(
            RealDataCertificationEvent.created_at.desc(),
            RealDataCertificationEvent.id.desc(),
        )
        .limit(1)
    )
    previous_event = latest_result.scalar_one_or_none()
    if previous_event is None or previous_event.action != "PROMOTE":
        raise RealDataReleaseCertificationError(
            "a valid previous promotion is required to anchor the production dataset"
        )
    current_state = await read_real_data_certification(session, runtime_identity)
    if current_state.status is RealDataCertificationStatus.CERTIFIED:
        return None, True
    previous_state = await read_real_data_certification(
        session,
        _prior_identity(previous_event),
    )
    if previous_state.status is not RealDataCertificationStatus.CERTIFIED:
        raise RealDataReleaseCertificationError(
            "previous production certification history is not valid"
        )
    if previous_event.dataset_reference != runtime_identity.dataset_reference:
        raise RealDataReleaseCertificationError(
            "configured dataset reference differs from the last valid certification"
        )

    evidence: dict[str, Any] = {
        "schema_version": "real-data-promotion-evidence.v1",
        "status": "GO",
        "dataset_reference": runtime_identity.dataset_reference,
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
        "release_provenance": {
            "source": "github-actions-successful-main-push",
            "workflow_run_id": workflow_run_id,
            "workflow_run_conclusion": workflow_run_conclusion,
            "workflow_run_event": workflow_run_event,
            "workflow_run_branch": workflow_run_branch,
            "commit_sha": expected_sha,
            "smoke_test_passed": smoke_test_passed,
            "alembic_revision": runtime_identity.alembic_revision,
            "previous_event_id": previous_event.id,
            "previous_event_key": previous_event.event_key,
            "inventory_tables": inventory.totals["tables"],
            "inventory_unclassified_tables": inventory.totals[
                "unclassified_tables"
            ],
            "inventory_blocking_findings": inventory.totals[
                "blocking_findings"
            ],
        },
    }
    return evidence, False
