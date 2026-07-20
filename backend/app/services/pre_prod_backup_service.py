"""Backup PostgreSQL auditável para o rebuild de pré-produção."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Callable, Sequence


BACKUP_REPORT_SCHEMA_VERSION = "pre-prod-backup.v2"
DEFAULT_ARTIFACT_ROOT = Path("artifacts/pre-prod-rebuild")


class BackupError(RuntimeError):
    """Falha segura que deve abortar o fluxo pré-produção."""


@dataclass(frozen=True)
class CommandResult:
    command: str
    return_code: int


@dataclass(frozen=True)
class BackupReport:
    schema_version: str
    generated_at: str
    run_id: str
    artifact_directory: str
    branch: str
    commit_sha: str
    pg_dump_major: int
    server_major: int
    dump_file: str
    dump_size_bytes: int
    sha256: str
    inventory_file: str
    contents_file: str
    commands: list[CommandResult]
    safety: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


Runner = Callable[..., subprocess.CompletedProcess[str]]


def create_run_directory(root: Path, run_id: str | None = None) -> Path:
    """Cria uma pasta exclusiva por execução e nunca reutiliza artefatos."""
    selected_run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    allowed = "-_.0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if not selected_run_id or any(char not in allowed for char in selected_run_id):
        raise BackupError("run-id deve conter apenas letras, números, ponto, hífen ou sublinhado")
    directory = root / selected_run_id
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise BackupError(f"diretório de execução já existe: {directory}") from exc
    return directory


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redacted_command(command: Sequence[str]) -> str:
    redacted: list[str] = []
    hide_next = False
    for value in command:
        if hide_next:
            redacted.append("<redacted-database-url>")
            hide_next = False
        elif value in {"--dbname", "-d"}:
            redacted.append(value)
            hide_next = True
        elif value.startswith("--dbname="):
            redacted.append("--dbname=<redacted-database-url>")
        else:
            redacted.append(value)
    return " ".join(redacted)


def run_checked(
    command: Sequence[str],
    *,
    runner: Runner,
    stdout_path: Path | None = None,
) -> CommandResult:
    if stdout_path is None:
        completed = runner(
            list(command),
            check=False,
            capture_output=True,
            text=True,
        )
    else:
        with stdout_path.open("w", encoding="utf-8", newline="\n") as stdout:
            completed = runner(
                list(command),
                check=False,
                stdout=stdout,
                stderr=subprocess.PIPE,
                text=True,
            )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise BackupError(
            f"comando falhou ({completed.returncode}): {redacted_command(command)}; {stderr}"
        )
    return CommandResult(redacted_command(command), completed.returncode)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _postgres_major(version_text: str, *, server_version_num: bool = False) -> int:
    normalized = version_text.strip()
    if server_version_num:
        if not normalized.isdigit():
            raise BackupError("server_version_num PostgreSQL inválido")
        value = int(normalized)
        return value // 10000 if value >= 100000 else value // 10000

    match = re.search(r"\b(\d+)(?:\.\d+)+\b", normalized)
    if not match:
        raise BackupError("não foi possível identificar a versão do pg_dump")
    return int(match.group(1))


def create_postgres_backup(
    *,
    database_url: str,
    inventory: dict[str, object],
    branch: str,
    commit_sha: str,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    run_id: str | None = None,
    runner: Runner = subprocess.run,
) -> BackupReport:
    """Cria dump custom, listagem, checksum e manifesto sem escrever na origem."""
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise BackupError("pre_prod_backup aceita somente uma DATABASE_URL PostgreSQL síncrona")

    directory = create_run_directory(artifact_root, run_id)
    dump_path = directory / "database.dump"
    inventory_path = directory / "origin-inventory.json"
    contents_path = directory / "database.contents.txt"
    client_version_path = directory / "pg-client-version.txt"
    server_version_path = directory / "source-server-version.txt"
    checksum_path = directory / "database.dump.sha256"
    report_path = directory / "backup-report.json"

    write_json(inventory_path, inventory)

    commands = [
        run_checked(
            ["pg_dump", "--version"],
            runner=runner,
            stdout_path=client_version_path,
        ),
        run_checked(
            [
                "psql",
                "--no-psqlrc",
                "--tuples-only",
                "--no-align",
                "--set",
                "ON_ERROR_STOP=1",
                "--dbname",
                database_url,
                "--command",
                "SHOW server_version_num",
            ],
            runner=runner,
            stdout_path=server_version_path,
        ),
    ]
    pg_dump_major = _postgres_major(
        client_version_path.read_text(encoding="utf-8")
    )
    server_major = _postgres_major(
        server_version_path.read_text(encoding="utf-8"),
        server_version_num=True,
    )
    if pg_dump_major != server_major:
        raise BackupError(
            "major do pg_dump diverge do servidor PostgreSQL: "
            f"cliente={pg_dump_major}, servidor={server_major}"
        )

    commands.append(
        run_checked(
            [
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(dump_path),
                "--dbname",
                database_url,
            ],
            runner=runner,
        )
    )
    if not dump_path.is_file() or dump_path.stat().st_size == 0:
        raise BackupError("pg_dump terminou sem produzir um arquivo não vazio")

    commands.append(
        run_checked(
            ["pg_restore", "--list", str(dump_path)],
            runner=runner,
            stdout_path=contents_path,
        )
    )
    if not contents_path.is_file() or contents_path.stat().st_size == 0:
        raise BackupError("pg_restore --list não produziu uma listagem válida")

    checksum = sha256_file(dump_path)
    checksum_path.write_text(
        f"{checksum}  {dump_path.name}\n",
        encoding="ascii",
    )
    report = BackupReport(
        schema_version=BACKUP_REPORT_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        run_id=directory.name,
        artifact_directory=str(directory),
        branch=branch,
        commit_sha=commit_sha,
        pg_dump_major=pg_dump_major,
        server_major=server_major,
        dump_file=dump_path.name,
        dump_size_bytes=dump_path.stat().st_size,
        sha256=checksum,
        inventory_file=inventory_path.name,
        contents_file=contents_path.name,
        commands=commands,
        safety={
            "source_database_writes_executed": 0,
            "cleanup_executed": False,
            "rebuild_executed": False,
            "credentials_recorded": False,
        },
    )
    write_json(report_path, report.to_dict())
    return report
