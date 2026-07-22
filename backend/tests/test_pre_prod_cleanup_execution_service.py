from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.services.pre_prod_cleanup_execution_service import (
    CleanupExecutionValidationError,
    build_pre_prod_cleanup_execution_plan,
    publish_pre_prod_cleanup_execution_plan,
)


def _canonical_sha256(payload: dict) -> str:  # type: ignore[type-arg]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_artifacts(tmp_path: Path) -> tuple[Path, Path, Path, dict, dict]:  # type: ignore[type-arg]
    run_directory = tmp_path / "run-1"
    export_directory = run_directory / "export"
    tables_directory = export_directory / "tables"
    tables_directory.mkdir(parents=True)

    cleanup_impact = {
        "schema_version": "pre-prod-cleanup-impact.v2",
        "generated_at": "2026-07-22T20:00:00+00:00",
        "mode": "dry-run",
        "branch": "stable-15jun",
        "commit_sha": "a" * 40,
        "inventory_schema_version": "pre-prod-inventory.v2",
        "tables": [
            {
                "name": "transactions",
                "classification": "export_before_cleanup",
                "proposed_action": "export_required",
                "rationale": "user data",
                "row_count": 2,
                "blocked": False,
            },
            {
                "name": "daily_prices",
                "classification": "rebuildable",
                "proposed_action": "clean_and_rebuild",
                "rationale": "canonical source",
                "row_count": 5,
                "blocked": False,
            },
        ],
        "totals": {
            "tables": 2,
            "rows": 7,
            "preserved_tables": 0,
            "export_required_tables": 1,
            "rebuildable_tables": 1,
            "blocked_tables": 0,
        },
        "dependency_plan": {
            "dependencies": [],
            "cleanup_order": ["daily_prices", "transactions"],
            "rebuild_order": ["daily_prices"],
            "export_required_before_cleanup": ["transactions"],
            "cycles": [],
        },
        "blockers": [],
        "safety": {
            "read_only": True,
            "writes_executed": 0,
            "cleanup_executed": False,
            "rebuild_executed": False,
        },
        "ok": True,
    }
    cleanup_path = run_directory / "cleanup-impact.json"
    cleanup_path.write_text(
        json.dumps(cleanup_impact, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    csv_path = tables_directory / "transactions.csv"
    csv_path.write_text("id,amount\n1,10.00\n2,20.00\n", encoding="utf-8")
    csv_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "pre-prod-export.v1",
        "generated_at": "2026-07-22T20:00:00+00:00",
        "run_id": "run-1",
        "branch": "stable-15jun",
        "commit_sha": "a" * 40,
        "source": {
            "transaction_isolation": "repeatable read",
            "read_only": True,
            "cleanup_impact_schema_version": "pre-prod-cleanup-impact.v2",
            "cleanup_impact_sha256": _canonical_sha256(cleanup_impact),
            "inventory_schema_version": "pre-prod-inventory.v2",
            "exported_tables": ["transactions"],
        },
        "tables": [
            {
                "table_name": "transactions",
                "classification": "export_before_cleanup",
                "row_count": 2,
                "relative_path": "tables/transactions.csv",
                "format": "csv",
                "byte_size": csv_path.stat().st_size,
                "data_sha256": csv_sha256,
                "schema_sha256": "b" * 64,
                "columns": [
                    {
                        "name": "id",
                        "postgres_type": "integer",
                        "nullable": False,
                        "ordinal_position": 1,
                    }
                ],
            }
        ],
        "safety": {
            "source_read_only": True,
            "source_writes_executed": 0,
            "cleanup_executed": False,
            "rebuild_executed": False,
            "overwrite_performed": False,
        },
        "totals": {"tables": 1, "rows": 2, "bytes": csv_path.stat().st_size},
    }
    manifest_path = export_directory / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run_directory, cleanup_path, manifest_path, cleanup_impact, manifest


def _build(tmp_path: Path):  # type: ignore[no-untyped-def]
    run_directory, cleanup_path, manifest_path, _, _ = _write_artifacts(tmp_path)
    return build_pre_prod_cleanup_execution_plan(
        run_directory=run_directory,
        cleanup_impact_path=cleanup_path,
        manifest_path=manifest_path,
        run_id="run-1",
        branch="stable-15jun",
        commit_sha="a" * 40,
        generated_at="2026-07-22T21:00:00+00:00",
    )


def test_build_plan_validates_artifacts_and_dag(tmp_path: Path) -> None:
    plan = _build(tmp_path)

    assert plan.cleanup_order == ["daily_prices", "transactions"]
    assert plan.expected_rows_before == 7
    assert [table.cleanup_position for table in plan.tables] == [1, 2]
    assert {artifact.kind for artifact in plan.artifacts} == {
        "cleanup_impact",
        "export_manifest",
        "export_table",
    }
    assert plan.safety.plan_only is True
    assert plan.safety.database_writes_executed == 0


def test_build_plan_rejects_tampered_export(tmp_path: Path) -> None:
    run_directory, cleanup_path, manifest_path, _, _ = _write_artifacts(tmp_path)
    (run_directory / "export" / "tables" / "transactions.csv").write_text(
        "tampered\n", encoding="utf-8"
    )

    with pytest.raises(CleanupExecutionValidationError, match="checksum do CSV diverge"):
        build_pre_prod_cleanup_execution_plan(
            run_directory=run_directory,
            cleanup_impact_path=cleanup_path,
            manifest_path=manifest_path,
            run_id="run-1",
            branch="stable-15jun",
            commit_sha="a" * 40,
            generated_at="2026-07-22T21:00:00+00:00",
        )


def test_build_plan_rejects_tampered_cleanup_impact(tmp_path: Path) -> None:
    run_directory, cleanup_path, manifest_path, cleanup_impact, _ = _write_artifacts(
        tmp_path
    )
    cleanup_impact["tables"][0]["row_count"] = 99
    cleanup_path.write_text(json.dumps(cleanup_impact), encoding="utf-8")

    with pytest.raises(CleanupExecutionValidationError, match="checksum do cleanup impact"):
        build_pre_prod_cleanup_execution_plan(
            run_directory=run_directory,
            cleanup_impact_path=cleanup_path,
            manifest_path=manifest_path,
            run_id="run-1",
            branch="stable-15jun",
            commit_sha="a" * 40,
            generated_at="2026-07-22T21:00:00+00:00",
        )


def test_build_plan_rejects_identity_divergence(tmp_path: Path) -> None:
    run_directory, cleanup_path, manifest_path, _, _ = _write_artifacts(tmp_path)

    with pytest.raises(CleanupExecutionValidationError, match="run_id diverge"):
        build_pre_prod_cleanup_execution_plan(
            run_directory=run_directory,
            cleanup_impact_path=cleanup_path,
            manifest_path=manifest_path,
            run_id="another-run",
            branch="stable-15jun",
            commit_sha="a" * 40,
            generated_at="2026-07-22T21:00:00+00:00",
        )


def test_build_plan_rejects_artifact_outside_run_directory(tmp_path: Path) -> None:
    run_directory, _, manifest_path, _, _ = _write_artifacts(tmp_path)
    external = tmp_path / "outside.json"
    external.write_text("{}", encoding="utf-8")

    with pytest.raises(CleanupExecutionValidationError, match="fora do run_directory"):
        build_pre_prod_cleanup_execution_plan(
            run_directory=run_directory,
            cleanup_impact_path=external,
            manifest_path=manifest_path,
            run_id="run-1",
            branch="stable-15jun",
            commit_sha="a" * 40,
            generated_at="2026-07-22T21:00:00+00:00",
        )


def test_publish_plan_is_atomic_and_refuses_overwrite(tmp_path: Path) -> None:
    plan = _build(tmp_path)
    run_directory = tmp_path / "run-1"

    destination = publish_pre_prod_cleanup_execution_plan(
        plan=plan,
        run_directory=run_directory,
    )

    assert destination == run_directory / "cleanup" / "plan.json"
    assert destination.is_file()
    assert not (run_directory / "cleanup" / ".plan.json.tmp").exists()
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "pre-prod-cleanup-execution.v1"
    assert payload["safety"]["database_writes_executed"] == 0

    with pytest.raises(FileExistsError, match="already exists"):
        publish_pre_prod_cleanup_execution_plan(
            plan=plan,
            run_directory=run_directory,
        )
