from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from app.services.pre_prod_backup_service import BackupError
from app.services.pre_prod_restore_service import (
    database_identity,
    reconcile_inventories,
    restore_postgres_backup,
)


def _artifacts(path: Path) -> None:
    dump = b"postgres-custom-dump"
    (path / "database.dump").write_bytes(dump)
    (path / "backup-report.json").write_text(
        json.dumps({"sha256": hashlib.sha256(dump).hexdigest()}),
        encoding="utf-8",
    )


def _runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    if command[0] == "psql":
        stdout = kwargs["stdout"]
        stdout.write("0\n")
        stdout.flush()
    return subprocess.CompletedProcess(command, 0, "", "")


def _inventory(rows: int = 3) -> dict[str, object]:
    return {
        "schema_version": "pre-prod-inventory.v2",
        "tables": [
            {
                "name": "assets",
                "classification": "rebuildable",
                "row_count": rows,
            }
        ],
        "findings": [
            {"code": "orphan_asset_prices", "severity": "info", "count": 0}
        ],
        "totals": {"unclassified_tables": 0, "blocking_findings": 0},
    }


def test_restore_accepts_only_different_empty_database(tmp_path: Path) -> None:
    _artifacts(tmp_path)

    execution = restore_postgres_backup(
        artifact_directory=tmp_path,
        source_database_url="postgresql://user:secret@db:5432/sgi",
        target_database_url="postgresql://user:secret@db:5432/sgi_restore_test",
        runner=_runner,
    )

    assert execution.target.database == "sgi_restore_test"
    assert execution.sha256
    assert all("secret" not in command.command for command in execution.commands)


def test_restore_rejects_original_database(tmp_path: Path) -> None:
    _artifacts(tmp_path)

    with pytest.raises(BackupError, match="não pode ser a origem"):
        restore_postgres_backup(
            artifact_directory=tmp_path,
            source_database_url="postgresql://user:secret@db:5432/sgi",
            target_database_url="postgresql://user:secret@db:5432/sgi",
            runner=_runner,
        )


def test_restore_rejects_nonempty_target(tmp_path: Path) -> None:
    _artifacts(tmp_path)

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[0] == "psql":
            stdout = kwargs["stdout"]
            stdout.write("1\n")
            stdout.flush()
        return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(BackupError, match="deve estar vazio"):
        restore_postgres_backup(
            artifact_directory=tmp_path,
            source_database_url="postgresql://user:secret@db:5432/sgi",
            target_database_url="postgresql://user:secret@db:5432/sgi_restore_test",
            runner=runner,
        )


def test_reconciliation_requires_exact_counts_and_migrations() -> None:
    approved = reconcile_inventories(
        source_inventory=_inventory(),
        restored_inventory=_inventory(),
        source_migrations=["20260720_head"],
        restored_migrations=["20260720_head"],
    )
    divergent = reconcile_inventories(
        source_inventory=_inventory(),
        restored_inventory=_inventory(rows=2),
        source_migrations=["20260720_head"],
        restored_migrations=["older"],
    )

    assert approved.ok is True
    assert divergent.ok is False
    assert divergent.row_count_mismatches == [
        {"table": "assets", "source": 3, "restored": 2}
    ]
    assert database_identity("postgresql://u:p@DB/sgi").host == "db"
