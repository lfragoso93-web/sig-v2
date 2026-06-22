import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.transaction import Transaction
from app.models.asset import Asset
from app.services.quotes_service import get_current_price

logger = logging.getLogger(__name__)


async def get_portfolio_performance(
    db: AsyncSession, portfolio_id: int, user_id: int
) -> dict:
    result = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    transactions = result.scalars().all()

    # Agrupa por ticker mantendo asset_type correto
    positions: dict[str, dict] = {}
    for tx in transactions:
        ticker = tx.ticker
        if ticker not in positions:
            positions[ticker] = {
                "ticker": ticker,
                "asset_type": tx.asset_type,
                "quantity": 0.0,
                "invested": 0.0,
                "current_value": 0.0,
            }
        p = positions[ticker]
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        op = (tx.operation or "").lower()
        if op in ("buy", "compra"):
            p["quantity"] += qty
            p["invested"] += qty * price + float(tx.fees or 0)
        elif op in ("sell", "venda"):
            p["quantity"] -= qty
            p["invested"] -= qty * price

    items = []
    for ticker, p in positions.items():
        if p["quantity"] <= 0:
            continue

        # Passa asset_type e db para buscar cotação correta (BRAPI para BR, yfinance para INTL)
        asset_type_str = p["asset_type"] if isinstance(p["asset_type"], str) else str(p["asset_type"].value)
        current_price = await get_current_price(ticker, asset_type=asset_type_str, db=db)

        if current_price:
            p["current_value"] = p["quantity"] * current_price
        else:
            # Fallback: usa preço médio se cotacao indisponível
            avg_price = p["invested"] / p["quantity"] if p["quantity"] else 0
            p["current_value"] = p["quantity"] * avg_price
            logger.warning(f"[performance] cotacao indisponivel para {ticker}, usando preco medio")

        gain = p["current_value"] - p["invested"]
        gain_pct = (gain / p["invested"] * 100) if p["invested"] else 0.0

        asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
        asset = asset_result.scalar_one_or_none()

        items.append({
            "ticker": ticker,
            "name": asset.name if asset else ticker,
            "asset_type": asset_type_str,
            "quantity": round(p["quantity"], 8),
            "invested": round(p["invested"], 2),
            "current_value": round(p["current_value"], 2),
            "gain": round(gain, 2),
            "gain_pct": round(gain_pct, 4),
        })

    # Totais consolidados
    total_invested = round(sum(i["invested"] for i in items), 2)
    total_current = round(sum(i["current_value"] for i in items), 2)
    total_gain = round(total_current - total_invested, 2)
    total_gain_pct = round(
        (total_gain / total_invested * 100) if total_invested else 0.0, 4
    )

    return {
        "total_invested": total_invested,
        "total_current_value": total_current,
        "total_gain": total_gain,
        "total_gain_pct": total_gain_pct,
        "positions": items,
    }
