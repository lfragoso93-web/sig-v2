"""Restaura backup pré-produção somente em PostgreSQL isolado.

Uso dentro do container backend:
    python -m app.cli.pre_prod_restore <artefatos> --confirm-isolated-target
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services.pre_prod_backup_service import BackupError, write_json
from app.services.pre_prod_inventory_service import build_pre_prod_inventory
from app.services.pre_prod_restore_service import (
    read_migration_versions,
    reconcile_inventories,
    restore_postgres_backup,
    write_restore_report,
)


def _configure_output() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida e restaura um backup em banco PostgreSQL isolado.",
    )
    parser.add_argument("artifact_directory", type=Path)
    parser.add_argument(
        "--target-database-url",
        default=os.getenv("PRE_PROD_RESTORE_DATABASE_URL"),
    )
    parser.add_argument("--confirm-isolated-target", action="store_true")
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BackupError(f"artefato JSON inválido: {path}")
    return payload


def _async_database_url(sync_url: str) -> str:
    url = make_url(sync_url)
    if url.drivername not in {"postgres", "postgresql"}:
        raise BackupError("destino deve usar uma URL PostgreSQL síncrona")
    return url.set(drivername="postgresql+asyncpg").render_as_string(
        hide_password=False
    )


async def _restored_inventory(target_database_url: str) -> dict[str, object]:
    engine = create_async_engine(
        _async_database_url(target_database_url),
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            report = await build_pre_prod_inventory(session)
            return report.to_dict()
    finally:
        await engine.dispose()


async def _main(arguments: argparse.Namespace) -> int:
    if not arguments.confirm_isolated_target:
        raise BackupError("use --confirm-isolated-target após validar o banco vazio")
    if not arguments.target_database_url:
        raise BackupError(
            "informe --target-database-url ou PRE_PROD_RESTORE_DATABASE_URL"
        )
    artifact_directory = arguments.artifact_directory.resolve()
    if not artifact_directory.is_dir():
        raise BackupError(f"diretório de artefatos inexistente: {artifact_directory}")

    execution = restore_postgres_backup(
        artifact_directory=artifact_directory,
        source_database_url=settings.DATABASE_URL,
        target_database_url=arguments.target_database_url,
    )
    restored_inventory = await _restored_inventory(arguments.target_database_url)
    write_json(
        artifact_directory / "restored-inventory.json",
        restored_inventory,
    )
    source_inventory = _read_json(artifact_directory / "origin-inventory.json")

    source_migrations, source_command = read_migration_versions(
        database_url=settings.DATABASE_URL,
        output_path=artifact_directory / "origin-migrations.txt",
    )
    restored_migrations, restored_command = read_migration_versions(
        database_url=arguments.target_database_url,
        output_path=artifact_directory / "restored-migrations.txt",
    )
    reconciliation = reconcile_inventories(
        source_inventory=source_inventory,
        restored_inventory=restored_inventory,
        source_migrations=source_migrations,
        restored_migrations=restored_migrations,
    )
    write_restore_report(
        artifact_directory=artifact_directory,
        execution=execution,
        reconciliation=reconciliation,
        migration_commands=[source_command, restored_command],
    )
    print(json.dumps(reconciliation.to_dict(), ensure_ascii=False, indent=2))
    return 0 if reconciliation.ok else 1


def main() -> None:
    _configure_output()
    try:
        exit_code = asyncio.run(_main(_arguments()))
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("restauração isolada interrompida")
        exit_code = 130
    except Exception:
        logging.getLogger(__name__).exception("restauração isolada abortada")
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
