import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.quotes_service import get_current_price

logger = logging.getLogger(__name__)


async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at)
    )
    return list(result.scalars().all())


async def create_portfolio(db: AsyncSession, user_id: int, data: PortfolioCreate) -> Portfolio:
    portfolio = Portfolio(user_id=user_id, name=data.name, description=getattr(data, "description", None))
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


async def get_portfolio(db: AsyncSession, portfolio_id: int, user_id: int) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira não encontrada")
    return portfolio


async def update_portfolio(db: AsyncSession, portfolio_id: int, user_id: int, data: PortfolioUpdate) -> Portfolio:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(portfolio, field, value)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


async def delete_portfolio(db: AsyncSession, portfolio_id: int, user_id: int) -> None:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    await db.delete(portfolio)
    await db.commit()


async def get_portfolio_summary(db: AsyncSession, portfolio_id: int, user_id: int) -> dict:
    await get_portfolio(db, portfolio_id, user_id)

    result = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    transactions = result.scalars().all()

    total_invested = 0.0
    positions: dict[str, dict] = {}
    for tx in transactions:
        ticker = tx.ticker
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        op = (tx.operation or "").lower()
        if ticker not in positions:
            positions[ticker] = {"quantity": 0.0, "avg_price": 0.0, "invested": 0.0}
        p = positions[ticker]
        if op in ("buy", "compra"):
            p["quantity"] += qty
            p["invested"] += qty * price + fees
            total_invested += qty * price + fees
        elif op in ("sell", "venda"):
            p["quantity"] -= qty
            p["invested"] -= qty * price
            total_invested -= qty * price

    current_value = 0.0
    for ticker, p in positions.items():
        if p["quantity"] <= 0:
            continue
        price_now = await get_current_price(ticker)
        current_value += p["quantity"] * (price_now or p["invested"] / max(p["quantity"], 1))

    total_gain = current_value - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0.0

    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_gain": round(total_gain, 2),
        "total_gain_pct": round(total_gain_pct, 4),
    }


async def get_portfolio_positions(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    await get_portfolio(db, portfolio_id, user_id)
    result = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    transactions = result.scalars().all()

    positions: dict[str, dict] = {}
    for tx in transactions:
        ticker = tx.ticker
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        op = (tx.operation or "").lower()
        if ticker not in positions:
            positions[ticker] = {
                "ticker": ticker,
                "asset_type": tx.asset_type,
                "quantity": 0.0,
                "invested": 0.0,
            }
        p = positions[ticker]
        if op in ("buy", "compra"):
            p["quantity"] += qty
            p["invested"] += qty * price + fees
        elif op in ("sell", "venda"):
            p["quantity"] -= qty

    total_current = 0.0
    enriched = []
    for ticker, p in positions.items():
        if p["quantity"] <= 0:
            continue
        price_now = await get_current_price(ticker)
        avg = p["invested"] / p["quantity"] if p["quantity"] else 0
        cur_val = p["quantity"] * (price_now or avg)
        total_current += cur_val
        enriched.append({"ticker": ticker, "data": p, "current_value": cur_val, "current_price": price_now or avg})

    result_list = []
    for e in enriched:
        p = e["data"]
        cur_val = e["current_value"]
        avg = p["invested"] / p["quantity"] if p["quantity"] else 0
        var_val = cur_val - p["invested"]
        var_pct = (var_val / p["invested"] * 100) if p["invested"] else 0
        alloc = (cur_val / total_current * 100) if total_current else 0
        result_list.append({
            "ticker": p["ticker"],
            "asset_type": p["asset_type"],
            "quantity": round(p["quantity"], 8),
            "average_price": round(avg, 4),
            "current_price": round(e["current_price"], 4),
            "current_value": round(cur_val, 2),
            "invested_value": round(p["invested"], 2),
            "variation_value": round(var_val, 2),
            "variation_percent": round(var_pct, 4),
            "allocation_pct": round(alloc, 4),
        })
    return result_list


async def get_asset_distribution(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    positions = await get_portfolio_positions(db, portfolio_id, user_id)
    by_type: dict[str, float] = {}
    for p in positions:
        at = p.get("asset_type") or "OUTRO"
        by_type[at] = by_type.get(at, 0) + p["current_value"]
    total = sum(by_type.values())
    return [
        {
            "asset_type": at,
            "label": at.replace("_", " ").title(),
            "value": round(v, 2),
            "percentage": round(v / total * 100, 4) if total else 0,
        }
        for at, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)
    ]


async def get_patrimonio_history(db: AsyncSession, portfolio_id: int, user_id: int, months: int = 12) -> list[dict]:
    """Retorna histórico mensal simplificado com base nas transações."""
    await get_portfolio(db, portfolio_id, user_id)
    result = await db.execute(
        select(
            func.date_trunc("month", Transaction.date).label("month"),
            func.sum(Transaction.quantity * Transaction.price).label("invested"),
        )
        .where(Transaction.portfolio_id == portfolio_id)
        .group_by(func.date_trunc("month", Transaction.date))
        .order_by(func.date_trunc("month", Transaction.date))
        .limit(months)
    )
    rows = result.fetchall()
    return [
        {
            "date": str(row.month)[:7],
            "value": round(float(row.invested or 0), 2),
            "invested": round(float(row.invested or 0), 2),
        }
        for row in rows
    ]
