"""Tipos estáveis para resultados futuros do Architecture Doctor.

Este módulo não executa checks. Ele apenas define o envelope e a semântica de
saída que o runner futuro deverá respeitar.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Collection, Mapping


class DoctorCheckKind(StrEnum):
    STATIC = "static"
    BEHAVIORAL = "behavioral"
    DATABASE = "database"
    RUNTIME = "runtime"


class DoctorSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class DoctorFindingStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class DoctorExitCode(IntEnum):
    OK = 0
    FINDINGS = 1
    INTERNAL_ERROR = 2


@dataclass(frozen=True)
class DoctorCatalogEntry:
    finding_id: str
    title: str
    severity: DoctorSeverity
    kind: DoctorCheckKind
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class DoctorFindingResult:
    finding_id: str
    status: DoctorFindingStatus
    detail: str


def resolve_exit_code(
    results: Collection[DoctorFindingResult],
    catalog: Mapping[str, DoctorCatalogEntry],
) -> DoctorExitCode:
    """Consolida resultados sem transformar ausência de evidência em sucesso."""

    if any(result.finding_id not in catalog for result in results):
        return DoctorExitCode.INTERNAL_ERROR

    if any(result.status is DoctorFindingStatus.ERROR for result in results):
        return DoctorExitCode.INTERNAL_ERROR

    if any(
        result.status is DoctorFindingStatus.SKIP
        and catalog[result.finding_id].severity is DoctorSeverity.ERROR
        for result in results
    ):
        return DoctorExitCode.INTERNAL_ERROR

    if any(
        result.status is DoctorFindingStatus.FAIL
        and catalog[result.finding_id].severity is DoctorSeverity.ERROR
        for result in results
    ):
        return DoctorExitCode.FINDINGS

    return DoctorExitCode.OK
