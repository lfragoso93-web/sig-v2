"""Caracteriza a política explícita de dependências do bootstrap."""

from __future__ import annotations

import pytest

from app.services.asset_bootstrap_contracts import AssetBootstrapRequest
from app.services.asset_bootstrap_coordinator import AssetBootstrapCoordinator
from tests.fixtures.asset_bootstrap_capabilities import (
    catalog_fixture_capability,
    income_events_fixture_capability,
    quotes_fixture_capability,
)


@pytest.mark.asyncio
async def test_catalog_failure_blocks_quotes_and_income_events() -> None:
    catalog = catalog_fixture_capability(errors=("catalog-unavailable",))
    quotes = quotes_fixture_capability(updated=3)
    income = income_events_fixture_capability(created=2)
    coordinator = AssetBootstrapCoordinator([catalog, quotes, income])

    report = await coordinator.execute(
        AssetBootstrapRequest(ticker="PETR4", asset_type="ACAO")
    )

    assert catalog.requests
    assert quotes.requests == []
    assert income.requests == []
    assert report.ok is False
    assert report.capabilities[1].errors == ("blocked_by_dependency:catalog",)
    assert report.capabilities[2].errors == ("blocked_by_dependency:catalog",)


@pytest.mark.asyncio
async def test_successful_catalog_allows_independent_capabilities() -> None:
    catalog = catalog_fixture_capability(created=1)
    quotes = quotes_fixture_capability(updated=3)
    income = income_events_fixture_capability(created=2)
    coordinator = AssetBootstrapCoordinator([catalog, quotes, income])

    report = await coordinator.execute(
        AssetBootstrapRequest(ticker="MXRF11", asset_type="FII")
    )

    assert report.ok is True
    assert len(quotes.requests) == 1
    assert len(income.requests) == 1
    assert report.coverage.created == 3
    assert report.coverage.updated == 3
