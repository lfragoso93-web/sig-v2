from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.pre_prod_cleanup_impact_contract import (
    IMPACT_REPORT_MODE,
    IMPACT_REPORT_SCHEMA_VERSION,
    CleanupImpactDependencyPlan,
    CleanupImpactSafety,
    CleanupImpactTable,
    CleanupImpactTotals,
    PreProdCleanupImpactReport,
)
from app.services.pre_prod_export_contract import ExportColumn
from app.services import pre_prod_export_service as service


class FakeSession:
    def __init__(self) -> None:
        self.executed: list[str] = []
        self.rollback_calls = 0
        self.close_calls = 0

    async def execute(self, statement, params=None):  # type: ignore[no-untyped-def]
        self.executed.append(str(statement))
        return []

    async def rollback(self) -> None:
        self.rollback_calls += 1

    async def close(self) -> None:
        self.close_calls += 1


def _cleanup_report(*, ok: bool = True) -> PreProdCleanupImpactReport:
    tables = [
        CleanupImpactTable(
            name="transactions",
            classification="export_before_cleanup",
            proposed_action="export_required",
            rationale="user-entered transactions",
            row_count=2,
            blocked=False,
        ),
        CleanupImpactTable(
            name="fixed_income_investments",
            classification="export_before_cleanup",
            proposed_action="export_required",
            rationale="user-entered fixed income",
            row_count=1,
            blocked=False,
        ),
        CleanupImpactTable(
            name="corporate_events",
            classification="export_before_cleanup",
            proposed_action="export_required",
            rationale="user-entered events",
            row_count=0,
            blocked=False,
        ),
    ]
    blockers = [] if ok else ["future_table"]
    if not ok:
        tables.append(
            CleanupImpactTable(
                name="future_table",
                classification="unclassified",
                proposed_action="block",
                rationale="unknown",
                row_count=0,
                blocked=True,
            )
        )
    return PreProdCleanupImpactReport(
        schema_version=IMPACT_REPORT_SCHEMA_VERSION,
        generated_at="2026-07-22T15:00:00+00:00",
        mode=IMPACT_REPORT_MODE,
        branch="stable-15jun",
        commit_sha="a" * 40,
        inventory_schema_version="pre-prod-inventory.v2",
        tables=tables,
        totals=CleanupImpactTotals.from_tables(tables),
        dependency_plan=CleanupImpactDependencyPlan(
            dependencies=[],
            cleanup_order=[
                "transactions",
                "fixed_income_investments",
                "corporate_events",
            ],
            rebuild_order=[],
            export_required_before_cleanup=[
                "corporate_events",
                "fixed_income_investments",
                "transactions",
            ],
            cycles=[],
        ),
        blockers=blockers,
        safety=CleanupImpactSafety(),
    )


def test_validate_gate_rejects_unapproved_report() -> None:
    with pytest.raises(ValueError, match="not approved"):
        service._validate_gate(_cleanup_report(ok=False))


def test_prepare_paths_rejects_existing_artifacts(tmp_path: Path) -> None:
    existing = tmp_path / "run-1" / "export"
    existing.mkdir(parents=True)

    with pytest.raises(FileExistsError, match="already exist"):
        service._prepare_paths(tmp_path, "run-1")


@pytest.mark.parametrize("run_id", ["", "../escape", "a/b", ".", ".."])
def test_prepare_paths_rejects_unsafe_run_id(tmp_path: Path, run_id: str) -> None:
    with pytest.raises(ValueError, match="safe directory"):
        service._prepare_paths(tmp_path, run_id)


def test_csv_value_is_deterministic() -> None:
    assert service._csv_value(None) == ""
    assert service._csv_value(True) == "true"
    assert service._csv_value({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert service._csv_value(b"\x00\xff") == "\\x00ff"


@pytest.mark.asyncio
async def test_build_export_writes_gate_tables_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    columns = [
        ExportColumn("id", "uuid", False, 1),
        ExportColumn("amount", "numeric", True, 2),
    ]
    rows_by_table = {
        "transactions": [["tx-1", "10.50"], ["tx-2", None]],
        "fixed_income_investments": [["rf-1", "1000.00"]],
        "corporate_events": [],
    }

    async def fake_read_columns(active_session, table_name):  # type: ignore[no-untyped-def]
        assert active_session is session
        return columns

    async def fake_write_table_csv(  # type: ignore[no-untyped-def]
        *, session: FakeSession, table_name: str, columns, destination: Path
    ) -> int:
        destination.parent.mkdir(parents=True, exist_ok=True)
        lines = ["id,amount\n"]
        lines.extend(
            f"{row[0]},{'' if row[1] is None else row[1]}\n"
            for row in rows_by_table[table_name]
        )
        destination.write_text("".join(lines), encoding="utf-8")
        return len(rows_by_table[table_name])

    monkeypatch.setattr(service, "_read_columns", fake_read_columns)
    monkeypatch.setattr(service, "_write_table_csv", fake_write_table_csv)

    manifest = await service.build_pre_prod_export(
        cleanup_impact=_cleanup_report(),
        branch="stable-15jun",
        commit_sha="b" * 40,
        run_id="20260722-120000",
        generated_at="2026-07-22T15:00:00+00:00",
        output_root=tmp_path,
        session=session,  # type: ignore[arg-type]
    )

    final_directory = tmp_path / "20260722-120000" / "export"
    assert final_directory.is_dir()
    assert not (tmp_path / "20260722-120000" / ".export.tmp").exists()
    assert manifest.total_rows == 3
    assert manifest.source.exported_tables == [
        "corporate_events",
        "fixed_income_investments",
        "transactions",
    ]
    assert [table.table_name for table in manifest.tables] == manifest.source.exported_tables
    assert all(table.data_sha256 != "0" * 64 for table in manifest.tables)
    assert all(table.schema_sha256 != "0" * 64 for table in manifest.tables)
    assert "REPEATABLE READ, READ ONLY" in session.executed[0]
    assert session.rollback_calls == 1
    assert session.close_calls == 0

    payload = json.loads((final_directory / "manifest.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "pre-prod-export.v1"
    assert payload["totals"] == {"tables": 3, "rows": 3, "bytes": manifest.total_bytes}
    for table_name in manifest.source.exported_tables:
        assert (final_directory / "tables" / f"{table_name}.csv").exists()


@pytest.mark.asyncio
async def test_build_export_removes_partial_directory_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()

    async def fake_read_columns(active_session, table_name):  # type: ignore[no-untyped-def]
        raise RuntimeError("introspection failed")

    monkeypatch.setattr(service, "_read_columns", fake_read_columns)

    with pytest.raises(RuntimeError, match="introspection failed"):
        await service.build_pre_prod_export(
            cleanup_impact=_cleanup_report(),
            branch="stable-15jun",
            commit_sha="b" * 40,
            run_id="failed-run",
            generated_at="2026-07-22T15:00:00+00:00",
            output_root=tmp_path,
            session=session,  # type: ignore[arg-type]
        )

    assert not (tmp_path / "failed-run" / ".export.tmp").exists()
    assert not (tmp_path / "failed-run" / "export").exists()
    assert session.rollback_calls == 1
