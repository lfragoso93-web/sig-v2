"""Testes do serviço batch do pipeline único de mercado."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services.market_pipeline_batch_service import (
    is_market_pipeline_ticker,
    load_market_pipeline_pairs,
    run_market_pipeline_batch,
)


async def _make_tx(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str,
    op: OperationType = OperationType.buy,
) -> Transaction:
    tx = Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=asset_type,
        operation=op,
        quantity=10,
        price=10,
        date=date(2024, 1, 1),
    )
    db.add(tx)
    await db.flush()
    return tx


class TestMarketPipelineTickerFilter:
    @pytest.mark.parametrize(
        "ticker,expected",
        [
            ("PETR4", True),
            ("BBAS3", True),
            ("MXRF11", True),
            ("ALUP11", True),
            ("B3SA3F", False),
            ("PETR4F", False),
            ("AZUL97", False),
            ("ABCD3R", False),
        ],
    )
    def test_is_market_pipeline_ticker(self, ticker: str, expected: bool):
        assert is_market_pipeline_ticker(ticker) is expected


@pytest.mark.asyncio
class TestLoadMarketPipelinePairs:
    async def test_only_held_filtra_tipos_e_tickers_especiais(self, db: AsyncSession, portfolio: Portfolio):
        await _make_tx(db, portfolio.id, "PETR4", "ACAO")
        await _make_tx(db, portfolio.id, "MXRF11", "FII")
        await _make_tx(db, portfolio.id, "PETR4F", "ACAO")
        await _make_tx(db, portfolio.id, "BTC", "CRIPTO")

        pairs, skipped = await load_market_pipeline_pairs(db, only_held=True)

        assert ("PETR4", Asset.__table__.columns.asset_type.type.python_type("ACAO")) not in pairs  # sanity: raw string is normalized below
        assert pairs == [("PETR4", __import__("app.models.asset", fromlist=["AssetType"]).AssetType.ACAO), ("MXRF11", __import__("app.models.asset", fromlist=["AssetType"]).AssetType.FII)]
        assert skipped == 1

    async def test_tickers_usa_assets_e_respeita_asset_type(self, db: AsyncSession):
        from app.models.asset import AssetType

        db.add_all([
            Asset(ticker="PETR4", name="PETR4", asset_type="ACAO", currency="BRL"),
            Asset(ticker="MXRF11", name="MXRF11", asset_type="FII", currency="BRL"),
            Asset(ticker="BTC", name="BTC", asset_type="CRIPTO", currency="BRL"),
        ])
        await db.flush()

        pairs, skipped = await load_market_pipeline_pairs(
            db,
            asset_types={AssetType.ACAO, AssetType.FII},
            only_held=False,
            tickers=["PETR4", "MXRF11", "BTC"],
        )

        assert pairs == [("PETR4", AssetType.ACAO), ("MXRF11", AssetType.FII)]
        assert skipped == 0


@pytest.mark.asyncio
class TestRunMarketPipelineBatch:
    async def test_roda_pipeline_para_ativos_elegiveis(self, db: AsyncSession, portfolio: Portfolio):
        from app.models.asset import AssetType

        await _make_tx(db, portfolio.id, "PETR4", "ACAO")
        await _make_tx(db, portfolio.id, "MXRF11", "FII")
        await _make_tx(db, portfolio.id, "B3SA3F", "ACAO")

        calls: list[tuple[str, str, bool]] = []

        async def fake_sync_asset_market_data(**kwargs):
            calls.append((kwargs["ticker"], kwargs["asset_type"].value, kwargs["full"]))
            return object()

        with patch(
            "app.services.market_pipeline_batch_service.sync_asset_market_data",
            new_callable=AsyncMock,
            side_effect=fake_sync_asset_market_data,
        ):
            result = await run_market_pipeline_batch(
                db,
                asset_types={AssetType.ACAO, AssetType.FII},
                only_held=True,
                full=False,
                concurrency=1,
            )

        assert result.candidates == 3
        assert result.eligible == 2
        assert result.skipped == 1
        assert result.ok == 2
        assert result.failed == 0
        assert result.errors == []
        assert calls == [("PETR4", "ACAO", False), ("MXRF11", "FII", False)]

    async def test_registra_falha_e_continua_lote(self, db: AsyncSession, portfolio: Portfolio):
        from app.models.asset import AssetType

        await _make_tx(db, portfolio.id, "BBAS3", "ACAO")
        await _make_tx(db, portfolio.id, "PETR4", "ACAO")

        async def fake_sync_asset_market_data(**kwargs):
            if kwargs["ticker"] == "BBAS3":
                raise RuntimeError("erro controlado")
            return object()

        with patch(
            "app.services.market_pipeline_batch_service.sync_asset_market_data",
            new_callable=AsyncMock,
            side_effect=fake_sync_asset_market_data,
        ):
            result = await run_market_pipeline_batch(
                db,
                asset_types={AssetType.ACAO},
                only_held=True,
                full=False,
                concurrency=1,
            )

        assert result.ok == 1
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "BBAS3/ACAO" in result.errors[0]
