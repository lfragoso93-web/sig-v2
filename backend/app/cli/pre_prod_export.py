"""Executa a exportação auditável dos dados não reconstruíveis.

Uso dentro do container backend:
    python -m app.cli.pre_prod_export \
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
import shutil
import sys

from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_cleanup_impact_service import (
    build_pre_prod_cleanup_impact,
)
from app.services.pre_prod_export_service import build_pre_prod_export

DEFAULT_ARTIFACT_ROOT = Path("artifacts/pre-prod-rebuild")
BLOCKED_EXIT_CODE = 2
RECONCILIATION_EXIT_CODE = 3
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class PreProdExportCliError(RuntimeError):
    """Erro operacional ou de entrada da CLI de exportação."""


class ExportGateBlockedError(PreProdExportCliError):
    """O cleanup impact contém bloqueadores."""


class ExportReconciliationError(PreProdExportCliError):
    """As contagens exportadas divergem do snapshot de origem."""


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
            "Exporta em snapshot único as tabelas aprovadas pelo gate "
            "pre-prod-cleanup-impact.v2."
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
        raise PreProdExportCliError(
            "run-id deve conter somente letras, números, ponto, hífen ou sublinhado"
        )
    return run_id


def _validate_arguments(arguments: argparse.Namespace) -> str:
    if arguments.branch != "stable-15jun":
        raise PreProdExportCliError(
            "exportação pré-produção deve executar na branch stable-15jun"
        )
    if not arguments.commit_sha:
        raise PreProdExportCliError("informe --commit-sha ou PRE_PROD_COMMIT_SHA")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", arguments.commit_sha):
        raise PreProdExportCliError(
            "commit SHA deve conter exatamente 40 caracteres hexadecimais"
        )
    return _validated_run_id(arguments.run_id)


def _expected_export_counts(cleanup_impact) -> dict[str, int]:  # type: ignore[no-untyped-def]
    return {
        table.name: table.row_count
        for table in cleanup_impact.tables
        if table.proposed_action == "export_required"
    }


def _reconcile_counts(cleanup_impact, manifest) -> None:  # type: ignore[no-untyped-def]
    expected = _expected_export_counts(cleanup_impact)
    exported = {table.table_name: table.row_count for table in manifest.tables}
    if exported != expected:
        raise ExportReconciliationError(
            f"contagens exportadas divergem do snapshot: expected={expected}, "
            f"exported={exported}"
        )


def _publish_cleanup_impact(*, cleanup_impact, run_directory: Path) -> Path:  # type: ignore[no-untyped-def]
    """Publica o gate aprovado de forma atômica e sem sobrescrita."""
    destination = run_directory / "cleanup-impact.json"
    temporary = run_directory / ".cleanup-impact.json.tmp"
    if destination.exists() or temporary.exists():
        raise FileExistsError("cleanup impact artifact already exists")
    run_directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        cleanup_impact.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


async def _main(arguments: argparse.Namespace) -> int:
    run_id = _validate_arguments(arguments)
    generated_at = datetime.now(timezone.utc).isoformat()
    run_directory = arguments.artifact_root / run_id
    session = AsyncSessionLocal()

    try:
        await session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        )
        cleanup_impact = await build_pre_prod_cleanup_impact(
            branch=arguments.branch,
            commit_sha=arguments.commit_sha.lower(),
            session=session,
            rollback_supplied_session=False,
        )
        if not cleanup_impact.ok:
            raise ExportGateBlockedError(
                f"cleanup impact bloqueado: {cleanup_impact.blockers}"
            )

        manifest = await build_pre_prod_export(
            cleanup_impact=cleanup_impact,
            branch=arguments.branch,
            commit_sha=arguments.commit_sha.lower(),
            run_id=run_id,
            generated_at=generated_at,
            output_root=arguments.artifact_root,
            session=session,
            transaction_started=True,
        )
        try:
            _reconcile_counts(cleanup_impact, manifest)
            cleanup_impact_path = _publish_cleanup_impact(
                cleanup_impact=cleanup_impact,
                run_directory=run_directory,
            )
        except Exception:
            shutil.rmtree(run_directory / "export", ignore_errors=True)
            (run_directory / "cleanup-impact.json").unlink(missing_ok=True)
            (run_directory / ".cleanup-impact.json.tmp").unlink(missing_ok=True)
            raise

        output = {
            "run_id": run_id,
            "artifact_directory": str(run_directory / "export"),
            "cleanup_impact_path": str(cleanup_impact_path),
            "cleanup_impact": cleanup_impact.to_dict(),
            "manifest": manifest.to_dict(),
            "reconciled": True,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    finally:
        await session.rollback()
        await session.close()


def main() -> None:
    _configure_output()
    try:
        exit_code = asyncio.run(_main(_arguments()))
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("exportação pré-produção interrompida")
        exit_code = 130
    except ExportGateBlockedError:
        logging.getLogger(__name__).exception("gate da exportação bloqueado")
        exit_code = BLOCKED_EXIT_CODE
    except ExportReconciliationError:
        logging.getLogger(__name__).exception("reconciliação da exportação falhou")
        exit_code = RECONCILIATION_EXIT_CODE
    except Exception:
        logging.getLogger(__name__).exception("exportação pré-produção abortada")
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
