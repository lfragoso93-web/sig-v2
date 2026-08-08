"""Disparo controlado do bootstrap global a partir de superficies operacionais.

Mantem uma reserva em memoria entre a aceitacao do request administrativo e o
inicio efetivo da BackgroundTask, evitando que duas requisicoes concorrentes
agendem o mesmo bootstrap global.
"""
from __future__ import annotations

from app.services.system_bootstrap_service import SystemBootstrapReport, run_system_bootstrap
from app.services.system_readiness_service import (
    BootstrapReadinessState,
    get_bootstrap_readiness,
)

_launch_reserved = False


def reserve_system_bootstrap_launch() -> bool:
    """Reserva uma execucao; retorna False se ja houver execucao/reserva ativa."""
    global _launch_reserved
    readiness = get_bootstrap_readiness()
    if _launch_reserved or readiness.state is BootstrapReadinessState.RUNNING:
        return False
    _launch_reserved = True
    return True


async def run_reserved_system_bootstrap() -> SystemBootstrapReport:
    """Executa a reserva atual e sempre libera a trava ao terminar."""
    global _launch_reserved
    if not _launch_reserved:
        raise RuntimeError("bootstrap global nao foi reservado")
    try:
        return await run_system_bootstrap()
    finally:
        _launch_reserved = False


def bootstrap_launch_reserved() -> bool:
    return _launch_reserved


def reset_bootstrap_launch_reservation_for_tests() -> None:
    global _launch_reserved
    _launch_reserved = False
