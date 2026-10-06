"""Resolve the runtime identity independently from certification events."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.services.real_data_certification_contract import (
    REQUIRED_GATE_ISSUE_REFERENCE,
    REQUIRED_PULL_REQUEST_REFERENCE,
)
from app.services.real_data_certification_reader import RealDataCertificationIdentity


class RealDataRuntimeIdentityError(RuntimeError):
    """The running process cannot prove its immutable target identity."""


def _required_runtime_value(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized or normalized.lower() == "unknown":
        raise RealDataRuntimeIdentityError(f"runtime identity missing {field}")
    return normalized


def _runtime_commit_sha(value: str) -> str:
    normalized = _required_runtime_value(value, "APP_COMMIT_SHA").lower()
    if len(normalized) != 40 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise RealDataRuntimeIdentityError(
            "runtime identity APP_COMMIT_SHA must be a full hexadecimal SHA"
        )
    return normalized


async def resolve_real_data_runtime_identity(
    session: AsyncSession,
    *,
    runtime_settings: Settings = settings,
) -> RealDataCertificationIdentity:
    """Build the expected identity from runtime config and the live schema."""

    environment = _required_runtime_value(
        runtime_settings.ENVIRONMENT,
        "ENVIRONMENT",
    )
    branch = _required_runtime_value(runtime_settings.APP_BRANCH, "APP_BRANCH")
    commit_sha = _runtime_commit_sha(runtime_settings.APP_COMMIT_SHA)
    dataset_reference = _required_runtime_value(
        runtime_settings.REAL_DATASET_REFERENCE,
        "REAL_DATASET_REFERENCE",
    )

    try:
        result = await session.execute(
            text("SELECT version_num FROM alembic_version ORDER BY version_num")
        )
        revisions = [str(value).strip() for value in result.scalars().all()]
    except SQLAlchemyError as exc:
        raise RealDataRuntimeIdentityError(
            f"runtime identity schema read failed: {type(exc).__name__}"
        ) from exc

    if len(revisions) != 1 or not revisions[0]:
        raise RealDataRuntimeIdentityError(
            "runtime identity requires exactly one Alembic revision"
        )

    return RealDataCertificationIdentity(
        environment=environment,
        branch=branch,
        commit_sha=commit_sha,
        dataset_reference=dataset_reference,
        alembic_revision=revisions[0],
        gate_issue_reference=REQUIRED_GATE_ISSUE_REFERENCE,
        pull_request_reference=REQUIRED_PULL_REQUEST_REFERENCE,
    )
