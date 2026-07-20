"""Cria backup auditável da base antes do rebuild pré-produção.

Uso dentro do container backend:
    python -m app.cli.pre_prod_backup --branch stable-15jun --commit-sha <sha>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import re
import sys

from app.core.config import settings
from app.services.pre_prod_backup_service import (
    BackupError,
    DEFAULT_ARTIFACT_ROOT,
    create_postgres_backup,
)
from app.services.pre_prod_inventory_service import build_pre_prod_inventory


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
        description="Gera pg_dump completo, inventário, listagem e SHA-256.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
    )
    parser.add_argument("--run-id")
    parser.add_argument("--branch", default=os.getenv("PRE_PROD_BRANCH"))
    parser.add_argument("--commit-sha", default=os.getenv("PRE_PROD_COMMIT_SHA"))
    return parser.parse_args()


async def _main(arguments: argparse.Namespace) -> int:
    if arguments.branch != "stable-15jun":
        raise BackupError("backup pré-produção deve executar na branch stable-15jun")
    if not arguments.commit_sha:
        raise BackupError("informe --commit-sha ou PRE_PROD_COMMIT_SHA")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", arguments.commit_sha):
        raise BackupError("commit SHA deve conter exatamente 40 caracteres hexadecimais")

    inventory = await build_pre_prod_inventory()
    if inventory.totals["blocking_findings"] or inventory.totals["unclassified_tables"]:
        raise BackupError("inventário da origem possui bloqueios; backup operacional abortado")

    report = create_postgres_backup(
        database_url=settings.DATABASE_URL,
        inventory=inventory.to_dict(),
        branch=arguments.branch,
        commit_sha=arguments.commit_sha,
        artifact_root=arguments.artifact_root,
        run_id=arguments.run_id,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    _configure_output()
    try:
        exit_code = asyncio.run(_main(_arguments()))
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("backup pré-produção interrompido")
        exit_code = 130
    except Exception:
        logging.getLogger(__name__).exception("backup pré-produção abortado")
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
