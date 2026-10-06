from __future__ import annotations

import json

import pytest

from app.cli import architecture_doctor as cli
from app.doctor.contracts import (
    DoctorExitCode,
    DoctorFindingResult,
    DoctorFindingStatus,
)
from app.doctor.static_runner import StaticDoctorReport


def _report(exit_code: DoctorExitCode) -> StaticDoctorReport:
    return StaticDoctorReport(
        results=(
            DoctorFindingResult(
                finding_id="SGI004",
                status=(
                    DoctorFindingStatus.PASS
                    if exit_code is DoctorExitCode.OK
                    else DoctorFindingStatus.FAIL
                ),
                detail="pytest exit_code=0",
            ),
        ),
        exit_code=exit_code,
    )


def test_json_output_is_machine_readable(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "run_static_checks", lambda *args, **kwargs: _report(DoctorExitCode.OK))

    exit_code = cli.main(["--check", "SGI004", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "schema_version": "architecture-doctor.v1",
        "mode": "static",
        "exit_code": 0,
        "results": [
            {
                "finding_id": "SGI004",
                "title": "PortfolioSnapshot mantém um único writer canônico",
                "severity": "error",
                "status": "pass",
                "detail": "pytest exit_code=0",
            }
        ],
    }


def test_human_output_and_exit_code_are_preserved(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "run_static_checks",
        lambda *args, **kwargs: _report(DoctorExitCode.FINDINGS),
    )

    exit_code = cli.main(["--all-static"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "[FAIL] SGI004" in output
    assert "Architecture Doctor exit_code=1" in output


def test_selection_is_explicit_and_static_only() -> None:
    with pytest.raises(SystemExit) as missing:
        cli.main([])
    with pytest.raises(SystemExit) as non_static:
        cli.main(["--check", "SGI001"])

    assert missing.value.code == 2
    assert non_static.value.code == 2
