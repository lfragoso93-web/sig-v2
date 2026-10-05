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

__all__ = [
    "ARCHITECTURE_CHECKS",
    "DoctorCheckKind",
    "DoctorExitCode",
    "DoctorFindingResult",
    "DoctorFindingStatus",
    "DoctorSeverity",
    "architecture_check_by_id",
    "resolve_exit_code",
]
