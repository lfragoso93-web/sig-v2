"""Executa o dry-run auditável de impacto da limpeza pré-produção.

Uso dentro do container backend:
    python -m app.cli.pre_prod_cleanup_impact \
        --branch stable-15jun \
        --commit-sha <sha> \
        --run-id <run-id>
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import Any

from app.services.pre_prod_cleanup_impact_service import (
    build_pre_prod_cleanup_impact,
)

DEFAULT_ARTIFACT_ROOT = Path("artifacts/pre-prod-rebuild")
REPORT_FILENAME = "cleanup-impact.json"
BLOCKED_EXIT_CODE = 2
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class CleanupImpactCliError(RuntimeError):
    """Erro operacional ou de entrada da CLI de impacto."""


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
        description=(
            "Gera o relatório read-only pre-prod-cleanup-impact.v2 e aborta "
            "quando houver bloqueadores."
        ),
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


def _validated_run_id(value: str | None) -> str:
    run_id = value or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise CleanupImpactCliError(
            "run-id deve conter somente letras, números, ponto, hífen ou sublinhado"
        )
    return run_id


def _validate_arguments(arguments: argparse.Namespace) -> str:
    if arguments.branch != "stable-15jun":
        raise CleanupImpactCliError(
            "dry-run pré-produção deve executar na branch stable-15jun"
        )
    if not arguments.commit_sha:
        raise CleanupImpactCliError("informe --commit-sha ou PRE_PROD_COMMIT_SHA")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", arguments.commit_sha):
        raise CleanupImpactCliError(
            "commit SHA deve conter exatamente 40 caracteres hexadecimais"
        )
    return _validated_run_id(arguments.run_id)


def _write_report(
    *,
    artifact_root: Path,
    run_id: str,
    payload: dict[str, Any],
) -> Path:
    artifact_directory = artifact_root / run_id
    artifact_directory.mkdir(parents=True, exist_ok=False)
    report_path = artifact_directory / REPORT_FILENAME
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_path


async def _main(arguments: argparse.Namespace) -> int:
    run_id = _validate_arguments(arguments)
    report = await build_pre_prod_cleanup_impact(
        branch=arguments.branch,
        commit_sha=arguments.commit_sha.lower(),
    )
    payload = report.to_dict()
    report_path = _write_report(
        artifact_root=arguments.artifact_root,
        run_id=run_id,
        payload=payload,
    )

    output = {
        "run_id": run_id,
        "artifact_directory": str(report_path.parent),
        "report_path": str(report_path),
        "report": payload,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if report.ok else BLOCKED_EXIT_CODE


def main() -> None:
    _configure_output()
    try:
        exit_code = asyncio.run(_main(_arguments()))
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("dry-run de impacto interrompido")
        exit_code = 130
    except Exception:
        logging.getLogger(__name__).exception("dry-run de impacto abortado")
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
