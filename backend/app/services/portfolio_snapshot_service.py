"""
Servico de snapshots diarios de patrimonio.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, case, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction, OperationType
from app.services.price_history_service import get_price_at_date, persist_daily_prices

logger = logging.getLogger(__name__)


class _TickerState:
    __slots__ = ("ticker", "asset_type", "qty", "cost", "realized_pnl")

    def __init__(self, ticker: str, asset_type: str):
        self.ticker = ticker
        self.asset_type = asset_type
        self.qty = Decimal("0")
        self.cost = Decimal("0")
        self.realized_pnl = Decimal("0")

    def buy(self, qty: Decimal, price: Decimal, fees: Decimal = Decimal("0")) -> None:
        self.qty += qty
        self.cost += qty * price + fees

    def sell(self, qty: Decimal, price: Decimal) -> None:
        sold = min(qty, self.qty)
        if self.qty > 0:
            avg = self.cost / self.qty
            self.realized_pnl += sold * (price - avg)
            self.cost -= sold * avg
        self.qty -= sold
        self.qty = max(self.qty, Decimal("0"))
        self.cost = max(self.cost, Decimal("0"))

    @property
    def avg_price(self) -> Decimal:
        return self.cost / self.qty if self.qty > 0 else Decimal("0")


def _safe_div(a: Decimal, b: Decimal) -> Decimal:
    return a / b if b else Decimal("0")


async def _build_positions_at(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, _TickerState]:
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()

    states: dict[str, _TickerState] = {}
    for tx in txs:
        key = tx.ticker.upper()
        if key not in states:
            states[key] = _TickerState(key, tx.asset_type)
        s = states[key]
        qty = Decimal(str(tx.quantity))
        price = Decimal(str(tx.price))
        fees = Decimal(str(tx.fees or 0))
        if tx.operation == OperationType.buy:
            s.buy(qty, price, fees)
        elif tx.operation == OperationType.sell:
            s.sell(qty, price)

    return {k: v for k, v in states.items() if v.qty > 0}


async def _calc_totals(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict:
    positions = await _build_positions_at(db, portfolio_id, target_date)
    if not positions:
        return {
            "market_value": Decimal("0"),
            "cost_basis": Decimal("0"),
            "invested_total": Decimal("0"),
            "realized_pnl": Decimal("0"),
            "unrealized_pnl": Decimal("0"),
            "total_pnl": Decimal("0"),
            "return_pct": Decimal("0"),
        }

    date_str = target_date.isoformat()
    market_value = Decimal("0")
    cost_basis = Decimal("0")
    realized_pnl = Decimal("0")

    for ticker, state in positions.items():
        asset_result = await db.execute(
            select(Asset).where(Asset.ticker == ticker)
        )
        asset = asset_result.scalar_one_or_none()
        asset_type = AssetType(state.asset_type) if asset is None else asset.asset_type

        close = await get_price_at_date(db, ticker, asset_type, date_str)
        if close is None:
            close = float(state.avg_price)
            logger.warning(
                "[snapshot] sem cotacao para %s em %s - usando avg_price como proxy",
                ticker, date_str,
            )

        market_value += state.qty * Decimal(str(close))
        cost_basis += state.cost
        realized_pnl += state.realized_pnl

    invested_result = await db.execute(
        select(
            func.sum(
                case(
                    (
                        Transaction.operation == OperationType.buy,
                        Transaction.price * Transaction.quantity + func.coalesce(Transaction.fees, 0),
                    ),
                    else_=-(Transaction.price * Transaction.quantity),
                )
            )
        ).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= target_date,
        )
    )
    invested_total = Decimal(str(invested_result.scalar_one() or 0))

    unrealized_pnl = market_value - cost_basis
    total_pnl = realized_pnl + unrealized_pnl
    return_pct = _safe_div(total_pnl, invested_total) * 100 if invested_total > 0 else Decimal("0")

    return {
        "market_value": market_value.quantize(Decimal("0.01")),
        "cost_basis": cost_basis.quantize(Decimal("0.01")),
        "invested_total": invested_total.quantize(Decimal("0.01")),
        "realized_pnl": realized_pnl.quantize(Decimal("0.01")),
        "unrealized_pnl": unrealized_pnl.quantize(Decimal("0.01")),
        "total_pnl": total_pnl.quantize(Decimal("0.01")),
        "return_pct": return_pct.quantize(Decimal("0.0001")),
    }


async def _upsert_snapshot(
    db: AsyncSession,
    portfolio_id: int,
    snapshot_date: date,
    totals: dict,
) -> None:
    stmt = (
        pg_insert(PortfolioSnapshot)
        .values(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            **totals,
        )
        .on_conflict_do_update(
            constraint="uq_snapshot_portfolio_date",
            set_={
                "market_value": totals["market_value"],
                "cost_basis": totals["cost_basis"],
                "invested_total": totals["invested_total"],
                "realized_pnl": totals["realized_pnl"],
                "unrealized_pnl": totals["unrealized_pnl"],
                "total_pnl": totals["total_pnl"],
                "return_pct": totals["return_pct"],
            },
        )
    )
    await db.execute(stmt)


async def _prefetch_price_history(
    db: AsyncSession,
    portfolio_id: int,
    days_back: int,
) -> None:
    """
    Popula o banco com historico de precos para todos os tickers do portfolio
    antes de iniciar qualquer loop de calculo por data.

    Isso transforma o loop de backfill em operacao somente-leitura:
    get_price_at_date acha os dados no banco e nao aciona BRAPI/yfinance
    a cada combinacao ticker+data. Apos o pre-fetch, o _persist_cooldown
    (30min) garante que chamadas subsequentes dentro do loop retornem 0.
    """
    result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    tickers = result.all()
    if not tickers:
        return

    logger.info(
        "[snapshot] pre-fetch de historico para %d tickers (days_back=%d)",
        len(tickers), days_back,
    )
    for row in tickers:
        ticker = row.ticker.upper()
        try:
            asset_type = AssetType(row.asset_type)
        except ValueError:
            asset_type = AssetType.ACAO
        await persist_daily_prices(db, ticker, asset_type, days_back=days_back)


async def calc_snapshot_at_date(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
    commit: bool = True,
    prefetch: bool = False,
) -> dict:
    """
    Calcula e persiste snapshot para uma data especifica.
    prefetch=True dispara _prefetch_price_history antes do calculo
    (util para chamadas isoladas fora do backfill).
    """
    if prefetch:
        days_back = (date.today() - target_date).days + 6
        await _prefetch_price_history(db, portfolio_id, days_back)

    totals = await _calc_totals(db, portfolio_id, target_date)
    await _upsert_snapshot(db, portfolio_id, target_date, totals)
    if commit:
        await db.commit()
    logger.info(
        "[snapshot] portfolio=%s date=%s market_value=%s return_pct=%s%%",
        portfolio_id, target_date, totals["market_value"], totals["return_pct"],
    )
    return totals


async def backfill_snapshots(
    db: AsyncSession,
    portfolio_id: int,
    days_back: Optional[int] = None,
) -> int:
    first_tx = await db.execute(
        select(func.min(Transaction.date))
        .where(Transaction.portfolio_id == portfolio_id)
    )
    first_date = first_tx.scalar_one_or_none()
    if first_date is None:
        return 0

    start = first_date
    if days_back is not None:
        start = max(start, date.today() - timedelta(days=days_back))

    total_days = (date.today() - start).days + 1

    existing = await db.execute(
        select(PortfolioSnapshot.snapshot_date)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= start,
            PortfolioSnapshot.snapshot_date < date.today(),
        )
    )
    existing_dates = {r.snapshot_date for r in existing.all()}

    # Pre-fetch: popula banco com historico completo de todos os tickers
    # antes do loop. O loop vira somente leitura (sem BRAPI/yfinance).
    await _prefetch_price_history(db, portfolio_id, days_back=total_days)

    count = 0
    cursor = start
    today = date.today()

    while cursor <= today:
        if cursor.weekday() < 5 and cursor not in existing_dates:
            totals = await _calc_totals(db, portfolio_id, cursor)
            await _upsert_snapshot(db, portfolio_id, cursor, totals)
            count += 1
            if count % 30 == 0:
                await db.commit()
        cursor += timedelta(days=1)

    await db.commit()
    logger.info(
        "[snapshot] backfill portfolio=%s: %s snapshots processados (start=%s)",
        portfolio_id, count, start,
    )
    return count


async def refresh_today_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> dict:
    return await calc_snapshot_at_date(
        db, portfolio_id, date.today(), commit=True, prefetch=True
    )


async def get_daily_evolution(
    db: AsyncSession,
    portfolio_id: int,
    days: int = 365,
) -> list[dict]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= since,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "date": str(r.snapshot_date),
            "market_value": float(r.market_value),
            "cost_basis": float(r.cost_basis),
            "invested_total": float(r.invested_total),
            "unrealized_pnl": float(r.unrealized_pnl),
            "realized_pnl": float(r.realized_pnl),
            "total_pnl": float(r.total_pnl),
            "return_pct": float(r.return_pct),
        }
        for r in rows
    ]


async def get_monthly_evolution(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 24,
) -> list[dict]:
    since = date.today() - timedelta(days=months * 31)
    sub = (
        select(
            func.date_trunc("month", PortfolioSnapshot.snapshot_date).label("month"),
            func.max(PortfolioSnapshot.snapshot_date).label("last_date"),
        )
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= since,
        )
        .group_by(text("1"))
        .subquery()
    )

    result = await db.execute(
        select(PortfolioSnapshot)
        .join(sub, PortfolioSnapshot.snapshot_date == sub.c.last_date)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "date": r.snapshot_date.strftime("%Y-%m-%d"),
            "value": float(r.market_value),
            "invested": float(r.invested_total),
            "period": r.snapshot_date.strftime("%Y-%m"),
            "market_value": float(r.market_value),
            "cost_basis": float(r.cost_basis),
            "invested_total": float(r.invested_total),
            "unrealized_pnl": float(r.unrealized_pnl),
            "realized_pnl": float(r.realized_pnl),
            "total_pnl": float(r.total_pnl),
            "return_pct": float(r.return_pct),
        }
        for r in rows
    ]
