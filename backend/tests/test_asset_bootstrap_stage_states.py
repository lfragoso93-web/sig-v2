"""Caracteriza estados de etapa e a capacidade explícita de cobertura."""

from __future__ import annotations

import pytest

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapRequest,
    AssetBootstrapStageState,
)
from app.services.asset_bootstrap_coordinator import AssetBootstrapCoordinator
from tests.fixtures.asset_bootstrap_capabilities import (
    catalog_fixture_capability,
    corporate_events_fixture_capability,
    coverage_fixture_capability,
    income_events_fixture_capability,
    quotes_fixture_capability,
)


@pytest.mark.asyncio
async def test_complete_pipeline_marks_all_stages_executed() -> None:
    capabilities = (
        catalog_fixture_capability(),
        quotes_fixture_capability(),
        income_events_fixture_capability(),
        corporate_events_fixture_capability(),
        coverage_fixture_capability(),
    )

    report = await AssetBootstrapCoordinator(capabilities).execute(
        AssetBootstrapRequest(ticker=" petr4 ", asset_type=" acao ")
    )

    assert report.ok is True
    assert tuple(item.state for item in report.capabilities) == (
        AssetBootstrapStageState.EXECUTED,
        AssetBootstrapStageState.EXECUTED,
        AssetBootstrapStageState.EXECUTED,
        AssetBootstrapStageState.EXECUTED,
        AssetBootstrapStageState.EXECUTED,
    )
    assert report.coverage.failed_capabilities == ()
    assert report.coverage.blocked_capabilities == ()


@pytest.mark.asyncio
async def test_failed_catalog_blocks_all_dependent_stages() -> None:
    catalog = catalog_fixture_capability(errors=("catalog unavailable",))
    quotes = quotes_fixture_capability()
    income_events = income_events_fixture_capability()
    corporate_events = corporate_events_fixture_capability()
    coverage = coverage_fixture_capability()

    report = await AssetBootstrapCoordinator(
        (catalog, quotes, income_events, corporate_events, coverage)
    ).execute(AssetBootstrapRequest(ticker="PETR4", asset_type="ACAO"))

    assert report.capabilities[0].state is AssetBootstrapStageState.FAILED
    assert all(
        item.state is AssetBootstrapStageState.BLOCKED
        for item in report.capabilities[1:]
    )
    assert quotes.requests == []
    assert income_events.requests == []
    assert corporate_events.requests == []
    assert coverage.requests == []
    assert report.coverage.failed_capabilities == ("catalog",)
    assert report.coverage.blocked_capabilities == (
        "quotes",
        "income_events",
        "corporate_events",
        "coverage",
    )


@pytest.mark.asyncio
async def test_coverage_failure_is_reported_as_failed_not_blocked() -> None:
    capabilities = (
        catalog_fixture_capability(),
        quotes_fixture_capability(),
        income_events_fixture_capability(),
        corporate_events_fixture_capability(),
        coverage_fixture_capability(errors=("coverage incomplete",)),
    )

    report = await AssetBootstrapCoordinator(capabilities).execute(
        AssetBootstrapRequest(ticker="PETR4", asset_type="ACAO")
    )

    assert report.ok is False
    assert report.capabilities[-1].state is AssetBootstrapStageState.FAILED
    assert report.coverage.failed_capabilities == ("coverage",)
    assert report.coverage.blocked_capabilities == ()
