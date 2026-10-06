from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from app.services.real_data_dataset_identity import (
    DatasetIdentityError,
    build_real_data_dataset_identity,
)


def _write_artifact(directory: Path) -> str:
    directory.mkdir()
    dump = b"complete-consistent-postgresql-dump"
    digest = hashlib.sha256(dump).hexdigest()
    (directory / "database.dump").write_bytes(dump)
    (directory / "database.dump.sha256").write_text(
        f"{digest}  database.dump\n", encoding="ascii"
    )
    (directory / "database.contents.txt").write_text(
        "TABLE public transactions\n", encoding="utf-8"
    )
    (directory / "origin-inventory.json").write_text(
        json.dumps(
            {
                "schema_version": "pre-prod-inventory.v2",
                "safety": {"read_only": True, "writes_executed": 0},
            }
        ),
        encoding="utf-8",
    )
    (directory / "backup-report.json").write_text(
        json.dumps(
            {
                "schema_version": "pre-prod-backup.v3",
                "run_id": "20261006-120000",
                "branch": "stable-15jun",
                "commit_sha": "a" * 40,
                "consistent_snapshot": True,
                "dump_file": "database.dump",
                "dump_size_bytes": len(dump),
                "sha256": digest,
                "inventory_file": "origin-inventory.json",
                "contents_file": "database.contents.txt",
                "safety": {
                    "source_database_writes_executed": 0,
                    "cleanup_executed": False,
                    "rebuild_executed": False,
                    "credentials_recorded": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return digest


def test_identity_uses_verified_complete_dump_checksum(tmp_path: Path) -> None:
    digest = _write_artifact(tmp_path / "backup")

    identity = build_real_data_dataset_identity(tmp_path / "backup")

    assert identity.schema_version == "real-data-dataset-identity.v1"
    assert identity.dataset_reference == f"pre-prod-backup.v3:sha256:{digest}"
    assert identity.backup_run_id == "20261006-120000"
    assert identity.database_writes_executed == 0


def test_identity_rejects_tampered_dump(tmp_path: Path) -> None:
    directory = tmp_path / "backup"
    _write_artifact(directory)
    (directory / "database.dump").write_bytes(b"tampered-dump-with-same-ish-size")

    with pytest.raises(DatasetIdentityError, match="size differs|checksum differs"):
        build_real_data_dataset_identity(directory)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("consistent_snapshot", False, "consistent snapshot"),
        ("schema_version", "pre-prod-backup.v2", "pre-prod-backup.v3"),
    ],
)
def test_identity_rejects_unsafe_backup_contract(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    directory = tmp_path / "backup"
    _write_artifact(directory)
    report_path = directory / "backup-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report[field] = value
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(DatasetIdentityError, match=message):
        build_real_data_dataset_identity(directory)


def test_identity_rejects_inventory_that_wrote_to_source(tmp_path: Path) -> None:
    directory = tmp_path / "backup"
    _write_artifact(directory)
    inventory_path = directory / "origin-inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["safety"]["writes_executed"] = 1
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    with pytest.raises(DatasetIdentityError, match="zero writes"):
        build_real_data_dataset_identity(directory)
