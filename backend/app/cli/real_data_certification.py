"""Dry-run-first administrative CLI for real-data certification events."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.core.database import AsyncSessionLocal
from app.services.real_data_certification_contract import (
    RealDataCertificationAction,
    RealDataCertificationValidationError,
)
from app.services.real_data_certification_executor import (
    execute_real_data_certification_plan,
    mark_certification_result_committed,
    prepare_real_data_certification_plan,
)
from app.services.real_data_certification_reader import RealDataCertificationIdentity

REPORT_SCHEMA_VERSION = "real-data-certification-cli.v1"


def _configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Planeja por padrao ou persiste, com confirmacao forte, uma "
            "promocao/revogacao auditavel de dados reais."
        )
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=[action.value.lower() for action in RealDataCertificationAction],
    )
    parser.add_argument("--environment", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--dataset-reference", required=True)
    parser.add_argument("--alembic-revision", required=True)
    parser.add_argument("--gate-issue-reference", required=True)
    parser.add_argument("--pull-request-reference", required=True)
    parser.add_argument("--evidence-file", type=Path, required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persiste um evento somente quando --confirmation também coincidir.",
    )
    parser.add_argument("--confirmation")
    return parser


def _load_evidence(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RealDataCertificationValidationError(
            f"unable to load promotion evidence: {type(exc).__name__}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise RealDataCertificationValidationError(
            "promotion evidence root must be an object"
        )
    return dict(payload)


def _identity(arguments: argparse.Namespace) -> RealDataCertificationIdentity:
    return RealDataCertificationIdentity(
        environment=arguments.environment,
        branch=arguments.branch,
        commit_sha=arguments.commit_sha,
        dataset_reference=arguments.dataset_reference,
        alembic_revision=arguments.alembic_revision,
        gate_issue_reference=arguments.gate_issue_reference,
        pull_request_reference=arguments.pull_request_reference,
    )


async def _main(arguments: argparse.Namespace) -> int:
    if arguments.execute and not arguments.confirmation:
        raise RealDataCertificationValidationError(
            "--execute requires --confirmation from the unchanged dry-run plan"
        )
    if not arguments.execute and arguments.confirmation:
        raise RealDataCertificationValidationError(
            "--confirmation is accepted only together with --execute"
        )

    evidence = _load_evidence(arguments.evidence_file)
    action = RealDataCertificationAction(arguments.action.upper())
    async with AsyncSessionLocal() as session:
        try:
            plan = await prepare_real_data_certification_plan(
                session,
                action=action,
                identity=_identity(arguments),
                evidence_payload=evidence,
                actor=arguments.actor,
                reason=arguments.reason,
            )
            if not arguments.execute:
                await session.rollback()
                payload = {
                    "schema_version": REPORT_SCHEMA_VERSION,
                    "mode": "dry-run",
                    "database_writes_executed": 0,
                    "transaction_committed": False,
                    "plan": plan.to_dict(),
                }
            else:
                result = await execute_real_data_certification_plan(
                    session,
                    plan=plan,
                    confirmation=arguments.confirmation,
                )
                await session.commit()
                committed = mark_certification_result_committed(result)
                payload = {
                    "schema_version": REPORT_SCHEMA_VERSION,
                    "mode": "execute",
                    "database_writes_executed": (
                        committed.database_writes_executed
                    ),
                    "transaction_committed": committed.transaction_committed,
                    "plan_event_key": plan.event_key,
                    "result": committed.to_dict(),
                }
        except Exception:
            await session.rollback()
            raise

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    _configure_output()
    try:
        exit_code = asyncio.run(_main(_parser().parse_args(argv)))
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:  # noqa: BLE001 - administrative CLI boundary
        print(
            json.dumps(
                {
                    "schema_version": REPORT_SCHEMA_VERSION,
                    "ok": False,
                    "database_writes_executed": 0,
                    "transaction_committed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        exit_code = 1
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
