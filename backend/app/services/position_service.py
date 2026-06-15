from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.transaction import Transaction
from app.services.quotes_service import get_current_price


async def get_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
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
            positions[ticker] = {"ticker": ticker, "asset_type": tx.asset_type, "quantity": 0.0, "invested": 0.0}
        p = positions[ticker]
        if op in ("buy", "compra"):
            p["quantity"] += qty
            p["invested"] += qty * price + fees
        elif op in ("sell", "venda"):
            p["quantity"] -= qty

    out = []
    for ticker, p in positions.items():
        if p["quantity"] <= 0:
            continue
        price_now = await get_current_price(ticker)
        avg = p["invested"] / p["quantity"] if p["quantity"] else 0
        cur_val = p["quantity"] * (price_now or avg)
        out.append({
            "ticker": ticker,
            "asset_type": p["asset_type"],
            "quantity": round(p["quantity"], 8),
            "average_price": round(avg, 4),
            "current_value": round(cur_val, 2),
        })
    return out
