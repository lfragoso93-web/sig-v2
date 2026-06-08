import logging
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.dividend import Dividend, DividendType
from app.models.portfolio_position import PortfolioPosition
from app.models.asset import Asset
from app.integrations.brapi import get_dividends_and_events
from app.schemas.dividend import DividendCreate
from typing import Optional

logger = logging.getLogger(__name__)

BRAPI_DIVIDEND_TYPE_MAP = {
    "DIVIDENDS": DividendType.DIVIDENDO,
    "JCP": DividendType.JCP,
    "RENDIMENTO": DividendType.RENDIMENTO,
    "AMORTIZACAO": DividendType.AMORTIZACAO,
}


async def sync_dividends_for_portfolio_position(
    db: AsyncSession, position: PortfolioPosition
) -> int:
    asset = position.asset
    ticker = asset.brapi_ticker or asset.ticker
    events = await get_dividends_and_events(ticker)
    new_count = 0

    for raw in events:
        event_type_str = raw.get("type", "")
        dividend_type = BRAPI_DIVIDEND_TYPE_MAP.get(event_type_str)
        if not dividend_type:
            continue

        rate = float(raw.get("rate") or 0)
        if rate <= 0:
            continue

        ex_date_str = raw.get("exDividendDate")
        try:
            ex_date = date.fromisoformat(ex_date_str[:10]) if ex_date_str else None
        except Exception:
            ex_date = None
        if not ex_date:
            continue

        pay_date_str = raw.get("paymentDate")
        try:
            payment_date = date.fromisoformat(pay_date_str[:10]) if pay_date_str else None
        except Exception:
            payment_date = None

        brapi_id = f"{ticker}_{event_type_str}_{ex_date_str}_{rate}_{position.portfolio_id}"

        existing = (await db.execute(
            select(Dividend).where(Dividend.brapi_event_id == brapi_id)
        )).scalar_one_or_none()
        if existing:
            continue

        qty_held = position.quantity
        value_per_unit = Decimal(str(rate))
        total_value = (qty_held * value_per_unit).quantize(Decimal("0.01"))

        db.add(Dividend(
            portfolio_id=position.portfolio_id,
            asset_id=asset.id,
            dividend_type=dividend_type,
            ex_date=ex_date,
            payment_date=payment_date,
            value_per_unit=value_per_unit,
            quantity_held=qty_held,
            total_value=total_value,
            is_automatic=True,
            brapi_event_id=brapi_id,
        ))
        new_count += 1
        logger.info(f"[Dividend] Novo: {ticker} {dividend_type} {ex_date} total=R${total_value}")

    await db.flush()
    return new_count


async def create_dividend_manual(
    db: AsyncSession, portfolio_id: int, data: DividendCreate
) -> Dividend:
    total_value = (data.quantity_held * data.value_per_unit).quantize(Decimal("0.01"))
    dividend = Dividend(
        portfolio_id=portfolio_id,
        asset_id=data.asset_id,
        dividend_type=data.dividend_type,
        ex_date=data.ex_date,
        payment_date=data.payment_date,
        value_per_unit=data.value_per_unit,
        quantity_held=data.quantity_held,
        total_value=total_value,
        is_automatic=False,
        notes=data.notes,
    )
    db.add(dividend)
    await db.flush()
    await db.refresh(dividend)
    return dividend


async def list_dividends(
    db: AsyncSession,
    portfolio_id: int,
    asset_id: Optional[int] = None,
    year: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Dividend], int]:
    stmt = select(Dividend).where(Dividend.portfolio_id == portfolio_id)
    count_stmt = select(func.count()).select_from(Dividend).where(
        Dividend.portfolio_id == portfolio_id
    )
    if asset_id:
        stmt = stmt.where(Dividend.asset_id == asset_id)
        count_stmt = count_stmt.where(Dividend.asset_id == asset_id)
    if year:
        stmt = stmt.where(func.extract("year", Dividend.ex_date) == year)
        count_stmt = count_stmt.where(func.extract("year", Dividend.ex_date) == year)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Dividend.ex_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def get_dividend_summary(
    db: AsyncSession, portfolio_id: int, year: Optional[int] = None
) -> dict:
    stmt = select(
        Dividend.dividend_type,
        func.sum(Dividend.total_value).label("total"),
    ).where(Dividend.portfolio_id == portfolio_id)
    if year:
        stmt = stmt.where(func.extract("year", Dividend.ex_date) == year)
    stmt = stmt.group_by(Dividend.dividend_type)
    rows = (await db.execute(stmt)).fetchall()
    return {
        "by_type": {row.dividend_type: float(row.total) for row in rows},
        "total": sum(float(row.total) for row in rows),
        "year": year,
    }
