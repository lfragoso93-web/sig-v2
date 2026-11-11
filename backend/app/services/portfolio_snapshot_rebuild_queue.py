"""Coordenador single-flight e coalescedor de reconstrucao de snapshots por carteira."""

from __future__ import annotations

import asyncio
import os
from datetime import date

_portfolio_locks: dict[int, asyncio.Lock] = {}
_pending_dates: dict[int, date] = {}
_active_workers: set[int] = set()


def get_coalesce_delay_seconds() -> float:
    """Retorna janela curta de coalescência em produção e zero em suítes de teste."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0.0
    return 0.25


def get_portfolio_snapshot_lock(portfolio_id: int) -> asyncio.Lock:
    """Retorna o lock assíncrono por carteira para serializar escritas de snapshots."""
    lock = _portfolio_locks.get(portfolio_id)
    if lock is None:
        lock = asyncio.Lock()
        _portfolio_locks[portfolio_id] = lock
    return lock


def register_snapshot_rebuild_request(portfolio_id: int, tx_date: date) -> bool:
    """Registra pedido de rebuild preservando a menor data efetiva pendente.

    Retorna ``True`` se o chamador deve assumir a execução do worker da carteira,
    ou ``False`` se já houver um worker ativo que absorverá a data pendente.
    """
    existing = _pending_dates.get(portfolio_id)
    if existing is None or tx_date < existing:
        _pending_dates[portfolio_id] = tx_date

    if portfolio_id in _active_workers:
        return False

    _active_workers.add(portfolio_id)
    return True


def pop_next_snapshot_rebuild_date(portfolio_id: int) -> date | None:
    """Consome atomicamente a próxima data efetiva pendente da carteira."""
    return _pending_dates.pop(portfolio_id, None)


def release_snapshot_rebuild_worker(portfolio_id: int) -> None:
    """Remove o marcador de worker ativo ao encerrar a drenagem da carteira."""
    _active_workers.discard(portfolio_id)


def reset_snapshot_rebuild_state() -> None:
    """Reseta estruturas internas do coordenador para isolamento de testes."""
    _portfolio_locks.clear()
    _pending_dates.clear()
    _active_workers.clear()
