"""Canonical identity for a validated, consistent pre-production backup."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.services.pre_prod_backup_service import (
    BACKUP_REPORT_SCHEMA_VERSION,
    sha256_file,
)

DATASET_IDENTITY_SCHEMA_VERSION = "real-data-dataset-identity.v1"
DATASET_REFERENCE_PREFIX = f"{BACKUP_REPORT_SCHEMA_VERSION}:sha256:"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DatasetIdentityError(RuntimeError):
    """A backup artifact cannot safely identify a certification dataset."""


@dataclass(frozen=True)
class RealDataDatasetIdentity:
    schema_version: str
    dataset_reference: str
    backup_schema_version: str
    backup_run_id: str
    backup_branch: str
    backup_commit_sha: str
    dump_sha256: str
    dump_size_bytes: int
    inventory_schema_version: str
    database_writes_executed: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetIdentityError(
            f"unable to load {label}: {type(exc).__name__}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise DatasetIdentityError(f"{label} root must be an object")
    return dict(payload)


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise DatasetIdentityError(f"backup report {field} must be non-empty text")
    return value.strip()


def _artifact_file(directory: Path, filename: str, label: str) -> Path:
    if Path(filename).name != filename:
        raise DatasetIdentityError(f"backup report {label} must be a filename")
    path = directory / filename
    if not path.is_file():
        raise DatasetIdentityError(f"backup artifact is missing {filename}")
    return path


def build_real_data_dataset_identity(
    artifact_directory: Path,
) -> RealDataDatasetIdentity:
    """Validate a v3 backup and derive its immutable dataset reference."""
    directory = artifact_directory.resolve()
    if not directory.is_dir():
        raise DatasetIdentityError("backup artifact directory does not exist")

    report = _load_object(directory / "backup-report.json", "backup report")
    if report.get("schema_version") != BACKUP_REPORT_SCHEMA_VERSION:
        raise DatasetIdentityError(
            f"backup report must use {BACKUP_REPORT_SCHEMA_VERSION}"
        )
    if report.get("consistent_snapshot") is not True:
        raise DatasetIdentityError("backup report must declare a consistent snapshot")

    safety = report.get("safety")
    if not isinstance(safety, Mapping):
        raise DatasetIdentityError("backup report safety must be an object")
    expected_safety = {
        "source_database_writes_executed": 0,
        "cleanup_executed": False,
        "rebuild_executed": False,
        "credentials_recorded": False,
    }
    for field, expected in expected_safety.items():
        if safety.get(field) != expected:
            raise DatasetIdentityError(
                f"backup report safety.{field} must be {expected!r}"
            )

    dump_name = _required_text(report, "dump_file")
    dump_path = _artifact_file(directory, dump_name, "dump_file")
    reported_size = report.get("dump_size_bytes")
    if not isinstance(reported_size, int) or reported_size <= 0:
        raise DatasetIdentityError("backup report dump_size_bytes must be positive")
    if dump_path.stat().st_size != reported_size:
        raise DatasetIdentityError("database dump size differs from backup report")

    reported_sha256 = _required_text(report, "sha256")
    if not _SHA256_PATTERN.fullmatch(reported_sha256):
        raise DatasetIdentityError("backup report sha256 is invalid")
    actual_sha256 = sha256_file(dump_path)
    if actual_sha256 != reported_sha256:
        raise DatasetIdentityError("database dump checksum differs from backup report")

    checksum_path = _artifact_file(
        directory, "database.dump.sha256", "checksum file"
    )
    try:
        checksum_manifest = checksum_path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise DatasetIdentityError(
            f"unable to load checksum manifest: {type(exc).__name__}"
        ) from exc
    if checksum_manifest != f"{reported_sha256}  {dump_name}":
        raise DatasetIdentityError("checksum manifest differs from backup report")

    inventory_name = _required_text(report, "inventory_file")
    inventory = _load_object(
        _artifact_file(directory, inventory_name, "inventory_file"),
        "origin inventory",
    )
    inventory_safety = inventory.get("safety")
    if not isinstance(inventory_safety, Mapping):
        raise DatasetIdentityError("origin inventory safety must be an object")
    if inventory_safety.get("read_only") is not True:
        raise DatasetIdentityError("origin inventory must be read-only")
    if inventory_safety.get("writes_executed") != 0:
        raise DatasetIdentityError("origin inventory must report zero writes")
    inventory_schema = inventory.get("schema_version")
    if inventory_schema != "pre-prod-inventory.v2":
        raise DatasetIdentityError(
            "origin inventory must use pre-prod-inventory.v2"
        )

    contents_name = _required_text(report, "contents_file")
    contents_path = _artifact_file(directory, contents_name, "contents_file")
    if contents_path.stat().st_size <= 0:
        raise DatasetIdentityError("database contents listing must be non-empty")

    return RealDataDatasetIdentity(
        schema_version=DATASET_IDENTITY_SCHEMA_VERSION,
        dataset_reference=f"{DATASET_REFERENCE_PREFIX}{reported_sha256}",
        backup_schema_version=BACKUP_REPORT_SCHEMA_VERSION,
        backup_run_id=_required_text(report, "run_id"),
        backup_branch=_required_text(report, "branch"),
        backup_commit_sha=_required_text(report, "commit_sha"),
        dump_sha256=reported_sha256,
        dump_size_bytes=reported_size,
        inventory_schema_version=inventory_schema,
        database_writes_executed=0,
    )
