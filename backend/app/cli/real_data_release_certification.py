"""Dry-run-first automatic certification for CI-approved production releases."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
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
from app.services.real_data_certification_reader import (
    read_real_data_certification,
)
from app.services.real_data_release_certification import (
    RealDataReleaseCertificationError,
    build_release_promotion_evidence,
)
from app.services.real_data_runtime_identity import (
    resolve_real_data_runtime_identity,
)

REPORT_SCHEMA_VERSION = "real-data-release-certification.v1"


class RealDataReleasePostCommitError(RealDataReleaseCertificationError):
    """A release event committed but post-commit verification/reporting failed."""

    def __init__(
        self,
        message: str,
        *,
        database_writes_executed: int,
        event_key: str,
    ) -> None:
        super().__init__(message)
        self.database_writes_executed = database_writes_executed
        self.transaction_committed = True
        self.plan_event_key = event_key


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Collects read-only production evidence and, when explicitly asked, "
            "promotes the exact CI-approved runtime SHA."
        )
    )
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--workflow-run-conclusion", required=True)
    parser.add_argument("--workflow-run-event", required=True)
    parser.add_argument("--workflow-run-branch", required=True)
    parser.add_argument("--smoke-test-passed", action="store_true")
    parser.add_argument("--report-file", type=Path, required=True)
    parser.add_argument("--actor", default="github-actions")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmation")
    return parser


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


async def _main(arguments: argparse.Namespace) -> int:
    if arguments.execute and not arguments.confirmation:
        raise RealDataCertificationValidationError(
            "--execute requires the exact confirmation from the release dry-run"
        )
    if not arguments.execute and arguments.confirmation:
        raise RealDataCertificationValidationError(
            "--confirmation is accepted only together with --execute"
        )

    async with AsyncSessionLocal() as evidence_session:
        try:
            evidence, already_certified = await build_release_promotion_evidence(
                evidence_session,
                expected_sha=arguments.expected_sha,
                workflow_run_id=arguments.workflow_run_id,
                workflow_run_conclusion=arguments.workflow_run_conclusion,
                workflow_run_event=arguments.workflow_run_event,
                workflow_run_branch=arguments.workflow_run_branch,
                smoke_test_passed=arguments.smoke_test_passed,
            )
            await evidence_session.rollback()
        except Exception:
            await evidence_session.rollback()
            raise

    if already_certified:
        payload = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "mode": "already-certified",
            "database_writes_executed": 0,
            "transaction_committed": False,
            "ready_for_real_data": True,
            "commit_sha": arguments.expected_sha,
        }
        _write_report(arguments.report_file, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if evidence is None:
        raise RealDataReleaseCertificationError(
            "release evidence was not produced"
        )

    async with AsyncSessionLocal() as session:
        try:
            identity = await resolve_real_data_runtime_identity(session)
            plan = await prepare_real_data_certification_plan(
                session,
                action=RealDataCertificationAction.PROMOTE,
                identity=identity,
                evidence_payload=evidence,
                actor=arguments.actor,
                reason=(
                    "automatic production release after successful CI workflow "
                    f"run {arguments.workflow_run_id}"
                ),
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
                try:
                    committed = mark_certification_result_committed(result)
                    async with AsyncSessionLocal() as verify_session:
                        current_identity = await resolve_real_data_runtime_identity(
                            verify_session
                        )
                        state = await read_real_data_certification(
                            verify_session,
                            current_identity,
                        )
                    if not state.ready_for_real_data:
                        raise RealDataReleaseCertificationError(
                            "persisted release event did not certify the running identity"
                        )
                except Exception as exc:
                    raise RealDataReleasePostCommitError(
                        "certification event committed, but post-commit verification failed",
                        database_writes_executed=result.database_writes_executed,
                        event_key=plan.event_key,
                    ) from exc
                payload = {
                    "schema_version": REPORT_SCHEMA_VERSION,
                    "mode": "execute",
                    "database_writes_executed": (
                        committed.database_writes_executed
                    ),
                    "transaction_committed": committed.transaction_committed,
                    "plan_event_key": plan.event_key,
                    "result": committed.to_dict(),
                    "ready_for_real_data": state.ready_for_real_data,
                }
        except RealDataReleasePostCommitError:
            raise
        except Exception:
            await session.rollback()
            raise

    try:
        _write_report(arguments.report_file, payload)
    except Exception as exc:
        if payload.get("transaction_committed"):
            raise RealDataReleasePostCommitError(
                "certification event committed, but release report could not be written",
                database_writes_executed=payload["database_writes_executed"],
                event_key=payload["plan_event_key"],
            ) from exc
        raise
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")
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
                    "database_writes_executed": getattr(
                        exc, "database_writes_executed", 0
                    ),
                    "transaction_committed": getattr(
                        exc, "transaction_committed", False
                    ),
                    "plan_event_key": getattr(exc, "plan_event_key", None),
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
