"""Transactional persistence boundary for real-data certification events."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, replace
from typing import Any, cast

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.real_data_certification_event import RealDataCertificationEvent
from app.services.real_data_certification_contract import (
    RealDataCertificationAction,
    RealDataCertificationPlan,
    RealDataCertificationValidationError,
    build_real_data_certification_plan,
    validate_execution_confirmation,
)
from app.services.real_data_certification_reader import RealDataCertificationIdentity

_LOCK_NAMESPACE = "sgi-v2:real-data-certification"


class RealDataCertificationExecutionError(RuntimeError):
    """Execution stopped without authorizing a certification write."""


class StaleRealDataCertificationPlanError(RealDataCertificationExecutionError):
    """The persisted chain changed after the dry-run plan was created."""


@dataclass(frozen=True)
class RealDataCertificationExecutionResult:
    action: RealDataCertificationAction
    event_id: int
    event_key: str
    idempotent: bool
    dry_run: bool
    database_writes_executed: int
    transaction_committed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


def _lock_key(environment: str) -> int:
    material = f"{_LOCK_NAMESPACE}:{environment}".encode()
    unsigned = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return unsigned if unsigned < 2**63 else unsigned - 2**64


async def _acquire_environment_lock(
    session: AsyncSession,
    environment: str,
) -> None:
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _lock_key(environment)},
        )


async def _latest_event(
    session: AsyncSession,
    environment: str,
    *,
    for_update: bool,
) -> RealDataCertificationEvent | None:
    statement = (
        select(RealDataCertificationEvent)
        .where(RealDataCertificationEvent.environment == environment)
        .order_by(
            RealDataCertificationEvent.created_at.desc(),
            RealDataCertificationEvent.id.desc(),
        )
        .limit(1)
    )
    if for_update:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def prepare_real_data_certification_plan(
    session: AsyncSession,
    *,
    action: RealDataCertificationAction,
    identity: RealDataCertificationIdentity,
    evidence_payload: dict[str, Any],
    actor: str,
    reason: str,
) -> RealDataCertificationPlan:
    """Build a dry-run plan bound to the current end of the persisted chain."""

    latest = await _latest_event(session, identity.environment, for_update=False)
    return build_real_data_certification_plan(
        action=action,
        identity=identity,
        evidence_payload=evidence_payload,
        actor=actor,
        reason=reason,
        supersedes_event_id=cast(int, latest.id) if latest is not None else None,
        supersedes_event_key=(
            cast(str, latest.event_key) if latest is not None else None
        ),
    )


def _event_matches_plan(
    event: RealDataCertificationEvent,
    plan: RealDataCertificationPlan,
) -> bool:
    identity = plan.identity
    return all(
        (
            event.action == plan.action.value,
            event.schema_version == identity.schema_version,
            event.environment == identity.environment,
            event.branch == identity.branch,
            event.commit_sha == identity.commit_sha,
            event.dataset_reference == identity.dataset_reference,
            event.alembic_revision == identity.alembic_revision,
            event.gate_issue_reference == identity.gate_issue_reference,
            event.pull_request_reference == identity.pull_request_reference,
            event.evidence_sha256 == plan.evidence_sha256,
            event.evidence_payload == dict(plan.evidence_payload),
        )
    )


async def execute_real_data_certification_plan(
    session: AsyncSession,
    *,
    plan: RealDataCertificationPlan,
    confirmation: str,
) -> RealDataCertificationExecutionResult:
    """Append one event after revalidating the approved dry-run plan.

    The caller owns commit/rollback. This function flushes at most one new row
    and never mutates financial tables or the in-memory readiness projection.
    """

    validate_execution_confirmation(plan, confirmation)
    if not plan.dry_run or plan.database_writes_executed != 0:
        raise RealDataCertificationValidationError(
            "executor accepts only an unchanged dry-run plan"
        )

    await _acquire_environment_lock(session, plan.identity.environment)
    latest = await _latest_event(
        session,
        plan.identity.environment,
        for_update=True,
    )

    if latest is not None and _event_matches_plan(latest, plan):
        return RealDataCertificationExecutionResult(
            action=plan.action,
            event_id=cast(int, latest.id),
            event_key=cast(str, latest.event_key),
            idempotent=True,
            dry_run=False,
            database_writes_executed=0,
        )

    latest_id = cast(int, latest.id) if latest is not None else None
    latest_key = cast(str, latest.event_key) if latest is not None else None
    if (
        latest_id != plan.supersedes_event_id
        or latest_key != plan.supersedes_event_key
    ):
        raise StaleRealDataCertificationPlanError(
            "persisted certification chain changed after dry-run"
        )

    identity = plan.identity
    event = RealDataCertificationEvent(
        event_key=plan.event_key,
        action=plan.action.value,
        schema_version=identity.schema_version,
        environment=identity.environment,
        branch=identity.branch,
        commit_sha=identity.commit_sha,
        dataset_reference=identity.dataset_reference,
        alembic_revision=identity.alembic_revision,
        gate_issue_reference=identity.gate_issue_reference,
        pull_request_reference=identity.pull_request_reference,
        evidence_sha256=plan.evidence_sha256,
        evidence_payload=dict(plan.evidence_payload),
        actor=plan.actor,
        reason=plan.reason,
        supersedes_event_id=plan.supersedes_event_id,
    )
    session.add(event)
    await session.flush()

    return RealDataCertificationExecutionResult(
        action=plan.action,
        event_id=cast(int, event.id),
        event_key=plan.event_key,
        idempotent=False,
        dry_run=False,
        database_writes_executed=1,
    )


def mark_certification_result_committed(
    result: RealDataCertificationExecutionResult,
) -> RealDataCertificationExecutionResult:
    """Return the post-commit representation used by an explicit caller."""

    return replace(result, transaction_committed=True)
