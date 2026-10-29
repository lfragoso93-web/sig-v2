"""Testes unitários para o catálogo e histórico de preços internacionais no bootstrap."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.asset import AssetType
from app.services.international_catalog_service import (
    InternationalCatalogSyncResult,
    seed_international_catalog,
)
from app.services.international_price_history_service import (
    run_international_price_history_backfill,
)
from app.services.international_universe_service import (
    SupportedInternationalAsset,
    fetch_supported_international_universe,
)
from app.services.system_bootstrap_service import (
    _bootstrap_international_catalog,
    _bootstrap_international_price_history,
    run_system_bootstrap,
)


@pytest.mark.asyncio
async def test_fetch_supported_international_universe_combines_base_and_db():
    """Garante que a lista inclui stocks e ETFs base, além de ativos do banco."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    # Ativo extra existente no banco
    mock_res.all.return_value = [
        ("TSM", "Taiwan Semiconductor", AssetType.STOCK.value, "USD"),
    ]
    mock_db.execute.return_value = mock_res

    universe = await fetch_supported_international_universe(mock_db)
    tickers = {a.ticker for a in universe}

    # Verifica principais ativos base
    assert "AAPL" in tickers
    assert "NVDA" in tickers
    assert "VOO" in tickers
    assert "QQQ" in tickers
    # Verifica ativo vindo do banco
    assert "TSM" in tickers


@pytest.mark.asyncio
async def test_seed_international_catalog_creates_and_updates():
    """Testa semeadura de catálogo internacional com inserções e atualizações."""
    mock_db = AsyncMock()

    sample_universe = [
        SupportedInternationalAsset("AAPL", "Apple Inc.", AssetType.STOCK.value, "USD"),
        SupportedInternationalAsset("VOO", "Vanguard S&P 500 ETF", AssetType.ETF_INTERNACIONAL.value, "USD"),
    ]

    with patch(
        "app.services.international_catalog_service.fetch_supported_international_universe",
        new=AsyncMock(return_value=sample_universe),
    ):
        # Primeiro ativo novo, segundo já existente
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.side_effect = [
            None,  # AAPL novo
            MagicMock(name="", currency="BRL"),  # VOO existente precisando de update
        ]
        mock_db.execute.return_value = mock_scalar

        result = await seed_international_catalog(mock_db)

        assert result.total == 2
        assert result.created == 1
        assert result.updated == 1
        assert result.errors == 0


@pytest.mark.asyncio
async def test_run_international_price_history_backfill():
    """Testa orquestração do backfill histórico de preços para ativos internacionais."""
    mock_db = AsyncMock()

    with patch(
        "app.services.international_price_history_service.fetch_international_tickers",
        new=AsyncMock(return_value={"AAPL", "MSFT", "VOO"}),
    ), patch(
        "app.services.international_price_history_service.run_global_asset_price_backfill",
        new=AsyncMock(return_value={
            "running": False,
            "audited": 3,
            "requested": 3,
            "inserted": 750,
            "errors": 0,
            "skipped": 0,
        }),
    ) as mock_backfill:
        res = await run_international_price_history_backfill(mock_db)

        assert res["total_tickers"] == 3
        assert res["inserted"] == 750
        assert res["audited"] == 3
        mock_backfill.assert_awaited_once_with(
            asset_types={AssetType.STOCK.value, AssetType.ETF_INTERNACIONAL.value},
            tickers={"AAPL", "MSFT", "VOO"},
        )


@pytest.mark.asyncio
async def test_system_bootstrap_international_stages():
    """Testa wrappers de estágio _bootstrap_international_catalog e _bootstrap_international_price_history."""
    with patch(
        "app.services.international_catalog_service.seed_international_catalog",
        new=AsyncMock(return_value=InternationalCatalogSyncResult(
            created=10, updated=2, unchanged=30, total=42, errors=0
        )),
    ):
        cat_str = await _bootstrap_international_catalog()
        assert "total=42" in cat_str
        assert "created=10" in cat_str

    with patch(
        "app.services.international_price_history_service.run_international_price_history_backfill",
        new=AsyncMock(return_value={
            "total_tickers": 42,
            "inserted": 1200,
            "audited": 42,
            "errors": 0,
        }),
    ):
        price_str = await _bootstrap_international_price_history()
        assert "tickers=42" in price_str
        assert "inserted=1200" in price_str


@pytest.mark.asyncio
async def test_run_system_bootstrap_selective_international():
    """Testa disparo seletivo dos novos estágios internacionais via run_system_bootstrap."""
    with patch(
        "app.services.system_bootstrap_service._bootstrap_international_catalog",
        new=AsyncMock(return_value="total=42 created=42 errors=0"),
    ), patch(
        "app.services.system_bootstrap_service._bootstrap_international_price_history",
        new=AsyncMock(return_value="tickers=42 inserted=1500 errors=0"),
    ):
        report = await run_system_bootstrap(
            commit_sha="c" * 40,
            stages=["international_catalog", "international_price_history"],
        )

        assert report.ok is True
        assert len(report.stages) == 2
        assert report.stages[0].name == "international_catalog"
        assert report.stages[1].name == "international_price_history"
        assert "created=42" in report.stages[0].detail
        assert "inserted=1500" in report.stages[1].detail
