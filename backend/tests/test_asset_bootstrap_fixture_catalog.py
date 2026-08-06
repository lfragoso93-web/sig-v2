"""Caracteriza catálogo simulado e cobertura agregada do bootstrap."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapabilityName,
    AssetBootstrapCapabilityResult,
    AssetBootstrapRequest,
)
from app.services.asset_bootstrap_coordinator import AssetBootstrapCoordinator
from tests.fixtures.asset_bootstrap_capabilities import (
    FixtureAssetBootstrapCapability,
    catalog_fixture_capability,
)


@pytest.mark.asyncio
async def test_fixture_catalog_receives_normalized_request() -> None:
    catalog = catalog_fixture_capability(created=1)
    coordinator = AssetBootstrapCoordinator([catalog])

    report = await coordinator.execute(
        AssetBootstrapRequest(ticker=" petr4 ", asset_type="acao")
    )

    assert catalog.requests == [
        AssetBootstrapRequest(ticker="PETR4", asset_type="ACAO")
    ]
    assert report.ok is True
    assert report.coverage.total_capabilities == 1
    assert report.coverage.successful_capabilities == 1
    assert report.coverage.created == 1
    assert report.coverage.failed_capabilities == ()


@pytest.mark.asyncio
async def test_coverage_aggregates_partial_failure_without_losing_results() -> None:
    catalog = catalog_fixture_capability(created=1, warnings=("alias_missing",))
    quotes = FixtureAssetBootstrapCapability(
        name=AssetBootstrapCapabilityName.QUOTES,
        result=AssetBootstrapCapabilityResult(
            capability=AssetBootstrapCapabilityName.QUOTES,
            ok=False,
            unchanged=3,
            errors=("fixture_quote_gap",),
        ),
    )
    coordinator = AssetBootstrapCoordinator([catalog, quotes])

    report = await coordinator.execute(
        AssetBootstrapRequest(ticker="VALE3", asset_type="ACAO")
    )

    assert report.ok is False
    assert [item.capability for item in report.capabilities] == [
        AssetBootstrapCapabilityName.CATALOG,
        AssetBootstrapCapabilityName.QUOTES,
    ]
    assert report.coverage.total_capabilities == 2
    assert report.coverage.successful_capabilities == 1
    assert report.coverage.failed_capabilities == ("quotes",)
    assert report.coverage.created == 1
    assert report.coverage.unchanged == 3
    assert report.coverage.warnings == 1
    assert report.coverage.errors == 1


def test_fixture_capabilities_have_no_provider_or_database_dependency() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "asset_bootstrap_capabilities.py"
    )
    source = fixture_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )

    assert not {
        "sqlalchemy",
        "requests",
        "httpx",
        "app.models",
    }.intersection(imported_modules)
    assert "AsyncSession" not in source
    assert "brapi" not in source.lower()
    assert "yahoo" not in source.lower()
