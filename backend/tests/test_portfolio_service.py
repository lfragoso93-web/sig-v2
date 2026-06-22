"""Testes para portfolio_service - logica financeira central.

Criterios de aceite Sprint 4:
  - PM ponderado calculado apenas nas compras
  - Vendas reduzem custo proporcional sem alterar PM
  - fees de venda nao entram no PM
  - Posicoes zeradas desaparecem
  - current_price/current_value/result_abs/result_pct = None quando sem cotacao
  - Resumo bate com as posicoes
  - Carteiras de usuarios diferentes ficam isoladas
"""
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
    def test_acao_canonico_passthrough(self):
        """"ACAO" ja e o valor canonico do enum — deve retornar igual."""
        assert normalize_type("ACAO") == "ACAO"

    def test_acao_nacional_para_acao(self):
        """"ACAO_NACIONAL" e alias legado — deve ser normalizado para "ACAO"."""
        assert normalize_type("ACAO_NACIONAL") == "ACAO"

    def test_etf_int_para_etf_internacional(self):
        assert normalize_type("ETF_INT") == "ETF_INTERNACIONAL"

    def test_tesouro_para_tesouro_direto(self):
        assert normalize_type("TESOURO") == "TESOURO_DIRETO"

    def test_tesouro_direto_passthrough(self):
        assert normalize_type("TESOURO_DIRETO") == "TESOURO_DIRETO"

    def test_stock_normalizado(self):
        assert normalize_type("STOCKS") == "STOCK"
        assert normalize_type("STOCK") == "STOCK"

    def test_cripto_normalizado(self):
        assert normalize_type("CRIPTOMOEDA") == "CRIPTO"
        assert normalize_type("CRIPTO") == "CRIPTO"

    def test_fii_passthrough(self):
        assert normalize_type("FII") == "FII"

    def test_passthrough_desconhecido(self):
        assert normalize_type("OUTRO") == "OUTRO"

    def test_case_insensitive(self):
        """Entrada em lowercase deve normalizar para o canonico "ACAO"."""
        assert normalize_type("acao") == "ACAO"

    def test_case_insensitive_alias_legado(self):
        """Alias legado em lowercase tambem deve ser normalizado."""
        assert normalize_type("acao_nacional") == "ACAO"

    def test_none_retorna_string_vazia(self):
        assert normalize_type(None) == ""


# ---------------------------------------------------------------------------
# calc_raw_positions - Preco Medio Ponderado
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
        """(10*30 + 10*40) / 20 = 35.0"""
        db.add(make_tx(portfolio.id, "PETR4", OperationType.buy, 10, 30.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "PETR4", OperationType.buy, 10, 40.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert len(positions) == 1
        assert positions[0]["avg_price"] == 35.0
        assert positions[0]["quantity"] == 20.0
        assert positions[0]["total_invested"] == 700.0

    async def test_compra_com_taxa_eleva_pm(self, db: AsyncSession, portfolio: Portfolio):
        """PM = (100*10 + 5) / 100 = 10.05"""
        db.add(make_tx(portfolio.id, "XPBR31", OperationType.buy, 100, 10.0, fees=5.0))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert positions[0]["avg_price"] == pytest.approx(10.05, abs=0.001)
        assert positions[0]["total_invested"] == 1005.0

    async def test_venda_parcial_nao_altera_pm(self, db: AsyncSession, portfolio: Portfolio):
        """Venda nao muda o PM - mesmo que vendida mais caro."""
        db.add(make_tx(portfolio.id, "ITUB4", OperationType.buy, 20, 25.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "ITUB4", OperationType.sell, 5, 30.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert len(positions) == 1
        p = positions[0]
        assert p["quantity"] == 15.0
        assert p["avg_price"] == pytest.approx(25.0, abs=0.001)  # PM invariante
        assert p["total_invested"] == pytest.approx(375.0, abs=0.01)  # 15 * 25

    async def test_venda_mais_barata_nao_altera_pm(self, db: AsyncSession, portfolio: Portfolio):
        """Mesmo vendendo com prejuizo, o PM das cotas restantes nao muda."""
        db.add(make_tx(portfolio.id, "VALE3", OperationType.buy, 10, 80.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "VALE3", OperationType.sell, 3, 60.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        p = positions[0]
        assert p["quantity"] == 7.0
        assert p["avg_price"] == pytest.approx(80.0, abs=0.001)  # PM invariante
        assert p["total_invested"] == pytest.approx(560.0, abs=0.01)  # 7 * 80

    async def test_taxa_de_venda_nao_entra_no_pm(self, db: AsyncSession, portfolio: Portfolio):
        """fees da venda NAO afetam o PM nem o custo da posicao restante."""
        db.add(make_tx(portfolio.id, "BBAS3", OperationType.buy, 10, 50.0, tx_date=date(2024, 1, 1)))
        # Venda com taxa de R$2 - nao deve alterar PM das 7 cotas restantes
        db.add(make_tx(portfolio.id, "BBAS3", OperationType.sell, 3, 55.0, fees=2.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        p = positions[0]
        assert p["quantity"] == 7.0
        assert p["avg_price"] == pytest.approx(50.0, abs=0.001)  # PM invariante
        assert p["total_invested"] == pytest.approx(350.0, abs=0.01)  # 7 * 50

    async def test_venda_total_remove_posicao(self, db: AsyncSession, portfolio: Portfolio):
        """Posicao zerada desaparece completamente."""
        db.add(make_tx(portfolio.id, "VALE3", OperationType.buy, 10, 50.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "VALE3", OperationType.sell, 10, 55.0, tx_date=date(2024, 1, 2)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert positions == []

    async def test_compra_venda_parcial_segunda_compra(self, db: AsyncSession, portfolio: Portfolio):
        """Cenario: compra 10@30 -> vende 5 -> compra 10@40 -> PM = (5*30 + 10*40) / 15 = 36.67"""
        db.add(make_tx(portfolio.id, "MGLU3", OperationType.buy, 10, 30.0, tx_date=date(2024, 1, 1)))
        db.add(make_tx(portfolio.id, "MGLU3", OperationType.sell, 5, 35.0, tx_date=date(2024, 1, 2)))
        db.add(make_tx(portfolio.id, "MGLU3", OperationType.buy, 10, 40.0, tx_date=date(2024, 1, 3)))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        p = positions[0]
        assert p["quantity"] == 15.0
        # (5*30 + 10*40) / 15 = (150 + 400) / 15 = 36.6666...
        assert p["avg_price"] == pytest.approx(36.6667, abs=0.001)
        assert p["total_invested"] == pytest.approx(550.0, abs=0.01)

    async def test_tesouro_direto_calcula_como_cotas(self, db: AsyncSession, portfolio: Portfolio):
        """Tesouro Direto: posicao controlada por quantidade de cotas."""
        db.add(make_tx(
            portfolio.id, "TESOURO SELIC 2029", OperationType.buy,
            0.5, 14000.0, asset_type="TESOURO_DIRETO",
            tx_date=date(2024, 1, 1),
        ))
        db.add(make_tx(
            portfolio.id, "TESOURO SELIC 2029", OperationType.sell,
            0.25, 15000.0, asset_type="TESOURO_DIRETO",
            tx_date=date(2024, 1, 2),
        ))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        assert len(positions) == 1
        p = positions[0]
        assert p["quantity"] == pytest.approx(0.25, abs=1e-9)
        assert p["avg_price"] == pytest.approx(14000.0, abs=0.01)  # PM invariante na venda
        assert p["asset_type"] == "TESOURO_DIRETO"

    async def test_multiplos_ativos_independentes(self, db: AsyncSession, portfolio: Portfolio):
        db.add(make_tx(portfolio.id, "PETR4", OperationType.buy, 10, 30.0))
        db.add(make_tx(portfolio.id, "VALE3", OperationType.buy, 5, 80.0))
        await db.flush()

        positions = await calc_raw_positions(db, portfolio.id)
        tickers = {p["ticker"] for p in positions}
        assert tickers == {"PETR4", "VALE3"}

    async def test_isolamento_entre_carteiras(self, db: AsyncSession, user: User):
        """Transacoes de uma carteira nao afetam posicoes de outra."""
        cart1 = await create_portfolio(db, user.id, PortfolioCreate(name="C1", description=""))
        cart2 = await create_portfolio(db, user.id, PortfolioCreate(name="C2", description=""))

        db.add(make_tx(cart1.id, "PETR4", OperationType.buy, 10, 30.0))
        db.add(make_tx(cart2.id, "PETR4", OperationType.buy, 5, 50.0))
        await db.flush()

        pos1 = await calc_raw_positions(db, cart1.id)
        pos2 = await calc_raw_positions(db, cart2.id)

        assert pos1[0]["quantity"] == 10.0
        assert pos1[0]["avg_price"] == 30.0
        assert pos2[0]["quantity"] == 5.0
        assert pos2[0]["avg_price"] == 50.0

    async def test_carteira_vazia_retorna_lista_vazia(self, db: AsyncSession, portfolio: Portfolio):
        positions = await calc_raw_positions(db, portfolio.id)
        assert positions == []


# ---------------------------------------------------------------------------
# enrich_with_prices
# ---------------------------------------------------------------------------

class TestEnrichWithPrices:

    def _item(
        self, ticker="PETR4", qty=10.0, avg=30.0, invested=300.0,
        asset_type="ACAO_NACIONAL"
    ):
        """Helper usa asset_type="ACAO_NACIONAL" (alias legado) intencionalmente
        para garantir que enrich_with_prices normalize antes de checar _MARKET_PRICE_TYPES.
        """
        return {
            "ticker": ticker,
            "asset_type": asset_type,
            "asset_label": "Acoes",
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

    def test_sem_cotacao_todos_campos_none(self):
        """Criterio de aceite: sem cotacao, current_price/value/result = None."""
        items = [self._item()]
        enriched = enrich_with_prices(items, {})
        e = enriched[0]
        assert e["current_price"] is None
        assert e["current_value"] is None
        assert e["result_abs"] is None
        assert e["result_pct"] is None

    def test_nao_usa_avg_como_cotacao(self):
        """Regra critica: sem cotacao, current_price e None. Nunca avg_price."""
        items = [self._item(avg=30.0)]
        enriched = enrich_with_prices(items, {})
        assert enriched[0]["current_price"] is None
        assert enriched[0]["current_value"] is None

    def test_prejuizo(self):
        items = [self._item(qty=10, avg=50, invested=500)]
        enriched = enrich_with_prices(items, {"PETR4": 40.0})
        e = enriched[0]
        assert e["result_abs"] == -100.0
        assert e["result_pct"] < 0

    def test_cotacao_zerada_nao_divide_por_zero(self):
        items = [self._item(qty=10, avg=30, invested=0.0)]
        enriched = enrich_with_prices(items, {"PETR4": 35.0})
        assert enriched[0]["result_pct"] == 0.0

    def test_lista_vazia(self):
        assert enrich_with_prices([], {}) == []

    def test_mix_com_e_sem_cotacao(self):
        """Ativos com cotacao retornam valores; sem cotacao retornam None."""
        items = [
            self._item(ticker="PETR4", qty=10, avg=30, invested=300),
            self._item(ticker="VALE3", qty=5,  avg=80, invested=400),
        ]
        enriched = enrich_with_prices(items, {"PETR4": 35.0})  # VALE3 sem cotacao
        petr = next(e for e in enriched if e["ticker"] == "PETR4")
        vale = next(e for e in enriched if e["ticker"] == "VALE3")

        assert petr["current_price"] == 35.0
        assert petr["current_value"] == 350.0
        assert vale["current_price"] is None
        assert vale["current_value"] is None
        assert vale["result_abs"] is None


# ---------------------------------------------------------------------------
# CRUD de carteiras
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestPortfolioCRUD:

    async def test_criar_e_listar_carteira(self, db: AsyncSession, user: User):
        data = PortfolioCreate(name="Minha Carteira", description="Descricao")
        p = await create_portfolio(db, user.id, data)
        assert p.id is not None
        assert p.name == "Minha Carteira"

        portfolios = await list_portfolios(db, user.id)
        assert any(port.id == p.id for port in portfolios)

    async def test_deletar_carteira(self, db: AsyncSession, user: User):
        data = PortfolioCreate(name="Deletavel", description="")
        p = await create_portfolio(db, user.id, data)
        pid = p.id

        await delete_portfolio(db, pid, user.id)
        portfolios = await list_portfolios(db, user.id)
        assert not any(port.id == pid for port in portfolios)

    async def test_isolamento_entre_usuarios(self, db: AsyncSession, user: User):
        """Usuarios nao veem carteiras alheias."""
        outro = User(name="Outro", email="outro@sig.com", hashed_password="h", is_active=True)
        db.add(outro)
        await db.flush()

        data = PortfolioCreate(name="Privada", description="")
        await create_portfolio(db, user.id, data)

        portfolios_outro = await list_portfolios(db, outro.id)
        assert portfolios_outro == []
