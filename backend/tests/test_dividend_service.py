"""Integration tests for canonical on-demand portfolio dividend totals."""

from datetime import date
from decimal import Decimal

import pytest
from app.models.asset import Asset, AssetCurrency, AssetType
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.models.user import User
from app.services.portfolio_service import sum_dividends
from sqlalchemy.ext.asyncio import AsyncSession

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
        record_date=ex_date,
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


async def _make_transaction(
    db: AsyncSession,
    portfolio_id: int,
    asset: Asset,
    transaction_date: date,
    quantity: float = 100.0,
) -> Transaction:
    transaction = Transaction(
        portfolio_id=portfolio_id,
        ticker=asset.ticker,
        asset_type=asset.asset_type,
        operation=OperationType.buy,
        quantity=quantity,
        price=1.0,
        fees=0.0,
        date=transaction_date,
        currency="BRL",
    )
    db.add(transaction)
    await db.flush()
    return transaction


# -- testes -------------------------------------------------------------------


@pytest.mark.asyncio
class TestSumDividends:
    async def test_sem_proventos_retorna_zero(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        total = await sum_dividends(db, portfolio.id)
        assert total == 0.0

    async def test_soma_direitos_canonicos(
        self, db: AsyncSession, portfolio: Portfolio
    ):
        asset = await _make_asset(db, "PETR4")
        await _make_asset_dividend(db, asset, date(2024, 3, 1), value=1.0)

        asset2 = await _make_asset(db, "VALE3")
        await _make_asset_dividend(db, asset2, date(2024, 4, 1), value=0.5)

        await _make_transaction(db, portfolio.id, asset, date(2024, 2, 1))
        await _make_transaction(db, portfolio.id, asset2, date(2024, 2, 1))

        total = await sum_dividends(db, portfolio.id)
        assert total == pytest.approx(150.0)

    async def test_filtro_por_cutoff(self, db: AsyncSession, portfolio: Portfolio):
        """sum_dividends com cutoff so conta proventos com payment_date >= cutoff."""
        asset = await _make_asset(db, "ITUB4")
        await _make_asset_dividend(db, asset, date(2024, 1, 1), value=2.0)
        await _make_asset_dividend(db, asset, date(2024, 6, 1), value=3.0)

        await _make_transaction(db, portfolio.id, asset, date(2023, 12, 1))

        total = await sum_dividends(db, portfolio.id, cutoff=date(2024, 3, 1))
        assert total == pytest.approx(300.0)

    async def test_isolamento_entre_carteiras(self, db: AsyncSession, user: User):
        from app.schemas.portfolio import PortfolioCreate
        from app.services.portfolio_service import create_portfolio

        p1 = await create_portfolio(
            db, user.id, PortfolioCreate(name="P1", description="")
        )
        p2 = await create_portfolio(
            db, user.id, PortfolioCreate(name="P2", description="")
        )

        asset = await _make_asset(db, "BBDC4")
        await _make_asset_dividend(db, asset, date(2024, 1, 1))

        await _make_transaction(
            db,
            p1.id,
            asset,
            date(2023, 12, 1),
            quantity=500,
        )

        assert await sum_dividends(db, p1.id) == pytest.approx(500.0)
        assert await sum_dividends(db, p2.id) == pytest.approx(0.0)

    async def test_asset_dividend_chave_unica(self, db: AsyncSession):
        """Dois registros com mesmo (asset_id, ex_date, dividend_type) devem falhar."""
        import pytest
        from sqlalchemy.exc import IntegrityError

        asset = await _make_asset(db, "BBAS3")
        await _make_asset_dividend(db, asset, date(2024, 5, 1))

        with pytest.raises(IntegrityError):
            await _make_asset_dividend(db, asset, date(2024, 5, 1))  # duplicata
