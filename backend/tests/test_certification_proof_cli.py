"""CLI boundary tests for the read-only certification proof generator."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.cli import certification_proof as cli
from app.doctor.contracts import (
    DoctorExitCode,
    DoctorFindingResult,
    DoctorFindingStatus,
)
from app.doctor.static_runner import StaticDoctorReport


def test_load_tests_rejects_raw_output_field(tmp_path: Path) -> None:
    path = tmp_path / "tests.json"
    path.write_text(
        json.dumps(
            {
                "contract": "sgi-certification-tests.v1",
                "suites": [
                    {
                        "name": "canonical",
                        "status": "passed",
                        "output": "not allowlisted",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        cli._load_tests(path)


def test_optional_gate_identifiers_are_safe_and_unique() -> None:
    assert cli._validate_optional_gates(["oci-284"]) == ("oci-284",)
    with pytest.raises(ValueError, match="safe identifier"):
        cli._validate_optional_gates(["TOKEN=value"])
    with pytest.raises(ValueError, match="unique"):
        cli._validate_optional_gates(["oci-284", "oci-284"])


@pytest.mark.parametrize(
    ("doctor_status", "proof_status"),
    [
        (DoctorFindingStatus.PASS, "passed"),
        (DoctorFindingStatus.FAIL, "failed"),
        (DoctorFindingStatus.SKIP, "skipped"),
        (DoctorFindingStatus.ERROR, "error"),
    ],
)
def test_architecture_status_mapping(
    monkeypatch: pytest.MonkeyPatch,
    doctor_status: DoctorFindingStatus,
    proof_status: str,
) -> None:
    report = StaticDoctorReport(
        results=(
            DoctorFindingResult(
                finding_id="SGI001",
                status=doctor_status,
                detail="not serialized",
            ),
        ),
        exit_code=(
            DoctorExitCode.OK
            if doctor_status is DoctorFindingStatus.PASS
            else DoctorExitCode.FINDINGS
        ),
    )
    monkeypatch.setattr(
        cli,
        "run_static_checks",
        lambda *args, **kwargs: report,
    )

    evidence = cli._architecture_evidence()

    assert evidence.findings[0].status.value == proof_status


def test_cli_error_boundary_does_not_serialize_exception_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "_build",
        AsyncMock(side_effect=RuntimeError("TOKEN=secret")),
    )

    with pytest.raises(SystemExit) as raised:
        cli.main(["--checkout-sha", "a" * 40, "--tests-file", "unused.json"])

    assert raised.value.code == 2
    error = capsys.readouterr().err
    assert "RuntimeError" in error
    assert "secret" not in error
