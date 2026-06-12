"""Testes para sum_dividends em portfolio_service."""
import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.portfolio import Portfolio
from app.models.user import User
from app.models.dividend import Dividend
from app.services.portfolio_service import sum_dividends


@pytest.mark.asyncio
class TestSumDividends:

    async def test_sem_proventos_retorna_zero(self, db: AsyncSession, portfolio: Portfolio):
        total = await sum_dividends(db, portfolio.id)
        assert total == 0.0

    async def test_soma_total_value(self, db: AsyncSession, portfolio: Portfolio):
        db.add(Dividend(
            portfolio_id=portfolio.id,
            ticker="PETR4",
            total_value=100.0,
            payment_date=date(2024, 3, 1),
        ))
        db.add(Dividend(
            portfolio_id=portfolio.id,
            ticker="VALE3",
            total_value=50.0,
            payment_date=date(2024, 4, 1),
        ))
        await db.flush()

        total = await sum_dividends(db, portfolio.id)
        assert total == pytest.approx(150.0)

    async def test_filtro_por_cutoff(self, db: AsyncSession, portfolio: Portfolio):
        db.add(Dividend(
            portfolio_id=portfolio.id,
            ticker="ITUB4",
            total_value=200.0,
            payment_date=date(2024, 1, 1),
        ))
        db.add(Dividend(
            portfolio_id=portfolio.id,
            ticker="ITUB4",
            total_value=300.0,
            payment_date=date(2024, 6, 1),
        ))
        await db.flush()

        total = await sum_dividends(db, portfolio.id, cutoff=date(2024, 3, 1))
        assert total == pytest.approx(300.0)  # só o de junho

    async def test_isolamento_entre_carteiras(self, db: AsyncSession, user: User):
        from app.schemas.portfolio import PortfolioCreate
        from app.services.portfolio_service import create_portfolio

        p1 = await create_portfolio(db, user.id, PortfolioCreate(name="P1", description=""))
        p2 = await create_portfolio(db, user.id, PortfolioCreate(name="P2", description=""))

        db.add(Dividend(portfolio_id=p1.id, ticker="PETR4", total_value=500.0, payment_date=date(2024, 1, 1)))
        await db.flush()

        assert await sum_dividends(db, p1.id) == pytest.approx(500.0)
        assert await sum_dividends(db, p2.id) == pytest.approx(0.0)
