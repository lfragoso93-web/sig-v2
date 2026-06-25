"""
Testes para rentabilidade_service.

Cobre:
  - get_kpis: sem snapshot, com snapshot, retorno por periodo
  - get_rentabilidade_por_ativo: posicao aberta, zerada, sem cotacao
  - get_rentabilidade_por_classe: agrupamento e alocacao_pct

Isolamento:
  - SQLite in-memory (conftest.py)
  - cache_get sempre retorna None (sem Redis)
  - cache_set noop
  - get_prices mockado (batch, igual ao servico real)
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType, AssetCurrency
from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction, OperationType
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers de fixtures
# ---------------------------------------------------------------------------

async def _make_asset(
    db: AsyncSession,
    ticker: str = "PETR4",
    asset_type: AssetType = AssetType.ACAO,
) -> Asset:
    a = Asset(
        ticker=ticker,
        name=f"Ativo {ticker}",
        asset_type=asset_type,
        currency=AssetCurrency.BRL,
    )
    db.add(a)
    await db.flush()
    await db.refresh(a)
    return a


async def _make_buy(
    db: AsyncSession,
    portfolio: Portfolio,
    ticker: str,
    quantity: float,
    price: float,
    asset_type: str = "ACAO",
) -> Transaction:
    """Cria uma transacao de compra — fonte real de posicoes para calc_raw_positions."""
    tx = Transaction(
        portfolio_id=portfolio.id,
        ticker=ticker,
        asset_type=asset_type,
        operation=OperationType.buy,
        quantity=Decimal(str(quantity)),
        price=Decimal(str(price)),
        fees=Decimal("0"),
        date=date.today(),
    )
    db.add(tx)
    await db.flush()
    return tx


async def _make_sell(
    db: AsyncSession,
    portfolio: Portfolio,
    ticker: str,
    quantity: float,
    price: float,
    asset_type: str = "ACAO",
) -> Transaction:
    tx = Transaction(
        portfolio_id=portfolio.id,
        ticker=ticker,
        asset_type=asset_type,
        operation=OperationType.sell,
        quantity=Decimal(str(quantity)),
        price=Decimal(str(price)),
        fees=Decimal("0"),
        date=date.today(),
    )
    db.add(tx)
    await db.flush()
    return tx


async def _make_snapshot(
    db: AsyncSession,
    portfolio: Portfolio,
    snapshot_date: date,
    market_value: float = 10000.0,
    cost_basis: float = 9000.0,
    invested_total: float = 9000.0,
    realized_pnl: float = 0.0,
    unrealized_pnl: float = 1000.0,
    total_pnl: float = 1000.0,
    return_pct: float = 11.11,
) -> PortfolioSnapshot:
    s = PortfolioSnapshot(
        portfolio_id=portfolio.id,
        snapshot_date=snapshot_date,
        market_value=Decimal(str(market_value)),
        cost_basis=Decimal(str(cost_basis)),
        invested_total=Decimal(str(invested_total)),
        realized_pnl=Decimal(str(realized_pnl)),
        unrealized_pnl=Decimal(str(unrealized_pnl)),
        total_pnl=Decimal(str(total_pnl)),
        return_pct=Decimal(str(return_pct)),
    )
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


# Patch padrao: cache sempre miss, set noop
_PATCH_CACHE_GET = patch(
    "app.services.rentabilidade_service.cache_get",
    new_callable=AsyncMock,
    return_value=None,
)
_PATCH_CACHE_SET = patch(
    "app.services.rentabilidade_service.cache_set",
    new_callable=AsyncMock,
)


def _make_prices_mock(prices: dict[str, float]):
    """
    Retorna AsyncMock para get_prices.
    get_prices recebe lista de {ticker, asset_type} e retorna {ticker: preco}.
    Apenas tickers presentes no dict prices serao incluidos no resultado.
    """
    async def _mock(items, db=None):
        return {i["ticker"]: prices[i["ticker"]] for i in items if i["ticker"] in prices}
    return _mock


# ---------------------------------------------------------------------------
# get_kpis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetKpis:

    async def test_sem_snapshot_retorna_zeros(self, db: AsyncSession, portfolio: Portfolio):
        from app.services.rentabilidade_service import get_kpis

        with _PATCH_CACHE_GET, _PATCH_CACHE_SET:
            result = await get_kpis(db, portfolio.id)

        assert result["patrimonio_atual"] == 0.0
        assert result["retorno_total_pct"] == 0.0
        assert result["snapshot_date"] is None

    async def test_snapshot_hoje_retorna_valores(self, db: AsyncSession, portfolio: Portfolio):
        from app.services.rentabilidade_service import get_kpis

        today = date.today()
        await _make_snapshot(
            db, portfolio, today,
            market_value=12000.0,
            invested_total=10000.0,
            total_pnl=2000.0,
            return_pct=20.0,
        )

        with _PATCH_CACHE_GET, _PATCH_CACHE_SET:
            result = await get_kpis(db, portfolio.id)

        assert result["patrimonio_atual"] == pytest.approx(12000.0)
        assert result["total_aportado"] == pytest.approx(10000.0)
        assert result["total_pnl"] == pytest.approx(2000.0)
        assert result["retorno_total_pct"] == pytest.approx(20.0)
        assert result["snapshot_date"] == str(today)

    async def test_retorno_mes_usa_snapshot_30d(self, db: AsyncSession, portfolio: Portfolio):
        from app.services.rentabilidade_service import get_kpis

        today = date.today()
        snap_30d = today - timedelta(days=30)

        await _make_snapshot(db, portfolio, snap_30d, market_value=9000.0)
        await _make_snapshot(db, portfolio, today,    market_value=10000.0)

        with _PATCH_CACHE_GET, _PATCH_CACHE_SET:
            result = await get_kpis(db, portfolio.id)

        # (10000 - 9000) / 9000 * 100 = 11.1111%
        assert result["retorno_mes_pct"] == pytest.approx(11.1111, rel=1e-3)

    async def test_retorno_mes_sem_snap_30d_usa_fallback(self, db: AsyncSession, portfolio: Portfolio):
        """Se nao houver snapshot 30d atras, retorno_mes cai no fallback total_pnl/invested."""
        from app.services.rentabilidade_service import get_kpis

        today = date.today()
        await _make_snapshot(
            db, portfolio, today,
            market_value=11000.0,
            invested_total=10000.0,
            total_pnl=1000.0,
            return_pct=10.0,
        )

        with _PATCH_CACHE_GET, _PATCH_CACHE_SET:
            result = await get_kpis(db, portfolio.id)

        # Sem snap_30d, _ret_between usa total_pnl/invested = 10%
        assert result["retorno_mes_pct"] == pytest.approx(10.0)

    async def test_campos_obrigatorios_presentes(self, db: AsyncSession, portfolio: Portfolio):
        from app.services.rentabilidade_service import get_kpis

        today = date.today()
        await _make_snapshot(db, portfolio, today)

        with _PATCH_CACHE_GET, _PATCH_CACHE_SET:
            result = await get_kpis(db, portfolio.id)

        campos = [
            "patrimonio_atual", "custo_total", "total_aportado",
            "ganho_nao_realizado", "ganho_realizado", "total_pnl",
            "retorno_total_pct", "retorno_mes_pct", "retorno_12m_pct",
            "retorno_desde_inicio_pct", "proventos_total", "proventos_12m",
            "snapshot_date",
        ]
        for campo in campos:
            assert campo in result, f"Campo ausente: {campo}"


# ---------------------------------------------------------------------------
# get_rentabilidade_por_ativo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetRentabilidadePorAtivo:

    async def test_sem_posicoes_retorna_lista_vazia(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_ativo

        with _PATCH_CACHE_GET, _PATCH_CACHE_SET:
            result = await get_rentabilidade_por_ativo(db, portfolio.id)

        assert result == []

    async def test_posicao_aberta_com_cotacao(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_ativo

        await _make_asset(db, "PETR4")
        await _make_buy(db, portfolio, "PETR4", quantity=100.0, price=20.0)

        prices_mock = _make_prices_mock({"PETR4": 25.0})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_ativo(db, portfolio.id)

        assert len(result) == 1
        r = result[0]
        assert r["ticker"] == "PETR4"
        assert r["is_open"] is True
        assert r["quantity"] == pytest.approx(100.0)
        assert r["current_value"] == pytest.approx(2500.0)   # 100 * 25
        assert r["unrealized_pnl"] == pytest.approx(500.0)   # 2500 - 2000
        assert r["realized_pnl"] == pytest.approx(0.0)
        assert r["total_pnl"] == pytest.approx(500.0)
        assert r["unrealized_pct"] == pytest.approx(25.0)    # 500/2000*100

    async def test_posicao_aberta_sem_cotacao_usa_preco_medio(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_ativo

        await _make_asset(db, "VALE3")
        await _make_buy(db, portfolio, "VALE3", quantity=50.0, price=30.0)

        # get_prices retorna dict vazio -> sem cotacao
        prices_mock = _make_prices_mock({})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_ativo(db, portfolio.id)

        assert len(result) == 1
        r = result[0]
        # Sem cotacao, current_value = qty * avg_price = 50 * 30 = 1500
        assert r["current_value"] == pytest.approx(1500.0)
        assert r["unrealized_pnl"] == pytest.approx(0.0)

    async def test_posicao_zerada_aparece_com_realized(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_ativo

        await _make_asset(db, "MGLU3")
        # Compra e venda total com lucro: realized = 100 * (5 - 2) = 300
        await _make_buy(db, portfolio, "MGLU3", quantity=100.0, price=2.0)
        await _make_sell(db, portfolio, "MGLU3", quantity=100.0, price=5.0)

        prices_mock = _make_prices_mock({})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_ativo(db, portfolio.id)

        assert len(result) == 1
        r = result[0]
        assert r["is_open"] is False
        assert r["quantity"] == pytest.approx(0.0)
        assert r["current_value"] == pytest.approx(0.0)
        assert r["realized_pnl"] == pytest.approx(300.0)
        assert r["total_pnl"] == pytest.approx(300.0)

    async def test_posicao_zerada_sem_realized_ignorada(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_ativo

        await _make_asset(db, "BOVA11")
        # Compra e venda no mesmo preco: realized = 0
        await _make_buy(db, portfolio, "BOVA11", quantity=10.0, price=10.0)
        await _make_sell(db, portfolio, "BOVA11", quantity=10.0, price=10.0)

        prices_mock = _make_prices_mock({})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_ativo(db, portfolio.id)

        # qty=0 e realized=0 -> deve ser ignorado
        assert result == []

    async def test_multiplos_ativos_ordenados_por_valor(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_ativo

        await _make_asset(db, "PETR4", AssetType.ACAO)
        await _make_asset(db, "HGLG11", AssetType.FII)

        await _make_buy(db, portfolio, "PETR4",  quantity=100.0, price=20.0, asset_type="ACAO")
        await _make_buy(db, portfolio, "HGLG11", quantity=10.0,  price=50.0, asset_type="FII")

        prices_mock = _make_prices_mock({"PETR4": 30.0, "HGLG11": 120.0})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_ativo(db, portfolio.id)

        assert len(result) == 2
        # PETR4: 100*30=3000, HGLG11: 10*120=1200 -> PETR4 primeiro
        assert result[0]["ticker"] == "PETR4"
        assert result[1]["ticker"] == "HGLG11"


# ---------------------------------------------------------------------------
# get_rentabilidade_por_classe
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetRentabilidadePorClasse:

    async def test_sem_posicoes_retorna_lista_vazia(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_classe

        with _PATCH_CACHE_GET, _PATCH_CACHE_SET:
            result = await get_rentabilidade_por_classe(db, portfolio.id)

        assert result == []

    async def test_agrupa_por_tipo(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_classe

        await _make_asset(db, "PETR4",  AssetType.ACAO)
        await _make_asset(db, "VALE3",  AssetType.ACAO)
        await _make_asset(db, "HGLG11", AssetType.FII)

        await _make_buy(db, portfolio, "PETR4",  quantity=100.0, price=20.0, asset_type="ACAO")
        await _make_buy(db, portfolio, "VALE3",  quantity=50.0,  price=20.0, asset_type="ACAO")
        await _make_buy(db, portfolio, "HGLG11", quantity=10.0,  price=50.0, asset_type="FII")

        prices_mock = _make_prices_mock({"PETR4": 25.0, "VALE3": 22.0, "HGLG11": 60.0})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_classe(db, portfolio.id)

        tipos = {r["asset_type"]: r for r in result}
        assert "ACAO" in tipos
        assert "FII" in tipos

        # ACAO: (100*25) + (50*22) = 2500+1100 = 3600
        assert tipos["ACAO"]["current_value"] == pytest.approx(3600.0)
        assert tipos["ACAO"]["count"] == 2

        # FII: 10*60 = 600
        assert tipos["FII"]["current_value"] == pytest.approx(600.0)
        assert tipos["FII"]["count"] == 1

    async def test_alocacao_pct_soma_100(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_classe

        await _make_asset(db, "PETR4",  AssetType.ACAO)
        await _make_asset(db, "HGLG11", AssetType.FII)

        await _make_buy(db, portfolio, "PETR4",  quantity=100.0, price=20.0, asset_type="ACAO")
        await _make_buy(db, portfolio, "HGLG11", quantity=10.0,  price=60.0, asset_type="FII")

        prices_mock = _make_prices_mock({"PETR4": 20.0, "HGLG11": 60.0})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_classe(db, portfolio.id)

        total_alocacao = sum(r["alocacao_pct"] for r in result)
        assert total_alocacao == pytest.approx(100.0, rel=1e-3)

    async def test_campos_obrigatorios_presentes(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        from app.services.rentabilidade_service import get_rentabilidade_por_classe

        await _make_asset(db, "PETR4", AssetType.ACAO)
        await _make_buy(db, portfolio, "PETR4", quantity=10.0, price=20.0, asset_type="ACAO")

        prices_mock = _make_prices_mock({"PETR4": 25.0})
        with _PATCH_CACHE_GET, _PATCH_CACHE_SET, \
             patch("app.services.rentabilidade_service.get_prices", prices_mock):
            result = await get_rentabilidade_por_classe(db, portfolio.id)

        assert len(result) == 1
        campos = [
            "asset_type", "total_invested", "current_value",
            "unrealized_pnl", "realized_pnl", "total_pnl",
            "total_pnl_pct", "alocacao_pct", "count",
        ]
        for campo in campos:
            assert campo in result[0], f"Campo ausente: {campo}"
