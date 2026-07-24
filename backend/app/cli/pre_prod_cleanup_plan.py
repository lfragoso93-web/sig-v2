"""Valida artefatos aprovados e publica o plano de limpeza sem acessar o banco.

Uso dentro do container backend:
    python -m app.cli.pre_prod_cleanup_plan \
        --run-id <run-id> \
        --branch stable-15jun \
        --commit-sha <sha>
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys

from app.services.pre_prod_cleanup_execution_service import (
    CleanupExecutionValidationError,
    build_pre_prod_cleanup_execution_plan,
    publish_pre_prod_cleanup_execution_plan,
)
from app.services.pre_prod_isolated_cleanup_contract import canonical_json_sha256

DEFAULT_ARTIFACT_ROOT = Path("artifacts/pre-prod-rebuild")
IDENTITY_EXIT_CODE = 2
VALIDATION_EXIT_CODE = 3
ALREADY_EXISTS_EXIT_CODE = 4


class CleanupPlanIdentityError(RuntimeError):
    """Identidade operacional ausente ou inconsistente."""


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
            "Valida cleanup impact, manifesto e CSVs e publica somente o "
            "pre-prod-cleanup-execution.v1."
        ),
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--branch", default=os.getenv("PRE_PROD_BRANCH"))
    parser.add_argument("--commit-sha", default=os.getenv("PRE_PROD_COMMIT_SHA"))
    parser.add_argument("--cleanup-impact-path", type=Path)
    parser.add_argument("--manifest-path", type=Path)
    return parser.parse_args()


def _validate_identity(arguments: argparse.Namespace) -> tuple[str, str]:
    if not arguments.branch:
        raise CleanupPlanIdentityError("informe --branch ou PRE_PROD_BRANCH")
    if not arguments.commit_sha:
        raise CleanupPlanIdentityError(
            "informe --commit-sha ou PRE_PROD_COMMIT_SHA"
        )
    return str(arguments.branch), str(arguments.commit_sha)


def _resolve_paths(arguments: argparse.Namespace) -> tuple[Path, Path, Path]:
    run_directory = arguments.artifact_root / arguments.run_id
    cleanup_impact_path = arguments.cleanup_impact_path or (
        run_directory / "cleanup-impact.json"
    )
    manifest_path = arguments.manifest_path or (
        run_directory / "export" / "manifest.json"
    )
    return run_directory, cleanup_impact_path, manifest_path


def _main(arguments: argparse.Namespace) -> int:
    branch, commit_sha = _validate_identity(arguments)
    run_directory, cleanup_impact_path, manifest_path = _resolve_paths(arguments)
    plan = build_pre_prod_cleanup_execution_plan(
        run_directory=run_directory,
        cleanup_impact_path=cleanup_impact_path,
        manifest_path=manifest_path,
        run_id=arguments.run_id,
        branch=branch,
        commit_sha=commit_sha,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    destination = publish_pre_prod_cleanup_execution_plan(
        plan=plan,
        run_directory=run_directory,
    )
    plan_sha256 = canonical_json_sha256(plan.to_dict())
    output = {
        "schema_version": plan.schema_version,
        "run_id": plan.run_id,
        "artifact_path": str(destination),
        "plan_sha256": plan_sha256,
        "plan": plan.to_dict(),
        "database_accessed": False,
        "database_writes_executed": 0,
        "cleanup_executed": False,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    _configure_output()
    try:
        exit_code = _main(_arguments())
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("planejamento de limpeza interrompido")
        exit_code = 130
    except CleanupPlanIdentityError:
        logging.getLogger(__name__).exception("identidade operacional inválida")
        exit_code = IDENTITY_EXIT_CODE
    except CleanupExecutionValidationError:
        logging.getLogger(__name__).exception("validação dos artefatos falhou")
        exit_code = VALIDATION_EXIT_CODE
    except FileExistsError:
        logging.getLogger(__name__).exception("plano de limpeza já existe")
        exit_code = ALREADY_EXISTS_EXIT_CODE
    except Exception:
        logging.getLogger(__name__).exception("planejamento de limpeza abortado")
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
