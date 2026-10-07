from pathlib import Path

import pytest

from app.doctor import static_runner
from app.doctor.contracts import DoctorExitCode, DoctorFindingStatus
from app.doctor.contracts import DoctorCatalogEntry, DoctorCheckKind, DoctorSeverity
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


def test_runner_executes_packaged_backend_layout(tmp_path: Path) -> None:
    evidence = tmp_path / "tests" / "test_portfolio_snapshot_single_writer_policy.py"
    evidence.parent.mkdir()
    evidence.write_text("# packaged static evidence\n", encoding="utf-8")
    calls: list[tuple[tuple[str, ...], Path]] = []

    def executor(command: tuple[str, ...], cwd: Path) -> StaticCheckExecution:
        calls.append((command, cwd))
        return StaticCheckExecution(0)

    report = run_static_checks(
        ["SGI004"], repository_root=tmp_path, executor=executor
    )

    assert report.exit_code is DoctorExitCode.OK
    assert calls[0][1] == tmp_path
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


def test_runner_batches_and_deduplicates_green_static_evidence() -> None:
    calls: list[tuple[str, ...]] = []

    def executor(command: tuple[str, ...], cwd: Path) -> StaticCheckExecution:
        calls.append(command)
        return StaticCheckExecution(0)

    report = run_static_checks(
        ["SGI002", "SGI009"],
        repository_root=REPOSITORY_ROOT,
        executor=executor,
    )

    assert report.exit_code is DoctorExitCode.OK
    assert len(calls) == 1
    assert sum(
        Path(argument).as_posix()
        == "tests/test_removed_model_consumers_and_main_import.py"
        for argument in calls[0]
    ) == 1
    assert [result.detail for result in report.results] == [
        "pytest batch exit_code=0",
        "pytest batch exit_code=0",
    ]


def test_runner_falls_back_to_isolation_after_batch_failure() -> None:
    executions = iter(
        (
            StaticCheckExecution(1, "batch failed"),
            StaticCheckExecution(0),
            StaticCheckExecution(1, "SGI009 failed"),
        )
    )

    report = run_static_checks(
        ["SGI002", "SGI009"],
        repository_root=REPOSITORY_ROOT,
        executor=lambda command, cwd: next(executions),
    )

    assert report.exit_code is DoctorExitCode.FINDINGS
    assert [result.status for result in report.results] == [
        DoctorFindingStatus.PASS,
        DoctorFindingStatus.FAIL,
    ]
    assert "SGI009 failed" in report.results[1].detail


def test_inconsistent_batch_and_isolated_results_fail_closed() -> None:
    executions = iter(
        (
            StaticCheckExecution(1, "batch failed"),
            StaticCheckExecution(0),
            StaticCheckExecution(0),
        )
    )

    report = run_static_checks(
        ["SGI002", "SGI009"],
        repository_root=REPOSITORY_ROOT,
        executor=lambda command, cwd: next(executions),
    )

    assert report.exit_code is DoctorExitCode.INTERNAL_ERROR
    assert all(
        result.status is DoctorFindingStatus.ERROR for result in report.results
    )


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


def test_artificial_architecture_violation_returns_findings(
    tmp_path: Path, monkeypatch
) -> None:
    evidence = (
        tmp_path
        / "backend"
        / "tests"
        / "test_artificial_architecture_violation.py"
    )
    evidence.parent.mkdir(parents=True)
    evidence.write_text(
        "def test_architecture_violation():\n    assert False, 'artificial violation'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        static_runner,
        "architecture_check_by_id",
        {
            "SGI900": DoctorCatalogEntry(
                finding_id="SGI900",
                title="Violação arquitetural artificial",
                severity=DoctorSeverity.ERROR,
                kind=DoctorCheckKind.STATIC,
                evidence=(
                    "backend/tests/test_artificial_architecture_violation.py",
                ),
            )
        },
    )

    report = run_static_checks(["SGI900"], repository_root=tmp_path)

    assert report.exit_code is DoctorExitCode.FINDINGS
    assert report.results[0].status is DoctorFindingStatus.FAIL
    assert "artificial violation" in report.results[0].detail
