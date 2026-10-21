"""Disparo controlado do bootstrap global a partir de superficies operacionais.

Mantem uma reserva em memoria entre a aceitacao do request administrativo e o
inicio efetivo da BackgroundTask, evitando que duas requisicoes concorrentes
agendem o mesmo bootstrap global. A reserva carrega o SHA auditavel que deve
identificar todas as etapas externas da execucao.
"""
from __future__ import annotations

from typing import Any

from app.services.system_bootstrap_execution_context import (
    build_system_bootstrap_execution_context,
)
from app.services.system_bootstrap_service import (
    SystemBootstrapReport,
    run_system_bootstrap,
)
from app.services.system_readiness_service import (
    BootstrapReadinessState,
    get_bootstrap_readiness,
)

_launch_reserved = False
_reserved_commit_sha: str | None = None
_reserved_stages: list[str] | None = None


def reserve_system_bootstrap_launch(
    commit_sha: str,
    stages: list[str] | None = None,
) -> bool:
    """Reserva uma execução identificada; False se houver ativa."""
    global _launch_reserved, _reserved_commit_sha, _reserved_stages
    build_system_bootstrap_execution_context(commit_sha=commit_sha)
    readiness = get_bootstrap_readiness()
    if _launch_reserved or readiness.state is BootstrapReadinessState.RUNNING:
        return False
    _launch_reserved = True
    _reserved_commit_sha = commit_sha.strip().lower()
    _reserved_stages = list(stages) if stages else None
    return True


async def run_reserved_system_bootstrap() -> SystemBootstrapReport:
    """Executa a reserva atual e sempre libera a trava ao terminar."""
    global _launch_reserved, _reserved_commit_sha, _reserved_stages
    if not _launch_reserved or _reserved_commit_sha is None:
        raise RuntimeError("bootstrap global nao foi reservado")
    commit_sha = _reserved_commit_sha
    stages = _reserved_stages
    kwargs: dict[str, Any] = {"commit_sha": commit_sha}
    if stages is not None:
        kwargs["stages"] = stages
    try:
        return await run_system_bootstrap(**kwargs)
    finally:
        _launch_reserved = False
        _reserved_commit_sha = None
        _reserved_stages = None


def bootstrap_launch_reserved() -> bool:
    return _launch_reserved


def get_reserved_stages() -> list[str] | None:
    return list(_reserved_stages) if _reserved_stages else None


def reset_bootstrap_launch_reservation_for_tests() -> None:
    global _launch_reserved, _reserved_commit_sha, _reserved_stages
    _launch_reserved = False
    _reserved_commit_sha = None
    _reserved_stages = None
