"""Fail-closed tests for the independent runtime identity resolver."""

import pytest
from app.core.config import Settings
from app.services.real_data_runtime_identity import (
    RealDataRuntimeIdentityError,
    resolve_real_data_runtime_identity,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _settings(**overrides: str) -> Settings:
    values = {
        "ENVIRONMENT": "local-canonical",
        "APP_BRANCH": "stable-15jun",
        "APP_COMMIT_SHA": "a" * 40,
        "REAL_DATASET_REFERENCE": "dataset:2026-10-06",
    }
    values.update(overrides)
    return Settings.model_validate(values)


async def _alembic_revision(db: AsyncSession, revision: str = "revision_head") -> None:
    await db.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
    await db.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
        {"revision": revision},
    )


@pytest.mark.asyncio
async def test_runtime_identity_combines_config_and_live_schema(
    db: AsyncSession,
) -> None:
    await _alembic_revision(db)

    identity = await resolve_real_data_runtime_identity(
        db,
        runtime_settings=_settings(),
    )

    assert identity.environment == "local-canonical"
    assert identity.branch == "stable-15jun"
    assert identity.commit_sha == "a" * 40
    assert identity.dataset_reference == "dataset:2026-10-06"
    assert identity.alembic_revision == "revision_head"
    assert identity.gate_issue_reference == "#227"
    assert identity.pull_request_reference == "#362"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("ENVIRONMENT", "", "ENVIRONMENT"),
        ("APP_BRANCH", "unknown", "APP_BRANCH"),
        ("APP_COMMIT_SHA", "short", "full hexadecimal SHA"),
        ("REAL_DATASET_REFERENCE", "", "REAL_DATASET_REFERENCE"),
    ],
)
async def test_runtime_identity_rejects_missing_or_invalid_config_before_db_read(
    db: AsyncSession,
    field: str,
    value: str,
    message: str,
) -> None:
    with pytest.raises(RealDataRuntimeIdentityError, match=message):
        await resolve_real_data_runtime_identity(
            db,
            runtime_settings=_settings(**{field: value}),
        )


@pytest.mark.asyncio
async def test_runtime_identity_fails_closed_when_schema_is_unavailable(
    db: AsyncSession,
) -> None:
    with pytest.raises(RealDataRuntimeIdentityError, match="schema read failed"):
        await resolve_real_data_runtime_identity(
            db,
            runtime_settings=_settings(),
        )


@pytest.mark.asyncio
async def test_runtime_identity_rejects_ambiguous_alembic_heads(
    db: AsyncSession,
) -> None:
    await _alembic_revision(db, "first")
    await db.execute(
        text("INSERT INTO alembic_version (version_num) VALUES ('second')")
    )

    with pytest.raises(RealDataRuntimeIdentityError, match="exactly one"):
        await resolve_real_data_runtime_identity(
            db,
            runtime_settings=_settings(),
        )
