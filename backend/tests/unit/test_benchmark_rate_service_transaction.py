from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import benchmark_rate_service


@pytest.mark.asyncio
async def test_import_missing_benchmark_history_preserves_default_commit(monkeypatch) -> None:
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: 0)),
        commit=AsyncMock(),
    )
    monkeypatch.setattr(
        benchmark_rate_service,
        "import_benchmark_history",
        AsyncMock(return_value={"CDI": 1}),
    )
    monkeypatch.setattr(
        benchmark_rate_service,
        "SGS_INDICATORS",
        {"CDI": 12},
    )

    result = await benchmark_rate_service.import_missing_benchmark_history(
        db,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
    )

    assert result == {"CDI": 1}
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_missing_benchmark_history_allows_external_transaction(monkeypatch) -> None:
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: 0)),
        commit=AsyncMock(),
    )
    import_history = AsyncMock(return_value={"CDI": 1})
    monkeypatch.setattr(
        benchmark_rate_service,
        "import_benchmark_history",
        import_history,
    )
    monkeypatch.setattr(
        benchmark_rate_service,
        "SGS_INDICATORS",
        {"CDI": 12},
    )

    result = await benchmark_rate_service.import_missing_benchmark_history(
        db,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        commit=False,
    )

    assert result == {"CDI": 1}
    db.commit.assert_not_awaited()
    import_history.assert_awaited_once_with(
        db,
        indicators=["CDI"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        commit=False,
    )
