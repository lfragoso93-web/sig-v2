"""Testes unitários para o serviço de atualização de fundamentos e indicadores (Issue #130)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.asset_fundamentals_refresh_service import (
    get_distinct_portfolio_and_catalog_assets,
    run_asset_fundamentals_refresh,
)
from app.services.system_bootstrap_service import (
    _bootstrap_asset_fundamentals,
    run_system_bootstrap,
)


@pytest.mark.asyncio
async def test_get_distinct_portfolio_and_catalog_assets_with_positions():
    """Retorna ativos com posições abertas ou transacionados."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = [
        ("PETR4", "ACAO"),
        ("HGLG11", "FII"),
        ("AAPL", "STOCK"),
        ("BTC", "CRIPTO"),
    ]
    mock_db.execute.return_value = mock_res

    assets = await get_distinct_portfolio_and_catalog_assets(mock_db)
    assert len(assets) == 4
    assert ("PETR4", "ACAO") in assets
    assert ("BTC", "CRIPTO") in assets


@pytest.mark.asyncio
async def test_get_distinct_portfolio_and_catalog_assets_fallback_to_catalog():
    """Em base limpa sem posições, utiliza ativos do catálogo como fallback."""
    mock_db = AsyncMock()
    # Primeira query vazia
    mock_res_empty = MagicMock()
    mock_res_empty.all.return_value = []
    # Segunda query retorna catálogo
    mock_res_catalog = MagicMock()
    mock_res_catalog.all.return_value = [
        ("VALE3", "ACAO"),
        ("KNRI11", "FII"),
    ]
    mock_db.execute.side_effect = [mock_res_empty, mock_res_catalog]

    assets = await get_distinct_portfolio_and_catalog_assets(mock_db, limit_catalog_fallback=10)
    assert len(assets) == 2
    assert ("VALE3", "ACAO") in assets
    assert ("KNRI11", "FII") in assets


@pytest.mark.asyncio
async def test_run_asset_fundamentals_refresh_success():
    """Testa enriquecimento com diferentes tipos de ativos."""
    mock_db = AsyncMock()

    with patch(
        "app.services.asset_fundamentals_refresh_service.get_distinct_portfolio_and_catalog_assets",
        new=AsyncMock(return_value=[
            ("PETR4", "ACAO"),
            ("MXRF11", "FII"),
            ("NVDA", "STOCK"),
            ("BTC", "CRIPTO"),
            ("TESOURO-SELIC-2029", "TESOURO_DIRETO"),
        ]),
    ), patch(
        "app.services.asset_fundamentals_refresh_service.asset_enrichment_service.get_asset_enrichment",
    ) as mock_enrich:
        async def fake_enrich(ticker, asset_type, force_refresh=False):
            if ticker == "BTC":
                return {"crypto_indicators": {"price_usd": 68000}}
            elif "TESOURO" in ticker:
                return {"treasury_indicators": {"taxa_compra": 11.5}}
            elif ticker == "MXRF11":
                return {"fii_indicators": {"pvp": 1.02}}
            elif ticker == "NVDA":
                return {"international_profile": {"currency": "USD"}, "stock_fundamentals": {}}
            else:
                return {"stock_fundamentals": {"pe": 6.5}}

        mock_enrich.side_effect = fake_enrich

        stats = await run_asset_fundamentals_refresh(mock_db, force_refresh=True)

        assert stats["total"] == 5
        assert stats["stock"] == 1
        assert stats["fii"] == 1
        assert stats["intl"] == 1
        assert stats["crypto"] == 1
        assert stats["treasury"] == 1
        assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_run_asset_fundamentals_refresh_with_errors():
    """Garante resiliência a falhas individuais durante o enriquecimento."""
    mock_db = AsyncMock()

    with patch(
        "app.services.asset_fundamentals_refresh_service.get_distinct_portfolio_and_catalog_assets",
        new=AsyncMock(return_value=[
            ("PETR4", "ACAO"),
            ("FAIL11", "FII"),
        ]),
    ), patch(
        "app.services.asset_fundamentals_refresh_service.asset_enrichment_service.get_asset_enrichment",
    ) as mock_enrich:
        async def fake_enrich(ticker, asset_type, force_refresh=False):
            if ticker == "FAIL11":
                raise RuntimeError("API timeout")
            return {"stock_fundamentals": {"pe": 5.0}}

        mock_enrich.side_effect = fake_enrich

        stats = await run_asset_fundamentals_refresh(mock_db, force_refresh=True)

        assert stats["total"] == 2
        assert stats["stock"] == 1
        assert stats["errors"] == 1


@pytest.mark.asyncio
async def test_bootstrap_asset_fundamentals_stage():
    """Testa execução da etapa _bootstrap_asset_fundamentals no pipeline."""
    with patch(
        "app.services.asset_fundamentals_refresh_service.run_asset_fundamentals_refresh",
        new=AsyncMock(return_value={
            "total": 3,
            "stock": 1,
            "fii": 1,
            "intl": 0,
            "crypto": 1,
            "treasury": 0,
            "errors": 0,
        }),
    ):
        result_str = await _bootstrap_asset_fundamentals()
        assert "total=3" in result_str
        assert "acoes_b3=1" in result_str
        assert "cripto=1" in result_str
        assert "erros=0" in result_str


@pytest.mark.asyncio
async def test_run_system_bootstrap_selective_asset_fundamentals():
    """Testa disparo seletivo da nova etapa pelo run_system_bootstrap."""
    with patch(
        "app.services.system_bootstrap_service._bootstrap_asset_fundamentals",
        new=AsyncMock(return_value="total=5 acoes_b3=2 fiis=1 internacional=1 cripto=1 tesouro=0 erros=0"),
    ):
        report = await run_system_bootstrap(
            commit_sha="b" * 40,
            stages=["asset_fundamentals"],
        )

        assert report.ok is True
        assert len(report.stages) == 1
        assert report.stages[0].name == "asset_fundamentals"
        assert "total=5" in report.stages[0].detail
