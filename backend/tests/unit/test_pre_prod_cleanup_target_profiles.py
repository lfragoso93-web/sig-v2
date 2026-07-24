from __future__ import annotations

import pytest

from app.cli.pre_prod_isolated_cleanup import CliTargetError, _validate_target_profile
from app.services.pre_prod_isolated_cleanup_contract import (
    REQUIRED_ISOLATION_MARKER,
    REQUIRED_PRE_PROD_MARKER,
    CleanupDatabaseIdentity,
    IsolatedCleanupValidationError,
    IsolatedCleanupAuthorization,
    ApprovedCleanupPlanIdentity,
    CleanupExecutionConfirmation,
    ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
)

COMMIT_SHA = "a" * 40
PLAN_SHA = "b" * 64
RUN_ID = "20260724-100752"


def _database(
    database: str,
    *,
    host: str = "db",
    marker: str | None = None,
) -> CleanupDatabaseIdentity:
    return CleanupDatabaseIdentity(
        host=host,
        port=5432,
        database=database,
        isolation_marker=marker,
    )


def _authorization(
    source: CleanupDatabaseIdentity,
    target: CleanupDatabaseIdentity,
) -> IsolatedCleanupAuthorization:
    plan = ApprovedCleanupPlanIdentity(
        run_id=RUN_ID,
        branch="stable-15jun",
        commit_sha=COMMIT_SHA,
        plan_sha256=PLAN_SHA,
        cleanup_order=("transactions",),
    )
    confirmation = CleanupExecutionConfirmation(
        run_id=RUN_ID,
        target_database=target.database,
        commit_sha=COMMIT_SHA,
        plan_sha256=PLAN_SHA,
        confirmation=(
            f"CLEANUP {RUN_ID} ON {target.database} "
            f"AT {COMMIT_SHA} WITH {PLAN_SHA}"
        ),
    )
    return IsolatedCleanupAuthorization(
        schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
        plan=plan,
        source=source,
        target=target,
        confirmation=confirmation,
    )


def test_isolated_profile_requires_distinct_target() -> None:
    source = _database("sgi_pre_prod")
    target = _database(
        "sgi_cleanup_isolated",
        host="isolated-db",
        marker=REQUIRED_ISOLATION_MARKER,
    )

    _validate_target_profile(source, target)
    authorization = _authorization(source, target)

    assert authorization.target.isolation_marker == REQUIRED_ISOLATION_MARKER


def test_isolated_profile_rejects_source_identity() -> None:
    source = _database("sgi_pre_prod")
    target = _database("sgi_pre_prod", marker=REQUIRED_ISOLATION_MARKER)

    with pytest.raises(CliTargetError, match="diferente da origem"):
        _validate_target_profile(source, target)
    with pytest.raises(IsolatedCleanupValidationError, match="must be different"):
        _authorization(source, target)


def test_real_pre_prod_profile_requires_source_identity() -> None:
    source = _database("sgi_pre_prod")
    target = _database("sgi_pre_prod", marker=REQUIRED_PRE_PROD_MARKER)

    _validate_target_profile(source, target)
    authorization = _authorization(source, target)

    assert authorization.target.isolation_marker == REQUIRED_PRE_PROD_MARKER
    assert authorization.source.normalized_key == authorization.target.normalized_key


def test_real_pre_prod_profile_rejects_different_target() -> None:
    source = _database("sgi_pre_prod")
    target = _database(
        "sgi_other",
        host="other-db",
        marker=REQUIRED_PRE_PROD_MARKER,
    )

    with pytest.raises(CliTargetError, match="mesma identidade"):
        _validate_target_profile(source, target)
    with pytest.raises(IsolatedCleanupValidationError, match="source database identity"):
        _authorization(source, target)


def test_unknown_marker_is_rejected() -> None:
    source = _database("sgi_pre_prod")
    target = _database("sgi_pre_prod", marker="unsafe")

    with pytest.raises(CliTargetError, match="inválido"):
        _validate_target_profile(source, target)
    with pytest.raises(IsolatedCleanupValidationError, match="supported execution marker"):
        _authorization(source, target)
