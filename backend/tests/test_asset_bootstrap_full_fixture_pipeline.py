"""Caracteriza o pipeline completo do bootstrap usando apenas fixtures."""

from __future__ import annotations

import pytest

from app.services.asset_bootstrap_contracts import AssetBootstrapRequest
from app.services.asset_bootstrap_coordinator import AssetBootstrapCoordinator
from tests.fixtures.asset_bootstrap_capabilities import (
    catalog_fixture_capability,
    corporate_events_fixture_capability,
    income_events_fixture_capability,
    quotes_fixture_capability,
)


@pytest.mark.asyncio
async def test_full_fixture_pipeline_reaches_corporate_events() -> None:
    catalog = catalog_fixture_capability(created=1)
    quotes = quotes_fixture_capability(created=3)
    income = income_events_fixture_capability(created=2)
    corporate = corporate_events_fixture_capability(created=4)

    report = await AssetBootstrapCoordinator(
        [catalog, quotes, income, corporate]
    ).execute(AssetBootstrapRequest(ticker=" petr4 ", asset_type=" acao "))

    assert report.ok is True
    assert [item.capability.value for item in report.capabilities] == [
        "catalog",
        "quotes",
        "income_events",
        "corporate_events",
    ]
    assert report.coverage.created == 10
    assert report.coverage.failed_capabilities == ()
    assert corporate.requests[0].ticker == "PETR4"
    assert corporate.requests[0].asset_type == "ACAO"


@pytest.mark.asyncio
async def test_corporate_events_failure_is_preserved_in_coverage() -> None:
    report = await AssetBootstrapCoordinator(
        [
            catalog_fixture_capability(),
            quotes_fixture_capability(),
            income_events_fixture_capability(),
            corporate_events_fixture_capability(errors=("fixture_conflict",)),
        ]
    ).execute(AssetBootstrapRequest(ticker="VALE3", asset_type="ACAO"))

    assert report.ok is False
    assert report.coverage.failed_capabilities == ("corporate_events",)
    assert report.coverage.errors == 1
    assert report.capabilities[-1].errors == ("fixture_conflict",)
