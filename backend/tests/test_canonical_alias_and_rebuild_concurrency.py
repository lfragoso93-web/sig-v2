from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.asset import AssetType
from app.services.asset_price_coverage_service import (
    CoverageStatus,
    _canonical_ticker,
    build_missing_ranges,
)


def test_fractional_ticker_resolves_to_base_asset():
    assert _canonical_ticker("PETR4F", AssetType.ACAO) == "PETR4"
    assert _canonical_ticker("ONCO11F", AssetType.FII) == "ONCO11"
    assert _canonical_ticker("PETR4", AssetType.ACAO) is None


def test_canonical_alias_never_generates_price_ranges():
    ranges = build_missing_ranges(
        status=CoverageStatus.CANONICAL_ALIAS,
        required_from=date(1900, 1, 1),
        required_to=date(2026, 7, 14),
        first_price_date=date(2000, 1, 1),
        last_price_date=date(2026, 7, 14),
    )
    assert ranges == ()


def test_unavailable_history_status_does_not_repeat_initial_range():
    ranges = build_missing_ranges(
        status=CoverageStatus.PARTIAL_START,
        required_from=date(1900, 1, 1),
        required_to=date(2026, 7, 14),
        first_price_date=date(2020, 1, 1),
        last_price_date=date(2026, 7, 14),
        provider_status="YAHOO_HISTORY_UNAVAILABLE",
    )
    assert ranges == ()


@pytest.mark.asyncio
async def test_full_rebuild_uses_configured_proventos_concurrency(monkeypatch):
    import app.services.proventos_daily_sync_service as proventos
    from app.services import full_market_rebuild_service as rebuild

    sync = AsyncMock(return_value=SimpleNamespace(errors=[]))
    monkeypatch.setattr(proventos, "SYNC_CONCURRENCY", 10)
    monkeypatch.setattr(proventos, "run_daily_proventos_sync", sync)

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(rebuild, "AsyncSessionLocal", lambda: _Session())

    await rebuild._sync_proventos()
    assert sync.await_args.kwargs["concurrency"] == 10
