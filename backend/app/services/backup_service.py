"""Serviço operacional de backup e restauração PostgreSQL."""

from __future__ import annotations

import asyncio
import gzip
import logging
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

BACKUPS_DIR = Path("/tmp/db_backups")
_BACKUP_FILENAME_RE = re.compile(r"^backup_[0-9]{8}_[0-9]{6}\.sql\.gz$")


class BackupError(Exception):
    """Erro de criação de backup."""


class RestoreError(Exception):
    """Erro de restauração de backup."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_backups_dir() -> None:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def _validate_backup_filename(backup_filename: str) -> None:
    """Valida a identidade externa sem usá-la em uma expressão de path."""
    if not isinstance(backup_filename, str) or not _BACKUP_FILENAME_RE.fullmatch(
        backup_filename,
    ):
        raise ValueError("Invalid backup filename")


def _new_backup_path(now: datetime) -> Path:
    """Cria o path de saída somente a partir de dados gerados pelo servidor."""
    backups_root = BACKUPS_DIR.resolve()
    backup_filename = f"backup_{now.strftime('%Y%m%d_%H%M%S')}.sql.gz"
    backup_path = backups_root / backup_filename
    return backup_path


def _find_existing_backup_path(backup_filename: str) -> Path | None:
    """Seleciona um backup pelo nome a partir da enumeração do diretório confiável."""
    _validate_backup_filename(backup_filename)
    backups_root = BACKUPS_DIR.resolve()

    for candidate in backups_root.iterdir():
        if candidate.name != backup_filename:
            continue
        backup_path = candidate.resolve()
        if candidate.is_symlink() or backup_path.parent != backups_root:
            raise ValueError("Invalid backup filename")
        return backup_path

    return None


def _decompress_backup(backup_path: Path, temp_sql_file: Path) -> None:
    """Descompacta o backup fora do event loop."""

    with gzip.open(backup_path, "rb") as input_file, open(
        temp_sql_file,
        "wb",
    ) as output_file:
        shutil.copyfileobj(input_file, output_file)


def _parse_db_url(db_url: str) -> dict[str, Any]:
    """Converte uma URL PostgreSQL nos argumentos usados por pg_dump/psql."""

    parsed = urlparse(db_url)
    database = parsed.path.lstrip("/")
    if not all([parsed.hostname, parsed.username, database]):
        raise ValueError(f"Invalid database URL: {db_url}")

    return {
        "user": parsed.username,
        "password": parsed.password or "",
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": database,
    }


async def create_database_backup(
    db_url: str,
) -> dict[str, Any]:
    """Cria um backup PostgreSQL comprimido com pg_dump."""

    _ensure_backups_dir()
    result: dict[str, Any] = {
        "success": False,
        "backup_id": None,
        "filename": None,
        "path": None,
        "size_mb": 0.0,
        "timestamp": None,
        "error": None,
    }

    try:
        now = _utc_now()
        backup_id = f"backup_{now.strftime('%Y%m%d_%H%M%S')}"
        backup_file_gz = _new_backup_path(now)
        parsed_url = _parse_db_url(db_url)

        env = os.environ.copy()
        env["PGPASSWORD"] = parsed_url["password"]
        command = [
            "pg_dump",
            "-h",
            parsed_url["host"],
            "-p",
            str(parsed_url["port"]),
            "-U",
            parsed_url["user"],
            "-d",
            parsed_url["database"],
            "--format=plain",
            "--verbose",
        ]

        logger.info("[backup] Starting backup: %s", backup_id)
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_message = stderr.decode("utf-8", errors="ignore")
            logger.error(
                "[backup] pg_dump failed: %s",
                sanitize_log_value(error_message),
            )
            result["error"] = f"pg_dump failed: {error_message}"
            return result

        with gzip.open(backup_file_gz, "wb") as output_file:
            output_file.write(stdout)

        size_mb = backup_file_gz.stat().st_size / (1024 * 1024)
        result.update(
            {
                "success": True,
                "backup_id": backup_id,
                "filename": backup_file_gz.name,
                "path": str(backup_file_gz),
                "size_mb": round(size_mb, 2),
                "timestamp": _utc_now().isoformat(),
            }
        )
        logger.info("[backup] Backup completed: %s (%.2f MB)", backup_id, size_mb)
    except Exception as exc:
        logger.exception("[backup] Backup failed")
        result["error"] = str(exc)

    return result


async def restore_database_backup(
    db_url: str,
    backup_filename: str,
) -> dict[str, Any]:
    """Restaura um backup PostgreSQL comprimido usando psql."""

    result: dict[str, Any] = {
        "success": False,
        "backup_id": None,
        "timestamp": None,
        "error": None,
        "warning": None,
    }

    try:
        _ensure_backups_dir()
        backup_path = _find_existing_backup_path(backup_filename)
        if backup_path is None:
            result["error"] = f"Backup file not found: {backup_filename}"
            logger.error("[restore] Backup file not found")
            return result

        temp_sql_file = BACKUPS_DIR / f"restore_temp_{_utc_now().timestamp()}.sql"
        try:
            await asyncio.to_thread(
                _decompress_backup,
                backup_path,
                temp_sql_file,
            )
        except Exception as exc:  # noqa: BLE001 - erro convertido no contrato de restore
            result["error"] = f"Failed to decompress backup: {exc}"
            logger.error(
                "[restore] Decompression failed: %s",
                sanitize_log_value(exc),
            )
            return result

        parsed_url = _parse_db_url(db_url)
        env = os.environ.copy()
        env["PGPASSWORD"] = parsed_url["password"]
        command = [
            "psql",
            "-h",
            parsed_url["host"],
            "-p",
            str(parsed_url["port"]),
            "-U",
            parsed_url["user"],
            "-d",
            parsed_url["database"],
            "-f",
            str(temp_sql_file),
        ]

        logger.info(
            "[restore] Starting restore from: %s",
            sanitize_log_value(backup_filename),
        )
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        _, stderr = await process.communicate()
        temp_sql_file.unlink(missing_ok=True)

        if process.returncode != 0:
            error_message = stderr.decode("utf-8", errors="ignore")
            logger.error(
                "[restore] psql failed: %s",
                sanitize_log_value(error_message),
            )
            result["error"] = f"psql failed: {error_message}"
            return result

        result.update(
            {
                "success": True,
                "backup_id": backup_filename.replace(".sql.gz", "").replace(".sql", ""),
                "timestamp": _utc_now().isoformat(),
            }
        )
        logger.info("[restore] Restore completed successfully")
    except ValueError:
        logger.warning("[restore] Rejected invalid backup filename")
        result["error"] = "Invalid backup filename"
    except Exception as exc:
        logger.exception("[restore] Restore failed")
        result["error"] = str(exc)

    return result


async def list_backups() -> dict[str, Any]:
    """Lista os backups disponíveis e seus metadados."""

    result: dict[str, Any] = {
        "success": False,
        "backups": [],
        "total_size_mb": 0.0,
        "count": 0,
        "error": None,
    }

    try:
        _ensure_backups_dir()
        backup_files = sorted(
            BACKUPS_DIR.glob("backup_*.sql.gz"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        total_size = 0
        for backup_file in backup_files:
            stat = backup_file.stat()
            total_size += stat.st_size
            result["backups"].append(
                {
                    "filename": backup_file.name,
                    "backup_id": backup_file.stem.replace(".sql", ""),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=UTC,
                    ).isoformat(),
                }
            )

        result.update(
            {
                "count": len(backup_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "success": True,
            }
        )
    except Exception as exc:
        logger.exception("[backups_list] Error listing backups")
        result["error"] = str(exc)

    return result


async def delete_backup(backup_filename: str) -> dict[str, Any]:
    """Remove um arquivo de backup existente."""

    result: dict[str, Any] = {
        "success": False,
        "backup_id": None,
        "error": None,
    }

    try:
        _ensure_backups_dir()
        backup_path = _find_existing_backup_path(backup_filename)
        if backup_path is None:
            result["error"] = f"Backup file not found: {backup_filename}"
            logger.warning("[backup_delete] File not found")
            return result

        backup_path.unlink()
        result.update(
            {
                "success": True,
                "backup_id": backup_filename.replace(".sql.gz", "").replace(".sql", ""),
            }
        )
        logger.info(
            "[backup_delete] Backup deleted: %s",
            sanitize_log_value(backup_filename),
        )
    except ValueError:
        logger.warning("[backup_delete] Rejected invalid backup filename")
        result["error"] = "Invalid backup filename"
    except Exception as exc:
        logger.exception("[backup_delete] Error deleting backup")
        result["error"] = str(exc)

    return result
