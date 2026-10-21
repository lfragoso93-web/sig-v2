"""Estado em memória do bootstrap/readiness do SGI v2.

O processo HTTP pode estar vivo sem que o ambiente esteja liberado para uso
real. O estado READY indica que a versão corrente do bootstrap terminou; a
liberação operacional depende adicionalmente de certificação explícita.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.services.system_bootstrap_stages import (
    CANONICAL_BOOTSTRAP_STAGES,
)


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
    current_stage: str | None = None
    commit_sha: str | None = None
    stage_results: dict[str, dict[str, Any]] = field(default_factory=dict)

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

        stages_payload: list[dict[str, Any]] = []
        for stage_def in CANONICAL_BOOTSTRAP_STAGES:
            res = self.stage_results.get(stage_def.id, {})
            stage_dict = {
                "id": stage_def.id,
                "name": stage_def.name,
                "description": stage_def.description,
                "dependencies": list(stage_def.dependencies),
                "provider_dependent": stage_def.provider_dependent,
                "destructive": stage_def.destructive,
                "status": res.get("status", "idle"),
                "detail": res.get("detail"),
                "last_run_at": res.get("last_run_at"),
                "error": res.get("error"),
            }
            stages_payload.append(stage_dict)
        payload["stages"] = stages_payload
        return payload


_readiness = BootstrapReadiness()


def mark_bootstrap_running(
    *,
    schema_version: str,
    started_at: str,
    commit_sha: str | None = None,
    stages: list[str] | None = None,
) -> None:
    _readiness.state = BootstrapReadinessState.RUNNING
    _readiness.schema_version = schema_version
    _readiness.started_at = started_at
    _readiness.commit_sha = commit_sha
    _readiness.current_stage = None
    _readiness.finished_at = None
    _readiness.failed_stage = None
    _readiness.detail = (
        f"executando bootstrap seletivo ({len(stages)} etapas)"
        if stages
        else "executando bootstrap global"
    )
    _readiness.certified_for_real_data = False
    if stages:
        for s in stages:
            info = _readiness.stage_results.setdefault(s, {})
            info["status"] = "pending"
    else:
        for stage_def in CANONICAL_BOOTSTRAP_STAGES:
            info = _readiness.stage_results.setdefault(stage_def.id, {})
            info["status"] = "pending"


def mark_stage_running(stage_id: str) -> None:
    _readiness.current_stage = stage_id
    info = _readiness.stage_results.setdefault(stage_id, {})
    info["status"] = "running"
    info["started_at"] = datetime.now(timezone.utc).isoformat()


def mark_stage_finished(
    stage_id: str,
    *,
    ok: bool,
    detail: str,
) -> None:
    if _readiness.current_stage == stage_id:
        _readiness.current_stage = None
    info = _readiness.stage_results.setdefault(stage_id, {})
    info["status"] = "success" if ok else "error"
    info["last_run_at"] = datetime.now(timezone.utc).isoformat()
    info["detail"] = detail
    info["error"] = None if ok else detail


def mark_bootstrap_finished(
    report,
    *,
    certified_for_real_data: bool = False,
    is_selective: bool = False,
) -> None:
    _readiness.schema_version = report.schema_version
    _readiness.started_at = report.started_at
    _readiness.finished_at = report.finished_at
    _readiness.current_stage = None
    _readiness.certified_for_real_data = bool(
        certified_for_real_data and report.ok and not is_selective
    )

    for stage in getattr(report, "stages", ()):
        info = _readiness.stage_results.setdefault(stage.name, {})
        info["status"] = "success" if stage.ok else "error"
        info["last_run_at"] = report.finished_at
        info["detail"] = stage.detail
        info["error"] = None if stage.ok else stage.detail

    if is_selective:
        if report.ok:
            if _readiness.state is not BootstrapReadinessState.READY:
                _readiness.state = BootstrapReadinessState.NOT_STARTED
            _readiness.failed_stage = None
            _readiness.detail = (
                f"bootstrap seletivo ({len(report.stages)} etapas) concluído"
            )
        else:
            _readiness.state = BootstrapReadinessState.FAILED
            failed = next((s for s in report.stages if not s.ok), None)
            _readiness.failed_stage = failed.name if failed else None
            _readiness.detail = (
                failed.detail if failed else "falha em bootstrap seletivo"
            )
        return

    if report.ok:
        _readiness.state = BootstrapReadinessState.READY
        _readiness.failed_stage = None
        _readiness.detail = (
            "bootstrap certificado para dados reais"
            if _readiness.certified_for_real_data
            else (
                "bootstrap parcial concluído; certificação operacional "
                "pendente"
            )
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
