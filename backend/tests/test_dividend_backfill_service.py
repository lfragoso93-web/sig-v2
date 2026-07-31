"""
Testes de integração para dividend_backfill_service.py.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services.dividend_backfill_service import (
    SKIP_TYPES,
    _parse_raw_dividend,
    backfill_dividends,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_tx(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    op: OperationType,
    qty: float,
    tx_date: date,
) -> Transaction:
    tx = Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        operation=op,
        quantity=qty,
        date=tx_date,
        price=Decimal("10.00"),
        asset_type="ACAO",
    )
    db.add(tx)
    await db.flush()
    return tx


class TestParseRawDividend:
    def test_parse_cash_dividend_brapi_com_data_com(self):
        raw = {
            "lastDatePrior": "2024-03-01",
            "paymentDate": "2024-03-15",
            "rate": 1.25,
            "label": "Dividendos",
            "eventCategory": "cash",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        assert result.record_date == date(2024, 3, 1)
        assert result.ex_date == date(2024, 3, 4)  # próximo dia útil após sexta-feira
        assert result.payment_date == date(2024, 3, 15)
        assert result.value_per_unit == 1.25
        assert result.dividend_type == "DIVIDENDO"

    def test_parse_cash_dividend_brapi_com_ex_date_explicito(self):
        raw = {
            "lastDatePrior": "2024-03-01",
            "exDate": "2024-03-04",
            "paymentDate": "2024-03-15",
            "rate": 1.25,
            "label": "Dividendos",
            "eventCategory": "cash",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        assert result.record_date == date(2024, 3, 1)
        assert result.ex_date == date(2024, 3, 4)

    def test_parse_jcp_por_label(self):
        raw = {
            "lastDatePrior": "2024-05-01",
            "paymentDate": "2024-05-15",
            "rate": 2.0,
            "label": "Juros Sobre Capital Próprio",
            "eventCategory": "cash",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        assert result.dividend_type == "JCP"

    def test_parse_bonificacao_stock_dividend_sem_valor_cash(self):
        raw = {
            "lastDatePrior": "2024-06-10",
            "approvedOn": "2024-06-01",
            "label": "Bonificação",
            "factor": 0.10,
            "completeFactor": 1.10,
            "eventCategory": "stock",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        assert result.dividend_type == "BONIFICACAO"
        assert result.value_per_unit == 0.0
        assert result.factor == 0.10
        assert result.complete_factor == 1.10
        assert result.approved_on == date(2024, 6, 1)

    def test_parse_subscricao(self):
        raw = {
            "lastDatePrior": "2024-07-01",
            "approvedOn": "2024-06-20",
            "label": "Subscrição",
            "eventCategory": "subscription",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        assert result.dividend_type == "SUBSCRICAO"

    def test_parse_formato_yfinance(self):
        raw = {"paymentDate": "2024-04-10", "rate": 0.75, "type": "DIVIDENDO"}
        result = _parse_raw_dividend(raw)
        assert result is not None
        assert result.record_date is None
        assert result.ex_date == date(2024, 4, 10)
        assert result.payment_date == date(2024, 4, 10)

    def test_retorna_none_sem_data(self):
        assert _parse_raw_dividend({"rate": 1.0, "type": "DIVIDENDO"}) is None

    def test_retorna_none_com_valor_zero_para_cash(self):
        raw = {"paymentDate": "2024-01-01", "rate": 0.0, "type": "DIVIDENDO"}
        assert _parse_raw_dividend(raw) is None

    def test_retorna_none_com_data_invalida(self):
        raw = {"paymentDate": "data-invalida", "rate": 1.0, "type": "DIVIDENDO"}
        assert _parse_raw_dividend(raw) is None


@pytest.mark.asyncio
class TestBackfillDividends:
    async def test_skip_types_nao_chamam_api(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        for skip_type in SKIP_TYPES:
            with patch(
                "app.services.dividend_backfill_service._fetch_dividends_brapi",
                new_callable=AsyncMock,
            ) as mock_brapi:
                await backfill_dividends(db, "BTC", skip_type)
                mock_brapi.assert_not_called()

    async def test_cria_somente_asset_dividend_com_record_date(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        await _make_tx(
            db, portfolio.id, "PETR4", OperationType.buy, 100, date(2023, 1, 1)
        )
        raw_dividends = [
            {
                "lastDatePrior": "2024-03-01",
                "paymentDate": "2024-03-15",
                "rate": 1.50,
                "label": "Dividendos",
                "eventCategory": "cash",
            }
        ]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_dividends,
        ):
            await backfill_dividends(db, "PETR4", "ACAO")

        ad_result = await db.execute(
            select(AssetDividend)
            .join(Asset, AssetDividend.asset_id == Asset.id)
            .where(Asset.ticker == "PETR4")
        )
        ads = ad_result.scalars().all()
        assert len(ads) == 1
        assert ads[0].record_date == date(2024, 3, 1)
        assert ads[0].ex_date == date(2024, 3, 4)
        assert ads[0].dividend_type == DividendType.DIVIDENDO
        assert float(ads[0].value_per_unit) == pytest.approx(1.50)

    async def test_jcp_coleta_evento_sem_materializar_carteira(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        await _make_tx(
            db, portfolio.id, "ITUB4", OperationType.buy, 200, date(2023, 1, 1)
        )
        raw_dividends = [
            {
                "lastDatePrior": "2024-04-01",
                "paymentDate": "2024-04-15",
                "rate": 1.00,
                "label": "JCP",
                "eventCategory": "cash",
            }
        ]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_dividends,
        ):
            await backfill_dividends(db, "ITUB4", "ACAO")

        event = (
            await db.execute(
                select(AssetDividend)
                .join(Asset, AssetDividend.asset_id == Asset.id)
                .where(Asset.ticker == "ITUB4")
            )
        ).scalar_one()
        assert event.dividend_type == DividendType.JCP

    async def test_sem_posicao_na_data_com_nao_cria_dividend(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        await _make_tx(
            db, portfolio.id, "ABEV3", OperationType.buy, 100, date(2025, 1, 1)
        )
        raw_dividends = [
            {
                "lastDatePrior": "2024-06-01",
                "paymentDate": "2024-06-15",
                "rate": 0.50,
                "label": "Dividendos",
                "eventCategory": "cash",
            }
        ]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_dividends,
        ):
            await backfill_dividends(db, "ABEV3", "ACAO")

        event = (
            await db.execute(
                select(AssetDividend)
                .join(Asset, AssetDividend.asset_id == Asset.id)
                .where(Asset.ticker == "ABEV3")
            )
        ).scalar_one()
        assert event.ex_date == date(2024, 6, 3)
