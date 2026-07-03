"""
proventos_service.py — agregacoes e leituras de proventos.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus
from app.models.transaction import Transaction, OperationType

logger = logging.getLogger(__name__)


def _first_buy_subquery():
    """Subquery que retorna a primeira data de compra (buy) por portfolio_id + ticker."""
    return (
        select(
            Transaction.portfolio_id.label("portfolio_id"),
            Transaction.ticker.label("ticker"),
            func.min(Transaction.date).label("first_buy"),
        )
        .where(Transaction.operation == OperationType.buy)
        .group_by(Transaction.portfolio_id, Transaction.ticker)
        .subquery()
    )


async def get_summary(db: AsyncSession, portfolio_id: int) -> dict:
    today = date.today()
    start_12m = today - relativedelta(months=12)

    res = await db.execute(
        select(func.sum(Dividend.net_value))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(
            Dividend.portfolio_id == portfolio_id,
            Dividend.status == DividendStatus.RECEBIDO,
        )
    )
    total_recebido = float(res.scalar_one() or 0.0)

    res = await db.execute(
        select(func.sum(Dividend.net_value))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(
            Dividend.portfolio_id == portfolio_id,
            Dividend.status == DividendStatus.A_RECEBER,
        )
    )
    total_a_receber = float(res.scalar_one() or 0.0)

    res = await db.execute(
        select(func.sum(Dividend.net_value))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(
            Dividend.portfolio_id == portfolio_id,
            Dividend.status == DividendStatus.RECEBIDO,
            AssetDividend.payment_date >= start_12m,
        )
    )
    total_12m = float(res.scalar_one() or 0.0)

    return {
        "total_recebido": total_recebido,
        "total_a_receber": total_a_receber,
        "total_12m": total_12m,
        "media_mensal_12m": round(total_12m / 12, 2),
    }


async def list_items(
    db: AsyncSession,
    portfolio_id: int,
    status: Optional[DividendStatus] = None,
    year: Optional[int] = None,
    asset_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    first_buy = _first_buy_subquery()

    base = (
        select(
            Dividend.id,
            Dividend.portfolio_id,
            Dividend.quantity,
            Dividend.total_value,
            Dividend.net_value,
            Dividend.status,
            AssetDividend.record_date,
            AssetDividend.ex_date,
            AssetDividend.payment_date,
            AssetDividend.approved_on,
            AssetDividend.value_per_unit,
            AssetDividend.gross_value_per_unit,
            AssetDividend.factor,
            AssetDividend.complete_factor,
            AssetDividend.dividend_type,
            AssetDividend.isin_code,
            AssetDividend.asset_issued,
            AssetDividend.related_to,
            AssetDividend.remarks,
            Asset.ticker,
            Asset.asset_type,
        )
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .join(
            first_buy,
            (first_buy.c.portfolio_id == Dividend.portfolio_id)
            & (first_buy.c.ticker == Asset.ticker),
        )
        .where(
            Dividend.portfolio_id == portfolio_id,
            (AssetDividend.record_date >= first_buy.c.first_buy) | (AssetDividend.ex_date >= first_buy.c.first_buy),
        )
    )

    if status:
        base = base.where(Dividend.status == status)
    if year:
        base = base.where(extract("year", AssetDividend.payment_date) == year)
    if asset_type:
        base = base.where(Asset.asset_type == asset_type)

    count_res = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_res.scalar_one()

    stmt = (
        base
        .order_by(AssetDividend.payment_date.desc().nullslast(), AssetDividend.ex_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).fetchall()

    items = [
        {
            "id": row.id,
            "ticker": row.ticker,
            "asset_type": row.asset_type,
            "dividend_type": row.dividend_type,
            "record_date": row.record_date,
            "ex_date": row.ex_date,
            "payment_date": row.payment_date,
            "approved_on": row.approved_on,
            "value_per_unit": float(row.value_per_unit),
            "gross_value_per_unit": float(row.gross_value_per_unit) if row.gross_value_per_unit else None,
            "factor": float(row.factor) if row.factor else None,
            "complete_factor": float(row.complete_factor) if row.complete_factor else None,
            "isin_code": row.isin_code,
            "asset_issued": row.asset_issued,
            "related_to": row.related_to,
            "remarks": row.remarks,
            "quantity": float(row.quantity),
            "total_value": float(row.total_value) if row.total_value else 0.0,
            "net_value": float(row.net_value) if row.net_value else 0.0,
            "status": row.status,
        }
        for row in rows
    ]

    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_monthly_history(
    db: AsyncSession,
    portfolio_id: int,
    status: Optional[DividendStatus] = None,
    asset_type: Optional[str] = None,
) -> list[dict]:
    first_buy = _first_buy_subquery()

    stmt = (
        select(
            extract("year", AssetDividend.payment_date).label("year"),
            extract("month", AssetDividend.payment_date).label("month"),
            func.sum(Dividend.net_value).label("total"),
        )
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .join(
            first_buy,
            (first_buy.c.portfolio_id == Dividend.portfolio_id)
            & (first_buy.c.ticker == Asset.ticker),
        )
        .where(
            Dividend.portfolio_id == portfolio_id,
            AssetDividend.payment_date.isnot(None),
            (AssetDividend.record_date >= first_buy.c.first_buy) | (AssetDividend.ex_date >= first_buy.c.first_buy),
        )
    )

    if status:
        stmt = stmt.where(Dividend.status == status)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)

    stmt = stmt.group_by("year", "month").order_by("year", "month")
    rows = (await db.execute(stmt)).fetchall()

    data: dict[int, dict[int, float]] = {}
    for r in rows:
        y, m = int(r.year), int(r.month)
        data.setdefault(y, {})[m] = float(r.total)

    result = []
    for year in sorted(data.keys(), reverse=True):
        months_vals = [data[year].get(m) for m in range(1, 13)]
        values = [v for v in months_vals if v is not None]
        total = sum(values)
        media = total / len(values) if values else 0.0
        result.append({
            "year": year,
            "months": months_vals,
            "total": round(total, 2),
            "media": round(media, 2),
        })
    return result


async def get_distribution(db: AsyncSession, portfolio_id: int, months: int = 12) -> list[dict]:
    start = date.today() - relativedelta(months=months)

    stmt = (
        select(Asset.ticker, Asset.asset_type, func.sum(Dividend.net_value).label("total"))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .where(
            Dividend.portfolio_id == portfolio_id,
            AssetDividend.payment_date >= start,
        )
        .group_by(Asset.ticker, Asset.asset_type)
        .order_by(func.sum(Dividend.net_value).desc())
    )
    rows = (await db.execute(stmt)).fetchall()

    grand_total = sum(float(r.total) for r in rows) or 1.0
    return [
        {
            "ticker": r.ticker,
            "asset_type": r.asset_type,
            "total": round(float(r.total), 2),
            "percentage": round(float(r.total) / grand_total * 100, 2),
        }
        for r in rows
    ]
