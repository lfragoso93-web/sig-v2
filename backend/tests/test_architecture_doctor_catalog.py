import re
from pathlib import Path

from app.doctor.catalog import ARCHITECTURE_CHECKS, architecture_check_by_id
from app.doctor.contracts import (
    DoctorCatalogEntry,
    DoctorCheckKind,
    DoctorExitCode,
    DoctorFindingResult,
    DoctorFindingStatus,
    DoctorSeverity,
    resolve_exit_code,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _result(finding_id: str, status: DoctorFindingStatus) -> DoctorFindingResult:
    return DoctorFindingResult(finding_id=finding_id, status=status, detail="test")


def test_catalog_has_stable_unique_ordered_ids_and_existing_evidence() -> None:
    finding_ids = [entry.finding_id for entry in ARCHITECTURE_CHECKS]

    assert finding_ids == sorted(finding_ids)
    assert len(finding_ids) == len(set(finding_ids))
    assert all(re.fullmatch(r"SGI\d{3}", finding_id) for finding_id in finding_ids)
    assert set(architecture_check_by_id) == set(finding_ids)
    assert all(entry.evidence for entry in ARCHITECTURE_CHECKS)
    assert all(
        (REPOSITORY_ROOT / evidence).is_file()
        for entry in ARCHITECTURE_CHECKS
        for evidence in entry.evidence
    )


def test_error_severity_failure_is_blocking() -> None:
    assert (
        resolve_exit_code(
            [_result("SGI001", DoctorFindingStatus.FAIL)], architecture_check_by_id
        )
        is DoctorExitCode.FINDINGS
    )


def test_error_or_blocking_skip_is_internal_error() -> None:
    assert (
        resolve_exit_code(
            [_result("SGI001", DoctorFindingStatus.ERROR)], architecture_check_by_id
        )
        is DoctorExitCode.INTERNAL_ERROR
    )
    assert (
        resolve_exit_code(
            [_result("SGI001", DoctorFindingStatus.SKIP)], architecture_check_by_id
        )
        is DoctorExitCode.INTERNAL_ERROR
    )


def test_unknown_finding_is_internal_error() -> None:
    assert (
        resolve_exit_code(
            [_result("SGI999", DoctorFindingStatus.PASS)], architecture_check_by_id
        )
        is DoctorExitCode.INTERNAL_ERROR
    )


def test_warning_failure_or_skip_does_not_block() -> None:
    warning_catalog = {
        "SGI900": DoctorCatalogEntry(
            finding_id="SGI900",
            title="Advisory",
            severity=DoctorSeverity.WARNING,
            kind=DoctorCheckKind.STATIC,
            evidence=("backend/tests/test_architecture_doctor_catalog.py",),
        )
    }

    assert (
        resolve_exit_code(
            [_result("SGI900", DoctorFindingStatus.FAIL)], warning_catalog
        )
        is DoctorExitCode.OK
    )
    assert (
        resolve_exit_code(
            [_result("SGI900", DoctorFindingStatus.SKIP)], warning_catalog
        )
        is DoctorExitCode.OK
    )
