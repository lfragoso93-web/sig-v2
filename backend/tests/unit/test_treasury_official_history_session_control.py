from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import treasury_official_history_service as service


@pytest.mark.asyncio
async def test_external_session_with_commit_false_never_commits(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
    runner = AsyncMock(return_value={"imported": 0})
    monkeypatch.setattr(service, "_rebuild_official_treasury_history", runner)

    result = await service.rebuild_official_treasury_history(db, commit=False)

    assert result == {"imported": 0}
    runner.assert_awaited_once_with(db, commit=False)
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_external_session_preserves_default_commit(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
    runner = AsyncMock(return_value={"imported": 2})
    monkeypatch.setattr(service, "_rebuild_official_treasury_history", runner)

    result = await service.rebuild_official_treasury_history(db)

    assert result == {"imported": 2}
    runner.assert_awaited_once_with(db, commit=True)


class _OwnedSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


@pytest.mark.asyncio
async def test_owned_session_keeps_backward_compatible_entrypoint(monkeypatch):
    owned = _OwnedSession()
    runner = AsyncMock(return_value={"imported": 1})
    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: owned)
    monkeypatch.setattr(service, "_rebuild_official_treasury_history", runner)

    result = await service.rebuild_official_treasury_history()

    assert result == {"imported": 1}
    runner.assert_awaited_once_with(owned, commit=True)


@pytest.mark.asyncio
async def test_internal_runner_commits_only_once_at_the_end(monkeypatch):
    asset = SimpleNamespace(id=4810, ticker="tesouro-selic-2029")
    db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        service,
        "_canonical_assets",
        AsyncMock(return_value=({asset.ticker: asset}, {asset.ticker: []}, [])),
    )
    monkeypatch.setattr(service, "_last_saved_date", AsyncMock(return_value=None))
    monkeypatch.setattr(
        service,
        "_first_official_saved_date",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        service,
        "fetch_official_treasury_history",
        AsyncMock(return_value={asset.ticker: []}),
    )
    monkeypatch.setattr(service, "is_brapi_treasury_symbol", lambda _symbol: False)
    monkeypatch.setattr(service, "refresh_asset_last_prices", AsyncMock(return_value=0))

    await service._rebuild_official_treasury_history(db, commit=True)

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_internal_runner_skips_commit_when_disabled(monkeypatch):
    asset = SimpleNamespace(id=4810, ticker="tesouro-selic-2029")
    db = SimpleNamespace(commit=AsyncMock())

    monkeypatch.setattr(
        service,
        "_canonical_assets",
        AsyncMock(return_value=({asset.ticker: asset}, {asset.ticker: []}, [])),
    )
    monkeypatch.setattr(service, "_last_saved_date", AsyncMock(return_value=None))
    monkeypatch.setattr(
        service,
        "_first_official_saved_date",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        service,
        "fetch_official_treasury_history",
        AsyncMock(return_value={asset.ticker: []}),
    )
    monkeypatch.setattr(service, "is_brapi_treasury_symbol", lambda _symbol: False)
    monkeypatch.setattr(service, "refresh_asset_last_prices", AsyncMock(return_value=0))

    await service._rebuild_official_treasury_history(db, commit=False)

    db.commit.assert_not_awaited()
