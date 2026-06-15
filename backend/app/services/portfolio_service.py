import logging
from datetime import date as DateType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.dividend import Dividend
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.quotes_service import get_current_price

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapa de normalizacao de tipos de ativo
# ---------------------------------------------------------------------------
_TYPE_MAP: dict[str, str] = {
    "ACAO": "ACAO_NACIONAL",
    "ACOES": "ACAO_NACIONAL",
    "ETF_INT": "ETF_INTERNACIONAL",
    "ETF_INTERNACIONAL": "ETF_INTERNACIONAL",
    "TESOURO": "TESOURO_DIRETO",
    "TESOURO_DIRETO": "TESOURO_DIRETO",
    "STOCK": "STOCK",
    "STOCKS": "STOCK",
    "CRIPTO": "CRIPTO",
    "CRIPTOMOEDA": "CRIPTO",
    "FII": "FII",
    "BDR": "BDR",
    "RENDA_FIXA": "RENDA_FIXA",
    "ETF_NACIONAL": "ETF_NACIONAL",
}


def normalize_type(asset_type: str | None) -> str:
    """Normaliza string de tipo de ativo para o padrao interno."""
    if not asset_type:
        return ""
    return _TYPE_MAP.get(asset_type.upper(), asset_type.upper())


# ---------------------------------------------------------------------------
# calc_raw_positions - PM ponderado, venda nao altera PM
# ---------------------------------------------------------------------------

async def calc_raw_positions(
    db: AsyncSession,
    portfolio_id: int,
) -> list[dict]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date)
    )
    transactions = result.scalars().all()

    state: dict[str, dict] = {}

    for tx in transactions:
        ticker = str(tx.ticker)
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        op = tx.operation
        asset_type = normalize_type(str(tx.asset_type or ""))

        if ticker not in state:
            state[ticker] = {"quantity": 0.0, "total_cost": 0.0, "asset_type": asset_type}

        s = state[ticker]

        if op == OperationType.buy or (hasattr(op, 'value') and op.value == 'buy') or str(op).lower() in ('buy', 'compra'):
            s["total_cost"] += qty * price + fees
            s["quantity"] += qty
        elif op == OperationType.sell or (hasattr(op, 'value') and op.value == 'sell') or str(op).lower() in ('sell', 'venda'):
            if s["quantity"] > 0:
                ratio = min(qty, s["quantity"]) / s["quantity"]
                s["total_cost"] -= s["total_cost"] * ratio
                s["quantity"] = max(0.0, s["quantity"] - qty)

    positions = []
    for ticker, s in state.items():
        qty = s["quantity"]
        if qty <= 1e-9:
            continue
        avg = s["total_cost"] / qty if qty else 0.0
        positions.append({
            "ticker": ticker,
            "asset_type": s["asset_type"],
            "asset_label": s["asset_type"].replace("_", " ").title(),
            "quantity": qty,
            "avg_price": round(avg, 8),
            "total_invested": round(s["total_cost"], 8),
        })

    return positions


# ---------------------------------------------------------------------------
# enrich_with_prices
# ---------------------------------------------------------------------------

def enrich_with_prices(
    positions: list[dict],
    prices: dict[str, float],
) -> list[dict]:
    enriched = []
    for p in positions:
        ticker = p["ticker"]
        price = prices.get(ticker)
        item = dict(p)
        if price is not None:
            qty = p["quantity"]
            invested = p["total_invested"]
            cur_val = qty * price
            result_abs = cur_val - invested
            result_pct = (result_abs / invested * 100) if invested else 0.0
            item["current_price"] = price
            item["current_value"] = cur_val
            item["result_abs"] = result_abs
            item["result_pct"] = round(result_pct, 4)
        else:
            item["current_price"] = None
            item["current_value"] = None
            item["result_abs"] = None
            item["result_pct"] = None
        enriched.append(item)
    return enriched


# ---------------------------------------------------------------------------
# sum_dividends
# ---------------------------------------------------------------------------

async def sum_dividends(
    db: AsyncSession,
    portfolio_id: int,
    cutoff: DateType | None = None,
) -> float:
    from app.models.asset_dividend import AssetDividend

    q = select(func.sum(Dividend.total_value)).where(
        Dividend.portfolio_id == portfolio_id
    )
    if cutoff is not None:
        q = q.join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id).where(
            AssetDividend.ex_date >= cutoff
        )
    result = await db.execute(q)
    total = result.scalar_one_or_none()
    return float(total) if total is not None else 0.0


# ---------------------------------------------------------------------------
# CRUD de carteiras
# ---------------------------------------------------------------------------

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
        raise HTTPException(status_code=404, detail="Carteira nao encontrada")
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
    positions_raw = await calc_raw_positions(db, portfolio_id)
    total_invested = sum(p["total_invested"] for p in positions_raw)

    current_value = 0.0
    for p in positions_raw:
        price_now = await get_current_price(p["ticker"])
        if price_now:
            current_value += p["quantity"] * price_now
        else:
            current_value += p["total_invested"]

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
    positions_raw = await calc_raw_positions(db, portfolio_id)

    prices: dict[str, float] = {}
    for p in positions_raw:
        price = await get_current_price(p["ticker"])
        if price:
            prices[p["ticker"]] = price

    enriched = enrich_with_prices(positions_raw, prices)

    total_current = sum(
        e["current_value"] for e in enriched if e["current_value"] is not None
    )

    result_list = []
    for e in enriched:
        cur_val = e["current_value"] or e["total_invested"]
        alloc = (cur_val / total_current * 100) if total_current else 0
        result_list.append({
            "ticker": e["ticker"],
            "asset_type": e["asset_type"],
            "quantity": round(e["quantity"], 8),
            "average_price": round(e["avg_price"], 4),
            "current_price": e["current_price"],
            "current_value": e["current_value"],
            "invested_value": round(e["total_invested"], 2),
            "result_abs": e["result_abs"],
            "result_pct": e["result_pct"],
            "allocation_pct": round(alloc, 4),
        })
    return result_list


async def get_asset_distribution(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    positions = await get_portfolio_positions(db, portfolio_id, user_id)
    by_type: dict[str, float] = {}
    for p in positions:
        at = p.get("asset_type") or "OUTRO"
        val = p["current_value"] or p["invested_value"]
        by_type[at] = by_type.get(at, 0) + val
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
