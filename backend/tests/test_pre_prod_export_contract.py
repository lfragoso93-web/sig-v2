from __future__ import annotations

from dataclasses import replace

import pytest

from app.services.pre_prod_export_contract import (
    EXPORT_CLASSIFICATION,
    EXPORT_FORMAT,
    EXPORT_MANIFEST_SCHEMA_VERSION,
    ExportColumn,
    ExportSafety,
    ExportSourceSnapshot,
    ExportTableArtifact,
    PreProdExportManifest,
)


def _columns() -> list[ExportColumn]:
    return [
        ExportColumn("id", "uuid", False, 1),
        ExportColumn("amount", "numeric(18,2)", True, 2),
    ]


def _table(name: str, *, rows: int = 2, path: str | None = None) -> ExportTableArtifact:
    return ExportTableArtifact(
        table_name=name,
        classification=EXPORT_CLASSIFICATION,
        row_count=rows,
        relative_path=path or f"tables/{name}.csv",
        format=EXPORT_FORMAT,
        byte_size=128,
        data_sha256="a" * 64,
        schema_sha256="b" * 64,
        columns=_columns(),
    )


def _source(tables: list[str]) -> ExportSourceSnapshot:
    return ExportSourceSnapshot(
        transaction_isolation="repeatable read",
        read_only=True,
        cleanup_impact_schema_version="pre-prod-cleanup-impact.v2",
        cleanup_impact_sha256="c" * 64,
        inventory_schema_version="pre-prod-inventory.v2",
        exported_tables=tables,
    )


def _manifest(tables: list[ExportTableArtifact]) -> PreProdExportManifest:
    return PreProdExportManifest(
        schema_version=EXPORT_MANIFEST_SCHEMA_VERSION,
        generated_at="2026-07-22T15:00:00+00:00",
        run_id="20260722-120000",
        branch="stable-15jun",
        commit_sha="d" * 40,
        source=_source([table.table_name for table in tables]),
        tables=tables,
        safety=ExportSafety(),
    )


def test_manifest_serializes_auditable_totals() -> None:
    manifest = _manifest(
        [
            _table("transactions", rows=3),
            _table("fixed_income_investments", rows=5),
            _table("corporate_events", rows=7),
        ]
    )

    assert manifest.total_rows == 15
    assert manifest.total_bytes == 384
    assert manifest.to_dict()["totals"] == {
        "tables": 3,
        "rows": 15,
        "bytes": 384,
    }


def test_manifest_tables_must_match_cleanup_export_gate() -> None:
    table = _table("transactions")

    with pytest.raises(ValueError, match="match source snapshot export gate"):
        replace(
            _manifest([table]),
            source=_source(["transactions", "corporate_events"]),
        )


def test_only_export_before_cleanup_classification_is_accepted() -> None:
    with pytest.raises(ValueError, match="only export_before_cleanup"):
        replace(_table("transactions"), classification="rebuildable")  # type: ignore[arg-type]


def test_snapshot_requires_repeatable_read_and_read_only() -> None:
    source = _source(["transactions"])

    with pytest.raises(ValueError, match="repeatable read"):
        replace(source, transaction_isolation="read committed")

    with pytest.raises(ValueError, match="read-only"):
        replace(source, read_only=False)


def test_safety_rejects_source_writes_cleanup_rebuild_and_overwrite() -> None:
    for kwargs in (
        {"source_read_only": False},
        {"source_writes_executed": 1},
        {"cleanup_executed": True},
        {"rebuild_executed": True},
        {"overwrite_performed": True},
    ):
        with pytest.raises(ValueError):
            ExportSafety(**kwargs)  # type: ignore[arg-type]


def test_checksums_must_be_full_sha256() -> None:
    with pytest.raises(ValueError, match="data_sha256"):
        replace(_table("transactions"), data_sha256="abc")

    with pytest.raises(ValueError, match="cleanup_impact_sha256"):
        replace(_source(["transactions"]), cleanup_impact_sha256="abc")


def test_artifact_path_must_be_relative_and_safe() -> None:
    with pytest.raises(ValueError, match="relative path"):
        _table("transactions", path="/tmp/transactions.csv")

    with pytest.raises(ValueError, match="traverse"):
        _table("transactions", path="../transactions.csv")


def test_column_metadata_preserves_order_and_uniqueness() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        ExportTableArtifact(
            table_name="transactions",
            classification=EXPORT_CLASSIFICATION,
            row_count=1,
            relative_path="tables/transactions.csv",
            format=EXPORT_FORMAT,
            byte_size=10,
            data_sha256="a" * 64,
            schema_sha256="b" * 64,
            columns=[ExportColumn("id", "uuid", False, 2)],
        )

    with pytest.raises(ValueError, match="unique"):
        ExportTableArtifact(
            table_name="transactions",
            classification=EXPORT_CLASSIFICATION,
            row_count=1,
            relative_path="tables/transactions.csv",
            format=EXPORT_FORMAT,
            byte_size=10,
            data_sha256="a" * 64,
            schema_sha256="b" * 64,
            columns=[
                ExportColumn("id", "uuid", False, 1),
                ExportColumn("id", "uuid", False, 2),
            ],
        )


def test_snapshot_rejects_duplicate_exported_tables() -> None:
    with pytest.raises(ValueError, match="snapshot exported tables must be unique"):
        _source(["transactions", "transactions"])


def test_manifest_rejects_duplicate_tables_and_paths() -> None:
    first = _table("transactions")
    duplicate = _table("transactions", path="tables/transactions-copy.csv")

    with pytest.raises(ValueError, match="manifest table names must be unique"):
        PreProdExportManifest(
            schema_version=EXPORT_MANIFEST_SCHEMA_VERSION,
            generated_at="2026-07-22T15:00:00+00:00",
            run_id="20260722-120000",
            branch="stable-15jun",
            commit_sha="d" * 40,
            source=_source(["transactions"]),
            tables=[first, duplicate],
            safety=ExportSafety(),
        )

    with pytest.raises(ValueError, match="artifact paths must be unique"):
        _manifest(
            [
                first,
                _table("corporate_events", path=first.relative_path),
            ]
        )
