"""Generate a read-only sgi-certification.v1 proof for the current runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.cli.architecture_doctor import REPOSITORY_ROOT, STATIC_FINDING_IDS
from app.core.cache import get_redis
from app.core.database import AsyncSessionLocal
from app.doctor.static_runner import run_static_checks
from app.doctor.contracts import DoctorFindingStatus
from app.services.certification_proof import (
    ArchitectureEvidence,
    CertificationProof,
    DoctorFindingEvidence,
    ProofStatus,
    RuntimeEvidence,
    ServiceEvidence,
    ServiceStatus,
    TestEvidence,
    build_certification_proof,
)
from app.services.real_data_certification_reader import (
    read_real_data_certification,
)
from app.services.real_data_runtime_identity import (
    resolve_real_data_runtime_identity,
)

CLI_CONTRACT = "sgi-certification-proof-cli.v1"
_SAFE_GATE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,79}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout-sha", required=True)
    parser.add_argument("--tests-file", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--disabled-optional-gate",
        action="append",
        default=[],
        dest="disabled_optional_gates",
    )
    return parser


def _load_tests(path: Path) -> TestEvidence:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return TestEvidence.model_validate(payload)


def _architecture_evidence() -> ArchitectureEvidence:
    report = run_static_checks(
        STATIC_FINDING_IDS,
        repository_root=REPOSITORY_ROOT,
    )
    return ArchitectureEvidence(
        exit_code=int(report.exit_code),
        findings=tuple(
            DoctorFindingEvidence(
                finding_id=result.finding_id,
                status={
                    DoctorFindingStatus.PASS: ProofStatus.PASSED,
                    DoctorFindingStatus.FAIL: ProofStatus.FAILED,
                    DoctorFindingStatus.SKIP: ProofStatus.SKIPPED,
                    DoctorFindingStatus.ERROR: ProofStatus.ERROR,
                }[result.status],
            )
            for result in report.results
        ),
    )


async def _runtime_evidence() -> RuntimeEvidence:
    redis_client = await get_redis()
    redis_status = ServiceStatus.UNAVAILABLE
    if redis_client is not None:
        try:
            if await redis_client.ping():
                redis_status = ServiceStatus.HEALTHY
        except Exception:  # noqa: BLE001 - serialize status only
            redis_status = ServiceStatus.UNAVAILABLE
    return RuntimeEvidence(
        backend=ServiceEvidence(status=ServiceStatus.HEALTHY, required=True),
        postgres=ServiceEvidence(status=ServiceStatus.HEALTHY, required=True),
        redis=ServiceEvidence(status=redis_status, required=False),
    )


def _validate_optional_gates(values: list[str]) -> tuple[str, ...]:
    if len(values) != len(set(values)):
        raise ValueError("disabled optional gates must be unique")
    if any(not _SAFE_GATE.fullmatch(value) for value in values):
        raise ValueError("disabled optional gate must be a safe identifier")
    return tuple(values)


async def _build(arguments: argparse.Namespace) -> CertificationProof:
    tests = _load_tests(arguments.tests_file)
    architecture = _architecture_evidence()
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        identity = await resolve_real_data_runtime_identity(session)
        certification = await read_real_data_certification(session, identity)
        await session.rollback()
    return build_certification_proof(
        generated_at_utc=datetime.now(timezone.utc),
        checkout_sha=arguments.checkout_sha,
        identity=identity,
        certification=certification,
        tests=tests,
        architecture=architecture,
        runtime=await _runtime_evidence(),
        disabled_optional_gates=_validate_optional_gates(
            arguments.disabled_optional_gates
        ),
    )


def _write(payload: str, output: Path | None) -> None:
    if output is not None:
        output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


def main(argv: Sequence[str] | None = None) -> None:
    try:
        arguments = _parser().parse_args(argv)
        proof = asyncio.run(_build(arguments))
        payload = proof.model_dump_json(indent=2)
        _write(payload, arguments.output)
        exit_code = 0 if proof.result is ProofStatus.PASSED else 1
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as exc:  # noqa: BLE001 - sanitized CLI boundary
        print(
            json.dumps(
                {
                    "contract": CLI_CONTRACT,
                    "database_writes_executed": 0,
                    "error_type": type(exc).__name__,
                    "result": "failed",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        exit_code = 2
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
