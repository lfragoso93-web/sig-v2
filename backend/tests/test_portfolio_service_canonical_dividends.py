"""Canonical dividend aggregation boundaries in portfolio_service."""

from __future__ import annotations

import ast
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.services.portfolio_service import (
    sum_dividends,
    sum_dividends_by_ticker,
    sum_dividends_for_tickers,
)

SERVICE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "services" / "portfolio_service.py"
)


@pytest.mark.asyncio
async def test_sum_dividends_delegates_to_canonical_entitlements() -> None:
    entitlements = [object()]
    with (
        patch(
            "app.services.portfolio_service.load_portfolio_dividend_entitlements",
            new=AsyncMock(return_value=entitlements),
        ) as load,
        patch(
            "app.services.portfolio_service.aggregate_received_entitlements",
            return_value=Decimal("125.50"),
        ) as aggregate,
    ):
        total = await sum_dividends(
            AsyncMock(),
            portfolio_id=7,
            cutoff=date(2026, 1, 1),
        )

    assert total == 125.5
    load.assert_awaited_once()
    aggregate.assert_called_once_with(
        entitlements,
        cutoff=date(2026, 1, 1),
        as_of=datetime.now(timezone.utc).date(),
    )


@pytest.mark.asyncio
async def test_ticker_totals_are_normalized_by_canonical_aggregator() -> None:
    canonical_totals = {"PETR4": 10.25, "VALE3": 20.0}
    loader = AsyncMock(return_value=canonical_totals)
    with patch(
        "app.services.portfolio_service.load_received_entitlements_by_ticker",
        new=loader,
    ):
        by_ticker = await sum_dividends_by_ticker(
            AsyncMock(),
            portfolio_id=7,
            tickers=["petr4", "VALE3"],
        )
        total = await sum_dividends_for_tickers(
            AsyncMock(),
            portfolio_id=7,
            tickers=["petr4", "VALE3"],
        )

    assert by_ticker == canonical_totals
    assert total == 30.25
    assert loader.await_count == 2
    assert all(
        call.kwargs["as_of"] == datetime.now(timezone.utc).date()
        for call in loader.await_args_list
    )


@pytest.mark.asyncio
async def test_empty_ticker_requests_do_not_load_entitlements() -> None:
    loader = AsyncMock()
    with patch(
        "app.services.portfolio_service.load_received_entitlements_by_ticker",
        new=loader,
    ):
        assert await sum_dividends_by_ticker(AsyncMock(), 7, []) == {}
        assert await sum_dividends_for_tickers(AsyncMock(), 7, []) == 0.0

    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_dividend_aggregations_propagate_reader_failures() -> None:
    failure = RuntimeError("canonical dividend reader unavailable")
    with (
        patch(
            "app.services.portfolio_service.load_portfolio_dividend_entitlements",
            new=AsyncMock(side_effect=failure),
        ),
        patch(
            "app.services.portfolio_service.load_received_entitlements_by_ticker",
            new=AsyncMock(side_effect=failure),
        ),
    ):
        with pytest.raises(RuntimeError, match="reader unavailable"):
            await sum_dividends(AsyncMock(), 7)
        with pytest.raises(RuntimeError, match="reader unavailable"):
            await sum_dividends_for_tickers(AsyncMock(), 7, ["PETR4"])
        with pytest.raises(RuntimeError, match="reader unavailable"):
            await sum_dividends_by_ticker(AsyncMock(), 7, ["PETR4"])


def test_portfolio_aggregations_do_not_access_legacy_dividends() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    aggregation_names = {
        "sum_dividends",
        "sum_dividends_for_tickers",
        "sum_dividends_by_ticker",
    }
    aggregations = [
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name in aggregation_names
    ]

    assert {node.name for node in aggregations} == aggregation_names
    for aggregation in aggregations:
        aggregation_source = ast.get_source_segment(source, aggregation) or ""
        imported_modules = {
            node.module
            for node in ast.walk(aggregation)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        imported_names = {
            alias.name
            for node in ast.walk(aggregation)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        called_attributes = {
            node.func.attr
            for node in ast.walk(aggregation)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }

        assert "app.models.dividend" not in imported_modules
        assert "Dividend" not in imported_names
        assert "Dividend" not in aggregation_source
        assert "rollback" not in called_attributes
        assert not any(isinstance(node, ast.Try) for node in ast.walk(aggregation))
