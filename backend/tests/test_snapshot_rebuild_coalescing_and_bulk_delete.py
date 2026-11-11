from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.core.access_context import PortfolioAccessDenied
from app.routers import transactions as tx_router
from app.schemas.transaction import TransactionBulkDeleteRequest
from app.services import portfolio_snapshot_rebuild_queue as rebuild_queue


@pytest.fixture(autouse=True)
def _reset_queue():
    rebuild_queue.reset_snapshot_rebuild_state()
    yield
    rebuild_queue.reset_snapshot_rebuild_state()


@pytest.mark.asyncio
async def test_snapshot_backfill_coalesces_concurrent_requests_by_earliest_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, date]] = []
    running = 0
    max_running = 0

    async def fake_invalidate(db, portfolio_id: int, from_date: date, commit: bool = True) -> int:
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        calls.append((portfolio_id, from_date))
        await asyncio.sleep(0.05)
        running -= 1
        return 1

    async def fake_backfill(db, portfolio_id: int) -> int:
        await asyncio.sleep(0.02)
        return 10

    async def fake_rebuild_classes(db, portfolio_id: int) -> int:
        return 2

    async def fake_invalidate_cache(portfolio_id: int) -> None:
        return None

    class _FakeExecResult:
        def scalar_one_or_none(self):
            return 1

    class _FakeDb:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, *args, **kwargs):
            return _FakeExecResult()

        async def commit(self) -> None:
            return None

    monkeypatch.setattr(tx_router, "AsyncSessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.services.portfolio_snapshot_service.invalidate_snapshots_from",
        fake_invalidate,
    )
    monkeypatch.setattr(
        "app.services.portfolio_snapshot_canonical_twr_service.backfill_canonical_snapshots_with_returns",
        fake_backfill,
    )
    monkeypatch.setattr(
        "app.services.portfolio_class_snapshot_service.rebuild_class_snapshots",
        fake_rebuild_classes,
    )
    monkeypatch.setattr(
        "app.services.rentabilidade_cache_service.invalidate_rentabilidade_cache",
        fake_invalidate_cache,
    )

    # Dispara 10 rebuilds concorrentes para a mesma carteira 65; o primeiro já inicia
    # com 2026-08-10 e os demais devem coalescer pela menor data (2025-04-04) sem sobreposição
    t1 = asyncio.create_task(tx_router._run_snapshot_backfill(65, date(2026, 8, 10)))
    await asyncio.sleep(0.01)  # deixa t1 iniciar a execução
    burst = [
        asyncio.create_task(tx_router._run_snapshot_backfill(65, d))
        for d in (
            date(2026, 5, 1),
            date(2025, 10, 1),
            date(2025, 4, 4),
            date(2026, 1, 15),
            date(2025, 7, 20),
        )
    ]
    await asyncio.gather(t1, *burst)

    assert max_running == 1
    assert calls == [
        (65, date(2026, 8, 10)),
        (65, date(2025, 4, 4)),
    ]


@pytest.mark.asyncio
async def test_bulk_delete_transactions_requires_ids_or_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tx_router,
        "get_accessible_portfolio",
        AsyncMock(return_value=SimpleNamespace(id=65, user_id=16)),
    )
    db = MagicMock()
    user = SimpleNamespace(id=16)

    with pytest.raises(HTTPException) as exc:
        await tx_router.bulk_delete_transactions(
            portfolio_id=65,
            payload=TransactionBulkDeleteRequest(),
            background_tasks=BackgroundTasks(),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_bulk_delete_transactions_rejects_unauthorized_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tx_router,
        "get_accessible_portfolio",
        AsyncMock(side_effect=PortfolioAccessDenied("denied")),
    )
    db = MagicMock()
    user = SimpleNamespace(id=99)

    with pytest.raises(HTTPException) as exc:
        await tx_router.bulk_delete_transactions(
            portfolio_id=65,
            payload=TransactionBulkDeleteRequest(asset_type="RENDA_FIXA"),
            background_tasks=BackgroundTasks(),
            db=db,
            current_user=user,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_transactions_deletes_matching_and_schedules_single_backfill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tx_router,
        "get_accessible_portfolio",
        AsyncMock(return_value=SimpleNamespace(id=65, user_id=16)),
    )

    select_result = MagicMock()
    select_result.all.return_value = [
        (101, date(2025, 8, 10)),
        (102, date(2025, 4, 4)),
        (103, date(2026, 1, 5)),
    ]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[select_result, MagicMock()])
    db.commit = AsyncMock()
    user = SimpleNamespace(id=16)
    bg = BackgroundTasks()

    response = await tx_router.bulk_delete_transactions(
        portfolio_id=65,
        payload=TransactionBulkDeleteRequest(asset_type="RENDA_FIXA"),
        background_tasks=bg,
        db=db,
        current_user=user,
    )

    assert response.deleted_count == 3
    assert response.earliest_date == date(2025, 4, 4)
    assert db.execute.await_count == 2
    assert db.commit.await_count == 1
    assert len(bg.tasks) == 2
    assert bg.tasks[0].func is tx_router._run_snapshot_backfill
    assert bg.tasks[0].kwargs == {"portfolio_id": 65, "tx_date": date(2025, 4, 4)}
    assert bg.tasks[1].func is tx_router.invalidate_portfolio_cache
    assert bg.tasks[1].kwargs == {"portfolio_id": 65}

@pytest.mark.asyncio
async def test_snapshot_backfill_continues_draining_pending_requests_after_iteration_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[date] = []
    attempt = 0

    async def fake_invalidate(db, portfolio_id: int, from_date: date, commit: bool = True) -> int:
        nonlocal attempt
        attempt += 1
        calls.append(from_date)
        if attempt == 1:
            await asyncio.sleep(0.05)
            raise RuntimeError("transient error on first pass")
        return 1

    async def fake_backfill(db, portfolio_id: int) -> int:
        return 5

    async def fake_rebuild_classes(db, portfolio_id: int) -> int:
        return 1

    async def fake_invalidate_cache(portfolio_id: int) -> None:
        return None

    class _FakeExecResult:
        def scalar_one_or_none(self):
            return 1

    class _FakeDb:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, *args, **kwargs):
            return _FakeExecResult()

        async def commit(self) -> None:
            return None

    monkeypatch.setattr(tx_router, "AsyncSessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.services.portfolio_snapshot_service.invalidate_snapshots_from",
        fake_invalidate,
    )
    monkeypatch.setattr(
        "app.services.portfolio_snapshot_canonical_twr_service.backfill_canonical_snapshots_with_returns",
        fake_backfill,
    )
    monkeypatch.setattr(
        "app.services.portfolio_class_snapshot_service.rebuild_class_snapshots",
        fake_rebuild_classes,
    )
    monkeypatch.setattr(
        "app.services.rentabilidade_cache_service.invalidate_rentabilidade_cache",
        fake_invalidate_cache,
    )

    t1 = asyncio.create_task(tx_router._run_snapshot_backfill(65, date(2026, 6, 1)))
    await asyncio.sleep(0.01)
    t2 = asyncio.create_task(tx_router._run_snapshot_backfill(65, date(2025, 1, 1)))
    await asyncio.gather(t1, t2)

    assert calls == [date(2026, 6, 1), date(2025, 1, 1)]
