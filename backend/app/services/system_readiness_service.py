"""Estado em memória do bootstrap/readiness do SGI v2.

O processo HTTP pode estar vivo sem que o ambiente esteja liberado para uso
real. O estado READY indica que a versão corrente do bootstrap terminou; a
liberação operacional depende adicionalmente de certificação explícita.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class BootstrapReadinessState(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


@dataclass
class BootstrapReadiness:
    state: BootstrapReadinessState = BootstrapReadinessState.NOT_STARTED
    schema_version: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    failed_stage: str | None = None
    detail: str | None = None
    certified_for_real_data: bool = False

    @property
    def bootstrap_complete(self) -> bool:
        return self.state is BootstrapReadinessState.READY

    @property
    def ready_for_real_data(self) -> bool:
        return self.bootstrap_complete and self.certified_for_real_data

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        payload["bootstrap_complete"] = self.bootstrap_complete
        payload["ready_for_real_data"] = self.ready_for_real_data
        return payload


_readiness = BootstrapReadiness()


def mark_bootstrap_running(*, schema_version: str, started_at: str) -> None:
    _readiness.state = BootstrapReadinessState.RUNNING
    _readiness.schema_version = schema_version
    _readiness.started_at = started_at
    _readiness.finished_at = None
    _readiness.failed_stage = None
    _readiness.detail = None
    _readiness.certified_for_real_data = False


def mark_bootstrap_finished(report, *, certified_for_real_data: bool = False) -> None:
    _readiness.schema_version = report.schema_version
    _readiness.started_at = report.started_at
    _readiness.finished_at = report.finished_at
    _readiness.certified_for_real_data = bool(certified_for_real_data and report.ok)
    if report.ok:
        _readiness.state = BootstrapReadinessState.READY
        _readiness.failed_stage = None
        _readiness.detail = (
            "bootstrap certificado para dados reais"
            if _readiness.certified_for_real_data
            else "bootstrap parcial concluído; certificação operacional pendente"
        )
        return

    _readiness.state = BootstrapReadinessState.FAILED
    failed = next((stage for stage in report.stages if not stage.ok), None)
    _readiness.failed_stage = failed.name if failed else None
    _readiness.detail = failed.detail if failed else "bootstrap incompleto"


def mark_bootstrap_disabled(*, detail: str) -> None:
    _readiness.state = BootstrapReadinessState.NOT_STARTED
    _readiness.detail = detail
    _readiness.certified_for_real_data = False


def get_bootstrap_readiness() -> BootstrapReadiness:
    return _readiness


def reset_bootstrap_readiness_for_tests() -> None:
    global _readiness
    _readiness = BootstrapReadiness()
