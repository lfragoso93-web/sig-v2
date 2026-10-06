"""Contratos read-only do Architecture Doctor."""

from app.doctor.catalog import ARCHITECTURE_CHECKS, architecture_check_by_id
from app.doctor.contracts import (
    DoctorCheckKind,
    DoctorExitCode,
    DoctorFindingResult,
    DoctorFindingStatus,
    DoctorSeverity,
    resolve_exit_code,
)
from app.doctor.static_runner import StaticDoctorReport, run_static_checks

__all__ = [
    "ARCHITECTURE_CHECKS",
    "DoctorCheckKind",
    "DoctorExitCode",
    "DoctorFindingResult",
    "DoctorFindingStatus",
    "DoctorSeverity",
    "StaticDoctorReport",
    "architecture_check_by_id",
    "resolve_exit_code",
    "run_static_checks",
]
