from pathlib import Path

import pytest

from app.doctor.contracts import DoctorExitCode, DoctorFindingStatus
from app.doctor.static_runner import StaticCheckExecution, run_static_checks


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_runner_executes_only_requested_static_evidence() -> None:
    calls: list[tuple[tuple[str, ...], Path]] = []

    def executor(command: tuple[str, ...], cwd: Path) -> StaticCheckExecution:
        calls.append((command, cwd))
        return StaticCheckExecution(0)

    report = run_static_checks(
        ["SGI004"], repository_root=REPOSITORY_ROOT, executor=executor
    )

    assert report.exit_code is DoctorExitCode.OK
    assert report.results[0].status is DoctorFindingStatus.PASS
    assert calls[0][1] == REPOSITORY_ROOT / "backend"
    assert calls[0][0][1:6] == (
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
    )
    assert Path(calls[0][0][6]).as_posix() == (
        "tests/test_portfolio_snapshot_single_writer_policy.py"
    )


@pytest.mark.parametrize("finding_id", ["SGI001", "SGI003", "SGI006", "SGI011"])
def test_runner_rejects_non_static_checks_without_execution(finding_id: str) -> None:
    called = False

    def executor(command: tuple[str, ...], cwd: Path) -> StaticCheckExecution:
        nonlocal called
        called = True
        return StaticCheckExecution(0)

    report = run_static_checks(
        [finding_id], repository_root=REPOSITORY_ROOT, executor=executor
    )

    assert report.exit_code is DoctorExitCode.INTERNAL_ERROR
    assert report.results[0].status is DoctorFindingStatus.ERROR
    assert called is False


def test_runner_fails_closed_for_unknown_id() -> None:
    report = run_static_checks(["SGI999"], repository_root=REPOSITORY_ROOT)

    assert report.exit_code is DoctorExitCode.INTERNAL_ERROR
    assert report.results[0].status is DoctorFindingStatus.ERROR


def test_runner_maps_pytest_failure_and_execution_error() -> None:
    failure = run_static_checks(
        ["SGI004"],
        repository_root=REPOSITORY_ROOT,
        executor=lambda command, cwd: StaticCheckExecution(1, "assertion failed"),
    )
    error = run_static_checks(
        ["SGI004"],
        repository_root=REPOSITORY_ROOT,
        executor=lambda command, cwd: StaticCheckExecution(5, "pytest error"),
    )

    assert failure.exit_code is DoctorExitCode.FINDINGS
    assert failure.results[0].status is DoctorFindingStatus.FAIL
    assert "assertion failed" in failure.results[0].detail
    assert error.exit_code is DoctorExitCode.INTERNAL_ERROR
    assert error.results[0].status is DoctorFindingStatus.ERROR
    assert "pytest error" in error.results[0].detail


def test_runner_rejects_empty_or_duplicate_selection() -> None:
    empty = run_static_checks([], repository_root=REPOSITORY_ROOT)
    assert empty.exit_code is DoctorExitCode.INTERNAL_ERROR
    assert empty.results == ()

    with pytest.raises(ValueError, match="duplicados"):
        run_static_checks(
            ["SGI004", "SGI004"], repository_root=REPOSITORY_ROOT
        )


def test_real_static_gate_runs_without_pytest_cache() -> None:
    report = run_static_checks(["SGI004"], repository_root=REPOSITORY_ROOT)

    assert report.exit_code is DoctorExitCode.OK
    assert report.results[0].status is DoctorFindingStatus.PASS
