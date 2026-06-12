"""Testes para portfolio_service — lógica financeira central."""
import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, OperationType
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.portfolio_service import (
    calc_raw_positions,
    enrich_with_prices,
    normalize_type,
    create_portfolio,
    list_portfolios,
    delete_portfolio,
)
from app.schemas.portfolio import PortfolioCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tx(
    portfolio_id: int,
    ticker: str,
    operation: OperationType,
    quantity: float,
    price: float,
    asset_type: str = "ACAO_NACIONAL",
    fees: float = 0.0,
    tx_date: date = date(2024, 1, 10),
) -> Transaction:
    return Transaction(
        portfolio_id=portfolio_id,
        ticker=ticker,
        operation=operation,
        quantity=quantity,
        price=price,
        asset_type=asset_type,
        fees=fees,
        date=tx_date,
        currency="BRL",
    )


# ---------------------------------------------------------------------------
# normalize_type
# ---------------------------------------------------------------------------

class TestNormalizeType:
    def test_acao_para_acao_nacional(self):
        assert normalize_type("ACAO") == "ACAO_NACIONAL"

    def test_etf_int_para_etf_internacional(self):
        assert normalize_type("ETF_INT") == "ETF_INTERNACIONAL"

    def test_tesouro_para_tesouro_direto(self):
        assert normalize_type("TESOURO") == "TESOURO_DIRETO"

    def test_passthrough_desconhecido(self):
        assert normalize_type("CRIPTO") == "CRIPTO"

    def test_case_insensitive(self):
        assert normalize_type("acao") == "ACAO_NACIONAL"

    def test_none_retorna_string(self):
        assert normalize_type(None) == ""


# ---------------------------------------------------------------------------
# calc_raw_positions — Prço Médio Ponderado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCalcRawPositions:

    async def test_compra_simples(self, db: AsyncSession, portfolio: Portfolio):
        db.add(make_tx(portfolio.id, "PETR4", OperationType.buy, 10, 30.0))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert len(positions) == 1
        p = positions[0]
        assert p["ticker"] == "PETR4"
        assert p["quantity"] == 10.0
        assert p["avg_price"] == 30.0
        assert p["total_invested"] == 300.0

    async def test_duas_compras_media_ponderada(self, db: AsyncSession, portfolio: Portfolio):
        """(10 * 30 + 10 * 40) / 20 = 35.0"""
        db.add(make_tx(portfolio.id, "PETR4", OperationType.buy, 10, 30.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "PETR4", OperationType.buy, 10, 40.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert len(positions) == 1
        assert positions[0]["avg_price"] == 35.0
        assert positions[0]["quantity"] == 20.0

    async def test_compra_com_corretagem(self, db: AsyncSession, portfolio: Portfolio):
        """(100 * 10 + 5 taxa) / 100 = 10.05"""
        db.add(make_tx(portfolio.id, "XPBR31", OperationType.buy, 100, 10.0, fees=5.0))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert positions[0]["avg_price"] == pytest.approx(10.05, abs=0.001)
        assert positions[0]["total_invested"] == 1005.0

    async def test_venda_parcial_mantem_preco_medio(self, db: AsyncSession, portfolio: Portfolio):
        """Venda não muda o preço médio ponderado."""
        db.add(make_tx(portfolio.id, "ITUB4", OperationType.buy, 20, 25.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "ITUB4", OperationType.sell, 5, 30.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert len(positions) == 1
        p = positions[0]
        assert p["quantity"] == 15.0
        assert p["avg_price"] == 25.0  # PM não muda na venda
        assert p["total_invested"] == pytest.approx(375.0, abs=0.01)  # 15 * 25

    async def test_venda_total_remove_posicao(self, db: AsyncSession, portfolio: Portfolio):
        db.add(make_tx(portfolio.id, "VALE3", OperationType.buy, 10, 50.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "VALE3", OperationType.sell, 10, 55.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert positions == []

    async def test_multiplos_ativos_independentes(self, db: AsyncSession, portfolio: Portfolio):
        db.add(make_tx(portfolio.id, "PETR4", OperationType.buy, 10, 30.0))
        db.add(make_tx(portfolio.id, "VALE3", OperationType.buy, 5, 80.0))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        tickers = {p["ticker"] for p in positions}
        assert tickers == {"PETR4", "VALE3"}

    async def test_carteira_vazia_retorna_lista_vazia(self, db: AsyncSession, portfolio: Portfolio):
        positions = await calc_raw_positions(db, portfolio.id)
        assert positions == []


# ---------------------------------------------------------------------------
# enrich_with_prices
# ---------------------------------------------------------------------------

class TestEnrichWithPrices:

    def _item(self, ticker="PETR4", qty=10.0, avg=30.0, invested=300.0):
        return {
            "ticker": ticker,
            "asset_type": "ACAO_NACIONAL",
            "asset_label": "Ações",
            "quantity": qty,
            "avg_price": avg,
            "total_invested": invested,
        }

    def test_com_cotacao_disponivel(self):
        items = [self._item(ticker="PETR4", qty=10, avg=30, invested=300)]
        enriched = enrich_with_prices(items, {"PETR4": 35.0})
        e = enriched[0]
        assert e["current_price"] == 35.0
        assert e["current_value"] == 350.0
        assert e["result_abs"] == 50.0
        assert e["result_pct"] == pytest.approx(16.6667, abs=0.01)

    def test_sem_cotacao_current_price_none(self):
        items = [self._item()]
        enriched = enrich_with_prices(items, {})
        e = enriched[0]
        assert e["current_price"] is None
        assert e["result_abs"] == 0.0
        assert e["result_pct"] == 0.0

    def test_nao_usa_avg_como_cotacao(self):
        """Regra crítica: sem cotação, current_price é None, nunca avg_price."""
        items = [self._item(avg=30.0)]
        enriched = enrich_with_prices(items, {})
        assert enriched[0]["current_price"] is None

    def test_prejuizo(self):
        items = [self._item(qty=10, avg=50, invested=500)]
        enriched = enrich_with_prices(items, {"PETR4": 40.0})
        e = enriched[0]
        assert e["result_abs"] == -100.0
        assert e["result_pct"] < 0

    def test_lista_vazia(self):
        assert enrich_with_prices([], {}) == []


# ---------------------------------------------------------------------------
# CRUD de cartîiras
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestPortfolioCRUD:

    async def test_criar_e_listar_carteira(self, db: AsyncSession, user: User):
        data = PortfolioCreate(name="Minha Carteira", description="Descrição")
        p = await create_portfolio(db, user.id, data)
        assert p.id is not None
        assert p.name == "Minha Carteira"

        portfolios = await list_portfolios(db, user.id)
        assert any(port.id == p.id for port in portfolios)

    async def test_deletar_carteira(self, db: AsyncSession, user: User):
        data = PortfolioCreate(name="Delível", description="")
        p = await create_portfolio(db, user.id, data)
        pid = p.id

        await delete_portfolio(db, pid, user.id)
        portfolios = await list_portfolios(db, user.id)
        assert not any(port.id == pid for port in portfolios)

    async def test_isolamento_entre_usuarios(self, db: AsyncSession, user: User):
        """Usuários não vêem carteiras alheias."""
        outro = User(name="Outro", email="outro@sig.com", hashed_password="h", is_active=True)
        db.add(outro)
        await db.flush()

        data = PortfolioCreate(name="Privada", description="")
        await create_portfolio(db, user.id, data)

        portfolios_outro = await list_portfolios(db, outro.id)
        assert portfolios_outro == []
