from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from app.services.pre_prod_backup_service import (
    BackupError,
    create_postgres_backup,
)


def _successful_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    if command == ["pg_dump", "--version"]:
        stdout = kwargs["stdout"]
        stdout.write("pg_dump (PostgreSQL) 16.10\n")
        stdout.flush()
    elif command[0] == "psql":
        stdout = kwargs["stdout"]
        stdout.write("160010\n")
        stdout.flush()
    elif command[0] == "pg_dump":
        dump_path = Path(command[command.index("--file") + 1])
        dump_path.write_bytes(b"postgres-custom-dump")
    elif command[:2] == ["pg_restore", "--list"]:
        stdout = kwargs["stdout"]
        stdout.write("TABLE public assets\n")
        stdout.flush()
    return subprocess.CompletedProcess(command, 0, "", "")


def test_backup_creates_exclusive_auditable_artifacts(tmp_path: Path) -> None:
    report = create_postgres_backup(
        database_url="postgresql://user:secret@db:5432/sgi",
        inventory={"schema_version": "pre-prod-inventory.v2"},
        branch="stable-15jun",
        commit_sha="abc123",
        artifact_root=tmp_path,
        run_id="test-run",
        runner=_successful_runner,
    )

    directory = tmp_path / "test-run"
    assert {path.name for path in directory.iterdir()} == {
        "backup-report.json",
        "database.contents.txt",
        "database.dump",
        "database.dump.sha256",
        "origin-inventory.json",
        "pg-client-version.txt",
        "source-server-version.txt",
    }
    assert report.dump_size_bytes > 0
    assert report.pg_dump_major == report.server_major == 16
    assert len(report.sha256) == 64
    assert report.safety["source_database_writes_executed"] == 0
    assert "secret" not in " ".join(item.command for item in report.commands)

    with pytest.raises(BackupError, match="já existe"):
        create_postgres_backup(
            database_url="postgresql://user:secret@db:5432/sgi",
            inventory={},
            branch="stable-15jun",
            commit_sha="abc123",
            artifact_root=tmp_path,
            run_id="test-run",
            runner=_successful_runner,
        )


def test_backup_rejects_non_postgresql_source(tmp_path: Path) -> None:
    with pytest.raises(BackupError, match="PostgreSQL"):
        create_postgres_backup(
            database_url="sqlite:///sgi.db",
            inventory={},
            branch="stable-15jun",
            commit_sha="abc123",
            artifact_root=tmp_path,
            runner=_successful_runner,
        )


def test_backup_aborts_when_pg_dump_does_not_create_file(tmp_path: Path) -> None:
    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["pg_dump", "--version"]:
            stdout = kwargs["stdout"]
            stdout.write("pg_dump (PostgreSQL) 16.10\n")
            stdout.flush()
        elif command[0] == "psql":
            stdout = kwargs["stdout"]
            stdout.write("160010\n")
            stdout.flush()
        return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(BackupError, match="arquivo não vazio"):
        create_postgres_backup(
            database_url="postgresql://user:secret@db:5432/sgi",
            inventory={},
            branch="stable-15jun",
            commit_sha="abc123",
            artifact_root=tmp_path,
            run_id="empty-dump",
            runner=runner,
        )


def test_backup_rejects_client_server_major_mismatch(tmp_path: Path) -> None:
    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        stdout = kwargs["stdout"]
        if command == ["pg_dump", "--version"]:
            stdout.write("pg_dump (PostgreSQL) 18.0\n")
        else:
            stdout.write("160010\n")
        stdout.flush()
        return subprocess.CompletedProcess(command, 0, "", "")

    with pytest.raises(BackupError, match="cliente=18, servidor=16"):
        create_postgres_backup(
            database_url="postgresql://user:secret@db:5432/sgi",
            inventory={},
            branch="stable-15jun",
            commit_sha="abc123",
            artifact_root=tmp_path,
            run_id="version-mismatch",
            runner=runner,
        )
