"""
Testes para proventos com o novo modelo AssetDividend + Dividend.

Fluxo testado:
  - AssetDividend: fonte global por ativo
  - Dividend: por carteira, FK asset_dividend_id
  - sum_dividends: soma total_value dos Dividends da carteira
"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType, AssetCurrency
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.models.user import User
from app.services.portfolio_service import sum_dividends


# -- fixtures de apoio --------------------------------------------------------

async def _make_asset(db: AsyncSession, ticker: str = "PETR4") -> Asset:
    asset = Asset(
        ticker=ticker,
        name=ticker,
        asset_type=AssetType.ACAO,
        currency=AssetCurrency.BRL,
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


async def _make_asset_dividend(
    db: AsyncSession,
    asset: Asset,
    ex_date: date,
    value: float = 1.0,
) -> AssetDividend:
    ad = AssetDividend(
        asset_id=asset.id,
        ex_date=ex_date,
        payment_date=ex_date,
        dividend_type=DividendType.DIVIDENDO,
        value_per_unit=Decimal(str(value)),
        source="brapi",
    )
    db.add(ad)
    await db.flush()
    await db.refresh(ad)
    return ad


async def _make_dividend(
    db: AsyncSession,
    portfolio_id: int,
    asset_dividend: AssetDividend,
    quantity: float = 100.0,
    total_value: float = 100.0,
    status: DividendStatus = DividendStatus.RECEBIDO,
) -> Dividend:
    div = Dividend(
        portfolio_id=portfolio_id,
        asset_dividend_id=asset_dividend.id,
        quantity=quantity,
        total_value=Decimal(str(total_value)),
        net_value=Decimal(str(total_value)),
        status=status,
    )
    db.add(div)
    await db.flush()
    return div


# -- testes -------------------------------------------------------------------

@pytest.mark.asyncio
class TestSumDividends:

    async def test_sem_proventos_retorna_zero(self, db: AsyncSession, portfolio: Portfolio):
        total = await sum_dividends(db, portfolio.id)
        assert total == 0.0

    async def test_soma_total_value(self, db: AsyncSession, portfolio: Portfolio):
        asset = await _make_asset(db, "PETR4")
        ad1 = await _make_asset_dividend(db, asset, date(2024, 3, 1), value=1.0)

        asset2 = await _make_asset(db, "VALE3")
        ad2 = await _make_asset_dividend(db, asset2, date(2024, 4, 1), value=0.5)

        await _make_dividend(db, portfolio.id, ad1, quantity=100, total_value=100.0)
        await _make_dividend(db, portfolio.id, ad2, quantity=100, total_value=50.0)

        total = await sum_dividends(db, portfolio.id)
        assert total == pytest.approx(150.0)

    async def test_filtro_por_cutoff(self, db: AsyncSession, portfolio: Portfolio):
        """sum_dividends com cutoff so conta proventos com payment_date >= cutoff."""
        asset = await _make_asset(db, "ITUB4")
        ad_jan = await _make_asset_dividend(db, asset, date(2024, 1, 1))
        ad_jun = await _make_asset_dividend(db, asset, date(2024, 6, 1))

        await _make_dividend(db, portfolio.id, ad_jan, total_value=200.0)
        await _make_dividend(db, portfolio.id, ad_jun, total_value=300.0)

        total = await sum_dividends(db, portfolio.id, cutoff=date(2024, 3, 1))
        assert total == pytest.approx(300.0)  # apenas junho

    async def test_isolamento_entre_carteiras(self, db: AsyncSession, user: User):
        from app.schemas.portfolio import PortfolioCreate
        from app.services.portfolio_service import create_portfolio

        p1 = await create_portfolio(db, user.id, PortfolioCreate(name="P1", description=""))
        p2 = await create_portfolio(db, user.id, PortfolioCreate(name="P2", description=""))

        asset = await _make_asset(db, "BBDC4")
        ad = await _make_asset_dividend(db, asset, date(2024, 1, 1))

        await _make_dividend(db, p1.id, ad, total_value=500.0)

        assert await sum_dividends(db, p1.id) == pytest.approx(500.0)
        assert await sum_dividends(db, p2.id) == pytest.approx(0.0)

    async def test_asset_dividend_chave_unica(self, db: AsyncSession):
        """Dois registros com mesmo (asset_id, ex_date, dividend_type) devem falhar."""
        from sqlalchemy.exc import IntegrityError
        import pytest

        asset = await _make_asset(db, "BBAS3")
        await _make_asset_dividend(db, asset, date(2024, 5, 1))

        with pytest.raises(IntegrityError):
            await _make_asset_dividend(db, asset, date(2024, 5, 1))  # duplicata
