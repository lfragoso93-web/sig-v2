from __future__ import annotations

import pytest

from app.services.pre_prod_cleanup_execution_contract import (
    CLEANUP_EXECUTION_MODE,
    CLEANUP_EXECUTION_SCHEMA_VERSION,
    CleanupExecutionArtifact,
    CleanupExecutionSafety,
    CleanupExecutionTable,
    PreProdCleanupExecutionPlan,
)


def _artifact(kind: str, relative_path: str) -> CleanupExecutionArtifact:
    return CleanupExecutionArtifact(
        kind=kind,  # type: ignore[arg-type]
        schema_version={
            "cleanup_impact": "pre-prod-cleanup-impact.v2",
            "export_manifest": "pre-prod-export.v1",
            "export_table": "pre-prod-export-table.v1",
        }[kind],
        relative_path=relative_path,
        sha256="a" * 64,
    )


def _plan(**overrides) -> PreProdCleanupExecutionPlan:  # type: ignore[no-untyped-def]
    values = {
        "schema_version": CLEANUP_EXECUTION_SCHEMA_VERSION,
        "generated_at": "2026-07-22T20:00:00+00:00",
        "mode": CLEANUP_EXECUTION_MODE,
        "run_id": "20260722-170000",
        "branch": "stable-15jun",
        "commit_sha": "b" * 40,
        "cleanup_impact_sha256": "c" * 64,
        "export_manifest_sha256": "d" * 64,
        "artifacts": [
            _artifact("cleanup_impact", "cleanup-impact/report.json"),
            _artifact("export_manifest", "export/manifest.json"),
            _artifact("export_table", "export/tables/transactions.csv"),
            _artifact("export_table", "export/tables/assets.csv"),
        ],
        "tables": [
            CleanupExecutionTable(
                name="transactions",
                classification="export_before_cleanup",
                expected_rows_before=10,
                cleanup_position=1,
            ),
            CleanupExecutionTable(
                name="assets",
                classification="export_before_cleanup",
                expected_rows_before=4,
                cleanup_position=2,
            ),
            CleanupExecutionTable(
                name="prices",
                classification="rebuildable",
                expected_rows_before=100,
                cleanup_position=3,
            ),
        ],
        "cleanup_order": ["transactions", "assets", "prices"],
        "blockers": [],
        "safety": CleanupExecutionSafety(),
    }
    values.update(overrides)
    return PreProdCleanupExecutionPlan(**values)


def test_plan_serializes_totals_and_preserves_order() -> None:
    plan = _plan()

    assert plan.expected_rows_before == 114
    assert plan.to_dict()["totals"] == {
        "artifacts": 4,
        "tables": 3,
        "expected_rows_before": 114,
    }
    assert plan.cleanup_order == ["transactions", "assets", "prices"]
    assert plan.safety.database_writes_executed == 0
    assert plan.safety.cleanup_executed is False


def test_plan_rejects_wrong_branch() -> None:
    with pytest.raises(ValueError, match="stable-15jun"):
        _plan(branch="main")


def test_plan_rejects_unsafe_run_id() -> None:
    with pytest.raises(ValueError, match="run_id"):
        _plan(run_id="../escape")


def test_plan_rejects_invalid_checksum() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        _plan(export_manifest_sha256="invalid")


def test_plan_rejects_missing_required_artifact() -> None:
    artifacts = [
        _artifact("cleanup_impact", "cleanup-impact/report.json"),
        _artifact("export_table", "export/tables/transactions.csv"),
        _artifact("export_table", "export/tables/assets.csv"),
    ]

    with pytest.raises(ValueError, match="export manifest"):
        _plan(artifacts=artifacts)


def test_plan_rejects_cleanup_order_divergence() -> None:
    with pytest.raises(ValueError, match="cleanup_order"):
        _plan(cleanup_order=["assets", "transactions", "prices"])


def test_plan_rejects_export_artifact_gate_divergence() -> None:
    artifacts = [
        _artifact("cleanup_impact", "cleanup-impact/report.json"),
        _artifact("export_manifest", "export/manifest.json"),
        _artifact("export_table", "export/tables/transactions.csv"),
    ]

    with pytest.raises(ValueError, match="export table artifacts"):
        _plan(artifacts=artifacts)


def test_plan_rejects_blockers() -> None:
    with pytest.raises(ValueError, match="cannot contain blockers"):
        _plan(blockers=["referential_cycle:prices->assets"])


def test_safety_rejects_any_database_write() -> None:
    with pytest.raises(ValueError, match="database writes"):
        CleanupExecutionSafety(database_writes_executed=1)


def test_safety_rejects_cleanup_execution() -> None:
    with pytest.raises(ValueError, match="cannot execute cleanup"):
        CleanupExecutionSafety(cleanup_executed=True)
