"""
proventos_service.py — agregacoes e leituras de proventos.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus
from app.models.transaction import Transaction, OperationType
from app.services.dividend_backfill_service import materialize_asset_dividends

logger = logging.getLogger(__name__)

_AUTO_MATERIALIZE_TTL_SECONDS = 60.0
_auto_materialize_cache: dict[int, float] = {}


def _first_buy_subquery():
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


def _calc_net_qty(txs: list[tuple], ref_date: date) -> float:
    qty = 0.0
    for tx_date, op, q in txs:
        if tx_date > ref_date:
            continue
        op_val = op.value if isinstance(op, OperationType) else str(op)
        if op_val == "buy":
            qty += float(q)
        elif op_val == "sell":
            qty -= float(q)
    return max(qty, 0.0)


async def _reconcile_portfolio_dividend_rights(db: AsyncSession, portfolio_id: int, tickers: list[str]) -> int:
    """
    Remove materializações que não fazem mais sentido após alteração/exclusão de
    transações. O evento global permanece em AssetDividend; só o vínculo da
    carteira é removido se a carteira não tinha posição na Data Com/Data Ex.
    """
    if not tickers:
        return 0

    tx_rows = await db.execute(
        select(Transaction.ticker, Transaction.date, Transaction.operation, Transaction.quantity)
        .where(Transaction.portfolio_id == portfolio_id, Transaction.ticker.in_(tickers))
    )
    txs_by_ticker: dict[str, list[tuple]] = {}
    for ticker, tx_date, op, qty in tx_rows.all():
        txs_by_ticker.setdefault(str(ticker).upper(), []).append((tx_date, op, qty))

    div_rows = await db.execute(
        select(Dividend, AssetDividend, Asset.ticker)
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .where(Dividend.portfolio_id == portfolio_id, Asset.ticker.in_(tickers))
    )

    removed = 0
    for div, asset_div, ticker in div_rows.all():
        entitlement_date = asset_div.record_date or asset_div.ex_date
        qty = _calc_net_qty(txs_by_ticker.get(str(ticker).upper(), []), entitlement_date)
        if qty <= 0:
            await db.delete(div)
            removed += 1

    return removed


async def ensure_portfolio_proventos(db: AsyncSession, portfolio_id: int, force: bool = False) -> int:
    """
    Garante que a página de Proventos reflita automaticamente os ativos da carteira.

    Não chama provedores externos. Materializa eventos globais já coletados e
    reconcilia vínculos da carteira usando a posição do investidor na Data Com.
    """
    now = time.monotonic()
    if not force and now < _auto_materialize_cache.get(portfolio_id, 0.0):
        return 0

    rows = await db.execute(
        select(Transaction.ticker)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    tickers = [str(row[0]).upper() for row in rows.all() if row[0]]
    if not tickers:
        _auto_materialize_cache[portfolio_id] = now + _AUTO_MATERIALIZE_TTL_SECONDS
        return 0

    changed = await materialize_asset_dividends(db=db, tickers=tickers, portfolio_id=portfolio_id, commit=False)
    removed = await _reconcile_portfolio_dividend_rights(db, portfolio_id, tickers)
    await db.commit()

    _auto_materialize_cache[portfolio_id] = time.monotonic() + _AUTO_MATERIALIZE_TTL_SECONDS
    total = changed + removed
    if total:
        logger.info(
            "[proventos] portfolio=%s: auto-sync concluido (%s criados/atualizados, %s removidos)",
            portfolio_id,
            changed,
            removed,
        )
    return total


async def get_summary(db: AsyncSession, portfolio_id: int) -> dict:
    today = date.today()
    start_12m = today - relativedelta(months=12)

    res = await db.execute(
        select(func.sum(Dividend.net_value))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(Dividend.portfolio_id == portfolio_id, Dividend.status == DividendStatus.RECEBIDO)
    )
    total_recebido = float(res.scalar_one() or 0.0)

    res = await db.execute(
        select(func.sum(Dividend.net_value))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(Dividend.portfolio_id == portfolio_id, Dividend.status == DividendStatus.A_RECEBER)
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
        .join(first_buy, (first_buy.c.portfolio_id == Dividend.portfolio_id) & (first_buy.c.ticker == Asset.ticker))
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

    stmt = base.order_by(AssetDividend.payment_date.desc().nullslast(), AssetDividend.ex_date.desc()).offset((page - 1) * page_size).limit(page_size)
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
        select(extract("year", AssetDividend.payment_date).label("year"), extract("month", AssetDividend.payment_date).label("month"), func.sum(Dividend.net_value).label("total"))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .join(first_buy, (first_buy.c.portfolio_id == Dividend.portfolio_id) & (first_buy.c.ticker == Asset.ticker))
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
        result.append({"year": year, "months": months_vals, "total": round(total, 2), "media": round(media, 2)})
    return result


async def get_distribution(db: AsyncSession, portfolio_id: int, months: int = 12) -> list[dict]:
    start = date.today() - relativedelta(months=months)
    stmt = (
        select(Asset.ticker, Asset.asset_type, func.sum(Dividend.net_value).label("total"))
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .where(Dividend.portfolio_id == portfolio_id, AssetDividend.payment_date >= start)
        .group_by(Asset.ticker, Asset.asset_type)
        .order_by(func.sum(Dividend.net_value).desc())
    )
    rows = (await db.execute(stmt)).fetchall()

    grand_total = sum(float(r.total) for r in rows) or 1.0
    return [
        {"ticker": r.ticker, "asset_type": r.asset_type, "total": round(float(r.total), 2), "percentage": round(float(r.total) / grand_total * 100, 2)}
        for r in rows
    ]
