"""Caracteriza capacidades simuladas de preços e Proventos."""

from __future__ import annotations

import pytest

from app.services.asset_bootstrap_contracts import AssetBootstrapRequest
from tests.fixtures.asset_bootstrap_capabilities import (
    income_events_fixture_capability,
    quotes_fixture_capability,
)


@pytest.mark.asyncio
async def test_quotes_fixture_preserves_normalized_request_and_result() -> None:
    capability = quotes_fixture_capability(updated=3, unchanged=7)
    request = AssetBootstrapRequest(ticker="PETR4", asset_type="ACAO")

    result = await capability.execute(request)

    assert capability.requests == [request]
    assert result.capability.value == "quotes"
    assert result.updated == 3
    assert result.unchanged == 7
    assert result.ok is True


@pytest.mark.asyncio
async def test_income_events_fixture_exposes_partial_failure() -> None:
    capability = income_events_fixture_capability(
        warnings=("coverage-gap",),
        errors=("fixture-source-unavailable",),
    )
    request = AssetBootstrapRequest(ticker="MXRF11", asset_type="FII")

    result = await capability.execute(request)

    assert capability.requests == [request]
    assert result.capability.value == "income_events"
    assert result.ok is False
    assert result.warnings == ("coverage-gap",)
    assert result.errors == ("fixture-source-unavailable",)
