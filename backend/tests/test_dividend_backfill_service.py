"""
Testes de integracao para dividend_backfill_service.py (Sprint 5B).

Fluxo testado:
  - _parse_raw_dividend: parseia formatos BRAPI e yfinance, invalida entradas ruins
  - _calc_net_qty: calcula posicao liquida a partir de historico de transacoes
  - SKIP_TYPES: criptos/tesouro/renda-fixa sao ignorados sem chamada API
  - backfill_dividends: cria AssetDividend + Dividend, atualiza se ja existe
  - backfill_dividends: JCP aplica desconto de 15%; status RECEBIDO vs A_RECEBER
  - backfill_all_tickers: itera lista e ignora SKIP_TYPES
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType, AssetCurrency
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.services.dividend_backfill_service import (
    _parse_raw_dividend,
    _calc_net_qty,
    backfill_dividends,
    backfill_all_tickers,
    materialize_asset_dividends,
    SKIP_TYPES,
)


# ─── Fixtures de apoio ───────────────────────────────────────────────────────

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


# ─── Testes de _parse_raw_dividend ────────────────────────────────────────────

class TestParseRawDividend:

    def test_parse_formato_brapi(self):
        raw = {
            "lastDatePrior": "2024-03-01",
            "paymentDate": "2024-03-15",
            "rate": 1.25,
            "type": "DIVIDENDO",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        ex_date, pay_date, value, div_type = result
        assert ex_date == date(2024, 3, 1)
        assert pay_date == date(2024, 3, 15)
        assert value == 1.25
        assert div_type == "DIVIDENDO"

    def test_parse_formato_yfinance(self):
        raw = {
            "paymentDate": "2024-04-10",
            "rate": 0.75,
            "type": "DIVIDENDO",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        ex_date, pay_date, value, div_type = result
        assert ex_date == date(2024, 4, 10)

    def test_retorna_none_sem_data(self):
        raw = {"rate": 1.0, "type": "DIVIDENDO"}
        assert _parse_raw_dividend(raw) is None

    def test_retorna_none_com_valor_zero(self):
        raw = {"paymentDate": "2024-01-01", "rate": 0.0, "type": "DIVIDENDO"}
        assert _parse_raw_dividend(raw) is None

    def test_retorna_none_com_valor_negativo(self):
        raw = {"paymentDate": "2024-01-01", "rate": -5.0, "type": "DIVIDENDO"}
        assert _parse_raw_dividend(raw) is None

    def test_retorna_none_com_data_invalida(self):
        raw = {"paymentDate": "data-invalida", "rate": 1.0, "type": "DIVIDENDO"}
        assert _parse_raw_dividend(raw) is None

    def test_parse_tipo_jcp(self):
        raw = {
            "lastDatePrior": "2024-05-01",
            "paymentDate": "2024-05-15",
            "rate": 2.0,
            "type": "JCP",
        }
        result = _parse_raw_dividend(raw)
        assert result is not None
        assert result[3] == "JCP"


# ─── Testes de _calc_net_qty ────────────────────────────────────────────────────

class TestCalcNetQty:

    def test_zero_sem_transacoes(self):
        assert _calc_net_qty([], date(2024, 1, 1)) == 0.0

    def test_compras_somam(self):
        txs = [
            (date(2024, 1, 1), OperationType.buy, 100),
            (date(2024, 2, 1), OperationType.buy, 50),
        ]
        assert _calc_net_qty(txs, date(2024, 3, 1)) == 150.0

    def test_vendas_subtraem(self):
        txs = [
            (date(2024, 1, 1), OperationType.buy, 100),
            (date(2024, 2, 1), OperationType.sell, 40),
        ]
        assert _calc_net_qty(txs, date(2024, 3, 1)) == 60.0

    def test_nao_conta_transacoes_futuras(self):
        txs = [
            (date(2024, 1, 1), OperationType.buy, 100),
            (date(2024, 6, 1), OperationType.buy, 200),  # futuro em relacao ao ex_date
        ]
        assert _calc_net_qty(txs, date(2024, 3, 1)) == 100.0

    def test_nunca_retorna_negativo(self):
        txs = [
            (date(2024, 1, 1), OperationType.sell, 999),  # venda sem compra previa
        ]
        assert _calc_net_qty(txs, date(2024, 6, 1)) == 0.0

    def test_posicao_zero_apos_venda_total(self):
        txs = [
            (date(2024, 1, 1), OperationType.buy, 100),
            (date(2024, 2, 1), OperationType.sell, 100),
        ]
        assert _calc_net_qty(txs, date(2024, 3, 1)) == 0.0


# ─── Testes de backfill_dividends ───────────────────────────────────────────────

@pytest.mark.asyncio
class TestBackfillDividends:

    async def test_skip_types_nao_chamam_api(self, db: AsyncSession, portfolio: Portfolio):
        """CRIPTO, TESOURO_DIRETO e RENDA_FIXA devem retornar sem chamada API."""
        for skip_type in SKIP_TYPES:
            with patch(
                "app.services.dividend_backfill_service._fetch_dividends_brapi",
                new_callable=AsyncMock,
            ) as mock_brapi:
                await backfill_dividends(db, portfolio.id, "BTC", skip_type)
                mock_brapi.assert_not_called()

    async def test_cria_asset_dividend_e_dividend(self, db: AsyncSession, portfolio: Portfolio):
        """Backfill cria AssetDividend global + Dividend por carteira."""
        await _make_tx(db, portfolio.id, "PETR4", OperationType.buy, 100, date(2023, 1, 1))

        raw_dividends = [
            {
                "lastDatePrior": "2024-03-01",
                "paymentDate": "2024-03-15",
                "rate": 1.50,
                "type": "DIVIDENDO",
            }
        ]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_dividends,
        ):
            await backfill_dividends(db, portfolio.id, "PETR4", "ACAO")

        # Verifica AssetDividend criado
        from sqlalchemy import select
        ad_result = await db.execute(
            select(AssetDividend)
            .join(Asset, AssetDividend.asset_id == Asset.id)
            .where(Asset.ticker == "PETR4")
        )
        ads = ad_result.scalars().all()
        assert len(ads) == 1
        assert float(ads[0].value_per_unit) == pytest.approx(1.50)

        # Verifica Dividend criado
        div_result = await db.execute(
            select(Dividend).where(Dividend.portfolio_id == portfolio.id)
        )
        divs = div_result.scalars().all()
        assert len(divs) == 1
        assert float(divs[0].total_value) == pytest.approx(150.0)  # 100 acoes * 1.50

    async def test_jcp_aplica_desconto_15_porcento(self, db: AsyncSession, portfolio: Portfolio):
        """JCP deve ter net_value = total_value * 0.85."""
        await _make_tx(db, portfolio.id, "ITUB4", OperationType.buy, 200, date(2023, 1, 1))

        raw_dividends = [
            {
                "lastDatePrior": "2024-04-01",
                "paymentDate": "2024-04-15",
                "rate": 1.00,
                "type": "JCP",
            }
        ]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_dividends,
        ):
            await backfill_dividends(db, portfolio.id, "ITUB4", "ACAO")

        from sqlalchemy import select
        div_result = await db.execute(
            select(Dividend).where(Dividend.portfolio_id == portfolio.id)
        )
        div = div_result.scalars().first()
        assert div is not None
        assert float(div.total_value) == pytest.approx(200.0)   # 200 * 1.00
        assert float(div.net_value) == pytest.approx(170.0)      # 200 * 0.85

    async def test_status_recebido_quando_payment_no_passado(self, db: AsyncSession, portfolio: Portfolio):
        """Se payment_date <= hoje, status deve ser RECEBIDO."""
        await _make_tx(db, portfolio.id, "VALE3", OperationType.buy, 100, date(2023, 1, 1))

        raw_dividends = [
            {
                "lastDatePrior": "2023-06-01",
                "paymentDate": "2023-06-15",  # passado
                "rate": 0.90,
                "type": "DIVIDENDO",
            }
        ]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_dividends,
        ):
            await backfill_dividends(db, portfolio.id, "VALE3", "ACAO")

        from sqlalchemy import select
        div_result = await db.execute(
            select(Dividend).where(Dividend.portfolio_id == portfolio.id)
        )
        div = div_result.scalars().first()
        assert div.status == DividendStatus.RECEBIDO

    async def test_sem_posicao_no_ex_date_nao_cria_dividend(self, db: AsyncSession, portfolio: Portfolio):
        """Se o usuario nao tinha o ativo no ex_date, nao deve criar Dividend."""
        # Comprou DEPOIS do ex_date
        await _make_tx(db, portfolio.id, "ABEV3", OperationType.buy, 100, date(2025, 1, 1))

        raw_dividends = [
            {
                "lastDatePrior": "2024-06-01",  # antes da compra
                "paymentDate": "2024-06-15",
                "rate": 0.50,
                "type": "DIVIDENDO",
            }
        ]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_dividends,
        ):
            await backfill_dividends(db, portfolio.id, "ABEV3", "ACAO")

        from sqlalchemy import select
        div_result = await db.execute(
            select(Dividend).where(Dividend.portfolio_id == portfolio.id)
        )
        divs = div_result.scalars().all()
        assert len(divs) == 0

    async def test_atualiza_dividend_existente(self, db: AsyncSession, portfolio: Portfolio):
        """Se AssetDividend ja existe, backfill atualiza qty/total_value do Dividend."""
        await _make_tx(db, portfolio.id, "PETR4", OperationType.buy, 100, date(2023, 1, 1))

        raw_v1 = [{
            "lastDatePrior": "2024-03-01",
            "paymentDate": "2024-03-15",
            "rate": 1.00,
            "type": "DIVIDENDO",
        }]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_v1,
        ):
            await backfill_dividends(db, portfolio.id, "PETR4", "ACAO")

        # Segunda chamada com valor diferente
        raw_v2 = [{
            "lastDatePrior": "2024-03-01",
            "paymentDate": "2024-03-15",
            "rate": 2.00,  # valor corrigido
            "type": "DIVIDENDO",
        }]

        with patch(
            "app.services.dividend_backfill_service._fetch_dividends_brapi",
            new_callable=AsyncMock,
            return_value=raw_v2,
        ):
            await backfill_dividends(db, portfolio.id, "PETR4", "ACAO")

        from sqlalchemy import select
        div_result = await db.execute(
            select(Dividend).where(Dividend.portfolio_id == portfolio.id)
        )
        divs = div_result.scalars().all()
        assert len(divs) == 1  # nao deve duplicar
        assert float(divs[0].total_value) == pytest.approx(200.0)  # 100 * 2.00


# ─── Testes de backfill_all_tickers ───────────────────────────────────────────

@pytest.mark.asyncio
class TestBackfillAllTickers:

    async def test_filtra_skip_types(self, db: AsyncSession, portfolio: Portfolio):
        """CRIPTO e RENDA_FIXA devem ser excluidos da lista processada."""
        tickers = [
            ("PETR4", "ACAO"),
            ("BTC", "CRIPTO"),
            ("TNLP11", "TESOURO_DIRETO"),
        ]

        processed = []

        async def fake_backfill(db, portfolio_id, ticker, asset_type):
            processed.append(ticker)

        with patch(
            "app.services.dividend_backfill_service.backfill_dividends",
            side_effect=fake_backfill,
        ):
            result = await backfill_all_tickers(db, portfolio.id, tickers)

        assert "PETR4" in result
        assert "BTC" not in result
        assert "TNLP11" not in result
        assert len(result) == 1


@pytest.mark.asyncio
async def test_materialize_asset_dividends_cria_provento_da_carteira(db: AsyncSession, portfolio: Portfolio):
    """Eventos globais em AssetDividend devem virar Dividend da carteira."""
    asset = Asset(
        ticker="MXRF11",
        name="MXRF11",
        asset_type=AssetType.FII,
        currency=AssetCurrency.BRL,
    )
    db.add(asset)
    await db.flush()

    await _make_tx(db, portfolio.id, "MXRF11", OperationType.buy, 100, date(2023, 1, 1))

    event = AssetDividend(
        asset_id=asset.id,
        ex_date=date(2024, 3, 1),
        payment_date=date(2024, 3, 15),
        value_per_unit=Decimal("0.10"),
        dividend_type=DividendType.RENDIMENTO,
        source="sync",
    )
    db.add(event)
    await db.flush()

    changed = await materialize_asset_dividends(db, tickers=["MXRF11"])
    assert changed == 1

    from sqlalchemy import select
    div_result = await db.execute(
        select(Dividend).where(Dividend.portfolio_id == portfolio.id)
    )
    div = div_result.scalars().one()
    assert div.ticker == "MXRF11"
    assert float(div.quantity) == pytest.approx(100.0)
    assert float(div.total_value) == pytest.approx(10.0)
