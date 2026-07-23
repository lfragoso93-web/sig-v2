"""CLI exclusiva para limpeza controlada em PostgreSQL isolado.

A confirmação composta é obrigatória por argumento. URLs nunca são impressas e o
executor transacional continua sendo a única camada autorizada a executar DELETE.
"""
from __future__ import annotations

import argparse
from enum import IntEnum
import json
import logging
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL, make_url

from app.services.pre_prod_isolated_cleanup_contract import (
    APPROVED_BRANCH,
    ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
    REQUIRED_ISOLATION_MARKER,
    CleanupDatabaseIdentity,
    CleanupExecutionConfirmation,
    IsolatedCleanupAuthorization,
    IsolatedCleanupValidationError,
    canonical_json_sha256,
    validate_approved_plan,
)
from app.services.pre_prod_isolated_cleanup_executor import (
    IsolatedCleanupCountMismatchError,
    IsolatedCleanupExecutionError,
    IsolatedCleanupLockUnavailableError,
    IsolatedCleanupPostconditionError,
    execute_isolated_cleanup,
)
from app.services.pre_prod_isolated_cleanup_report import (
    DEFAULT_ARTIFACT_ROOT,
    IsolatedCleanupReportError,
    build_execution_report,
    build_failure_report,
    publish_execution_report,
    utc_now_iso,
)

_LOGGER = logging.getLogger(__name__)


class CleanupExitCode(IntEnum):
    SUCCESS = 0
    INTERNAL_ERROR = 1
    INVALID_INPUT = 2
    IDENTITY_MISMATCH = 10
    INVALID_TARGET = 11
    INVALID_CONFIRMATION = 12
    PLAN_DIVERGENCE = 20
    LOCK_UNAVAILABLE = 21
    ROLLED_BACK = 22
    ARTIFACT_ERROR = 30
    INTERRUPTED = 130


class CliIdentityError(ValueError):
    pass


class CliTargetError(ValueError):
    pass


class CliConfirmationError(ValueError):
    pass


def _configure_output() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa cleanup aprovado somente em PostgreSQL isolado.",
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--source-database-url", required=True)
    parser.add_argument("--target-database-url", required=True)
    parser.add_argument("--target-isolation-marker", required=True)
    parser.add_argument("--confirmation", required=True)
    return parser.parse_args(argv)


def _load_plan(path: Path) -> Mapping[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"não foi possível ler plano UTF-8 válido: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("cleanup plan deve ser um objeto JSON")
    return payload


def _database_identity(database_url: str, *, isolation_marker: str | None) -> CleanupDatabaseIdentity:
    try:
        parsed: URL = make_url(database_url)
    except Exception as exc:
        raise CliTargetError("URL PostgreSQL inválida") from exc
    if not parsed.drivername.startswith("postgresql"):
        raise CliTargetError("cleanup isolado exige URL PostgreSQL")
    if not parsed.host or not parsed.database:
        raise CliTargetError("URL PostgreSQL deve informar host e database")
    return CleanupDatabaseIdentity(
        host=parsed.host,
        port=parsed.port or 5432,
        database=parsed.database,
        isolation_marker=isolation_marker,
    )


def _build_authorization(
    arguments: argparse.Namespace,
    plan_payload: Mapping[str, Any],
) -> IsolatedCleanupAuthorization:
    if arguments.branch != APPROVED_BRANCH:
        raise CliIdentityError("branch de execução deve ser stable-15jun")

    run_id = plan_payload.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise CliIdentityError("cleanup plan não possui run_id válido")

    plan_sha256 = canonical_json_sha256(plan_payload)
    try:
        plan = validate_approved_plan(
            payload=plan_payload,
            expected_run_id=run_id,
            expected_commit_sha=arguments.commit_sha,
            expected_plan_sha256=plan_sha256,
        )
    except IsolatedCleanupValidationError as exc:
        raise CliIdentityError(str(exc)) from exc

    try:
        source = _database_identity(
            arguments.source_database_url,
            isolation_marker=None,
        )
        target = _database_identity(
            arguments.target_database_url,
            isolation_marker=arguments.target_isolation_marker,
        )
        if target.isolation_marker != REQUIRED_ISOLATION_MARKER:
            raise CliTargetError("marcador obrigatório de isolamento ausente")
        if source.normalized_key == target.normalized_key:
            raise CliTargetError("destino isolado deve ser diferente da origem")
    except IsolatedCleanupValidationError as exc:
        raise CliTargetError(str(exc)) from exc

    try:
        confirmation = CleanupExecutionConfirmation(
            run_id=plan.run_id,
            target_database=target.database,
            commit_sha=plan.commit_sha,
            plan_sha256=plan.plan_sha256,
            confirmation=arguments.confirmation,
        )
    except IsolatedCleanupValidationError as exc:
        raise CliConfirmationError(str(exc)) from exc

    try:
        return IsolatedCleanupAuthorization(
            schema_version=ISOLATED_CLEANUP_REPORT_SCHEMA_VERSION,
            plan=plan,
            source=source,
            target=target,
            confirmation=confirmation,
        )
    except IsolatedCleanupValidationError as exc:
        raise CliTargetError(str(exc)) from exc


def _target_engine(database_url: str) -> Engine:
    parsed = make_url(database_url)
    if "+asyncpg" in parsed.drivername:
        raise CliTargetError("target-database-url deve usar driver PostgreSQL síncrono")
    return create_engine(database_url, pool_pre_ping=True)


def _publish_failure_evidence(
    *,
    authorization: IsolatedCleanupAuthorization,
    arguments: argparse.Namespace,
    started_at: str,
    final_state: str,
    abort_reason: str,
    lock_acquired: bool,
) -> Path:
    report = build_failure_report(
        authorization=authorization,
        started_at=started_at,
        finished_at=utc_now_iso(),
        final_state=final_state,
        abort_reason=abort_reason,
        lock_acquired=lock_acquired,
    )
    return publish_execution_report(
        report=report,
        artifact_root=arguments.artifact_root,
    )


def run(
    arguments: argparse.Namespace,
    *,
    engine_factory: Callable[[str], Engine] = _target_engine,
) -> CleanupExitCode:
    try:
        plan_payload = _load_plan(arguments.plan)
    except ValueError as exc:
        _LOGGER.error("entrada inválida: %s", exc)
        return CleanupExitCode.INVALID_INPUT

    try:
        authorization = _build_authorization(arguments, plan_payload)
    except CliIdentityError as exc:
        _LOGGER.error("identidade recusada: %s", exc)
        return CleanupExitCode.IDENTITY_MISMATCH
    except CliTargetError as exc:
        _LOGGER.error("alvo recusado: %s", exc)
        return CleanupExitCode.INVALID_TARGET
    except CliConfirmationError as exc:
        _LOGGER.error("confirmação recusada: %s", exc)
        return CleanupExitCode.INVALID_CONFIRMATION

    started_at = utc_now_iso()
    engine: Engine | None = None
    try:
        engine = engine_factory(arguments.target_database_url)
        with engine.connect() as connection:
            result = execute_isolated_cleanup(
                connection=connection,
                authorization=authorization,
                plan_payload=plan_payload,
            )
        report = build_execution_report(
            authorization=authorization,
            result=result,
            started_at=started_at,
            finished_at=utc_now_iso(),
        )
        destination = publish_execution_report(
            report=report,
            artifact_root=arguments.artifact_root,
        )
    except IsolatedCleanupCountMismatchError:
        _LOGGER.error("divergência anterior à limpeza; detalhes omitidos")
        try:
            _publish_failure_evidence(
                authorization=authorization,
                arguments=arguments,
                started_at=started_at,
                final_state="aborted",
                abort_reason="precondition_count_mismatch",
                lock_acquired=True,
            )
        except IsolatedCleanupReportError as report_exc:
            _LOGGER.error("falha ao publicar evidência de aborto: %s", report_exc)
            return CleanupExitCode.ARTIFACT_ERROR
        return CleanupExitCode.PLAN_DIVERGENCE
    except IsolatedCleanupLockUnavailableError:
        _LOGGER.error("lock operacional indisponível; detalhes omitidos")
        try:
            _publish_failure_evidence(
                authorization=authorization,
                arguments=arguments,
                started_at=started_at,
                final_state="aborted",
                abort_reason="lock_unavailable",
                lock_acquired=False,
            )
        except IsolatedCleanupReportError as report_exc:
            _LOGGER.error("falha ao publicar evidência de aborto: %s", report_exc)
            return CleanupExitCode.ARTIFACT_ERROR
        return CleanupExitCode.LOCK_UNAVAILABLE
    except IsolatedCleanupPostconditionError:
        _LOGGER.error("execução revertida por pós-condição; detalhes omitidos")
        try:
            _publish_failure_evidence(
                authorization=authorization,
                arguments=arguments,
                started_at=started_at,
                final_state="rolled_back",
                abort_reason="postcondition_failed",
                lock_acquired=True,
            )
        except IsolatedCleanupReportError as report_exc:
            _LOGGER.error("falha ao publicar evidência de rollback: %s", report_exc)
            return CleanupExitCode.ARTIFACT_ERROR
        return CleanupExitCode.ROLLED_BACK
    except IsolatedCleanupExecutionError:
        _LOGGER.error("execução revertida; detalhes omitidos")
        try:
            _publish_failure_evidence(
                authorization=authorization,
                arguments=arguments,
                started_at=started_at,
                final_state="rolled_back",
                abort_reason="execution_failed",
                lock_acquired=True,
            )
        except IsolatedCleanupReportError as report_exc:
            _LOGGER.error("falha ao publicar evidência de rollback: %s", report_exc)
            return CleanupExitCode.ARTIFACT_ERROR
        return CleanupExitCode.ROLLED_BACK
    except IsolatedCleanupReportError as exc:
        _LOGGER.error("falha ao publicar evidência: %s", exc)
        return CleanupExitCode.ARTIFACT_ERROR
    except CliTargetError as exc:
        _LOGGER.error("alvo recusado: %s", exc)
        return CleanupExitCode.INVALID_TARGET
    finally:
        if engine is not None:
            engine.dispose()

    print(json.dumps({"status": "committed", "execution_report": str(destination)}, ensure_ascii=False))
    return CleanupExitCode.SUCCESS


def main(argv: list[str] | None = None) -> None:
    _configure_output()
    try:
        exit_code = run(_arguments(argv))
    except KeyboardInterrupt:
        _LOGGER.warning("cleanup isolado interrompido")
        exit_code = CleanupExitCode.INTERRUPTED
    except Exception:
        _LOGGER.exception("cleanup isolado abortado por falha interna")
        exit_code = CleanupExitCode.INTERNAL_ERROR
    raise SystemExit(int(exit_code))


if __name__ == "__main__":
    main()
