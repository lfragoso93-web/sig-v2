from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import Session
from collections import defaultdict
from fastapi import HTTPException, status

from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.position import Position
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate


# ---------------------------------------------------------------------------
# CRUD assíncrono (usado pelos routers)
# ---------------------------------------------------------------------------

async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.id)
    )
    return result.scalars().all()


async def get_portfolio(db: AsyncSession, portfolio_id: int, user_id: int) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carteira não encontrada",
        )
    return portfolio


async def create_portfolio(
    db: AsyncSession, user_id: int, data: PortfolioCreate
) -> Portfolio:
    portfolio = Portfolio(user_id=user_id, **data.model_dump())
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


async def update_portfolio(
    db: AsyncSession, portfolio_id: int, user_id: int, data: PortfolioUpdate
) -> Portfolio:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(portfolio, field, value)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


async def delete_portfolio(
    db: AsyncSession, portfolio_id: int, user_id: int
) -> None:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    await db.delete(portfolio)
    await db.flush()


# ---------------------------------------------------------------------------
# Recálculo de posições (preço médio ponderado)
# Usado internamente após cada transação
# ---------------------------------------------------------------------------

async def recalc_positions(portfolio_id: int, db: AsyncSession) -> None:
    """
    Recalcula preço médio ponderado e quantidade atual
    para cada ativo da carteira, a partir do histórico de transações.

    Algoritmo:
      - Compra: pm = (pm_ant * qt_ant + qt_nova * preco + fees) / (qt_ant + qt_nova)
      - Venda:  pm não muda, apenas reduz quantidade
    """
    txs_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = txs_result.scalars().all()

    # ticker -> {qty, avg_price, asset_type}
    state: dict[str, dict] = defaultdict(
        lambda: {"qty": 0.0, "avg_price": 0.0, "asset_type": ""}
    )

    for tx in txs:
        s = state[tx.ticker]
        s["asset_type"] = tx.asset_type

        if tx.operation == OperationType.buy:
            total_cost = s["qty"] * s["avg_price"] + tx.quantity * tx.price + tx.fees
            new_qty = s["qty"] + tx.quantity
            s["avg_price"] = total_cost / new_qty if new_qty > 0 else 0
            s["qty"] = new_qty
        else:  # sell
            s["qty"] = max(s["qty"] - tx.quantity, 0)

    active = {k: v for k, v in state.items() if v["qty"] > 1e-9}

    # Posições existentes no banco
    existing_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    existing = {p.ticker: p for p in existing_result.scalars().all()}

    # Remove posições zeradas
    for ticker in list(existing.keys()):
        if ticker not in active:
            await db.delete(existing[ticker])

    # Upsert das posições ativas
    for ticker, data in active.items():
        if ticker in existing:
            pos = existing[ticker]
            pos.quantity = data["qty"]
            pos.avg_price = data["avg_price"]
        else:
            pos = Position(
                portfolio_id=portfolio_id,
                ticker=ticker,
                asset_type=data["asset_type"],
                quantity=data["qty"],
                avg_price=data["avg_price"],
            )
            db.add(pos)

    await db.flush()
