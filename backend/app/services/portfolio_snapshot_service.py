"""
Servico de snapshots diarios de patrimonio.

SEMANTICA DOS CAMPOS CALCULADOS
================================
Os snapshots capturam o retorno de PRECO puro da carteira, sem proventos.

  total_pnl  = realized_pnl + unrealized_pnl
               Lucro/prejuizo de compra e venda e valorizacao de preco.
               NAO inclui dividendos, JCP ou outros proventos recebidos.
               Renda Fixa e Tesouro usam os mesmos motores dedicados do
               valuation canonico; nao existe fallback paralelo no snapshot.

  return_pct = total_pnl / (cost_basis + max(realized_pnl, 0)) * 100
               Percentual de retorno de preco sobre capital empregado.
               Usa cost_basis + realized positivo como denominador para
               evitar distorcao quando ha muitas vendas.

FLUXO DE ATUALIZACAO
====================
  backfill_snapshots       : reconstroi historico dia a dia usando dados persistidos
  refresh_today_snapshot   : atualiza o snapshot de hoje
  invalidate_snapshots_from: remove snapshots a partir de uma data

POLITICA DE PRECO
=================
A leitura e estritamente DB-first e delega ao valuation canonico da carteira.
Ausencia de cobertura persistida permanece fail-closed e nunca aciona providers
no runtime financeiro.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Portfolio
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction
from app.services.portfolio_canonical_valuation_service import (
    calculate_canonical_portfolio_totals,
)
from app.services.portfolio_position_state_service import (
    TickerState as _TickerState,
    build_positions_at as _build_positions_at,
)

logger = logging.getLogger(__name__)

_SNAPSHOT_TOTAL_FIELDS = (
    "market_value",
    "cost_basis",
    "invested_total",
    "realized_pnl",
    "unrealized_pnl",
    "total_pnl",
    "return_pct",
)


async def invalidate_snapshots_from(
    db: AsyncSession,
    portfolio_id: int,
    from_date: date,
    commit: bool = False,
) -> int:
    stmt = delete(PortfolioSnapshot).where(
        PortfolioSnapshot.portfolio_id == portfolio_id,
        PortfolioSnapshot.snapshot_date >= from_date,
    )
    result = await db.execute(stmt)
    deleted = result.rowcount
    if commit:
        await db.commit()
    logger.info(
        "[snapshot] invalidate portfolio=%s from=%s — %s snapshots removidos",
        portfolio_id,
        from_date,
        deleted,
    )
    return deleted


async def _calc_totals(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict:
    """Projeta os campos do snapshot a partir do valuation canônico único."""
    totals = await calculate_canonical_portfolio_totals(db, portfolio_id, target_date)
    return {field: totals[field] for field in _SNAPSHOT_TOTAL_FIELDS}


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


async def calc_snapshot_at_date(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
    commit: bool = True,
    prefetch: bool = False,
) -> dict:
    """Calcula snapshot exclusivamente com dados persistidos.

    `prefetch` permanece temporariamente na assinatura por compatibilidade interna,
    mas nao dispara qualquer carga historica ampla.
    """
    if prefetch:
        logger.debug("[snapshot] prefetch legado ignorado; leitura permanece DB-first")

    totals = await _calc_totals(db, portfolio_id, target_date)
    await _upsert_snapshot(db, portfolio_id, target_date, totals)
    if commit:
        await db.commit()
    logger.info(
        "[snapshot] portfolio=%s date=%s market_value=%s return_pct=%s%%",
        portfolio_id,
        target_date,
        totals["market_value"],
        totals["return_pct"],
    )
    return totals


async def backfill_snapshots(
    db: AsyncSession,
    portfolio_id: int,
    days_back: Optional[int] = None,
) -> int:
    first_tx = await db.execute(
        select(func.min(Transaction.date)).where(
            Transaction.portfolio_id == portfolio_id
        )
    )
    first_date = first_tx.scalar_one_or_none()
    if first_date is None:
        return 0

    start = first_date
    if days_back is not None:
        start = max(start, date.today() - timedelta(days=days_back))

    existing = await db.execute(
        select(PortfolioSnapshot.snapshot_date).where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= start,
            PortfolioSnapshot.snapshot_date < date.today(),
        )
    )
    existing_dates = {r.snapshot_date for r in existing.all()}

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
        portfolio_id,
        count,
        start,
    )
    return count


async def refresh_today_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> dict:
    return await calc_snapshot_at_date(
        db,
        portfolio_id,
        date.today(),
        commit=True,
        prefetch=False,
    )


def _weekday_count(start: date, end: date) -> int:
    count = 0
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            count += 1
        cursor += timedelta(days=1)
    return count


async def snapshot_backfill_needed(
    db: AsyncSession,
    portfolio_id: int,
) -> bool:
    first_date = await _first_transaction_date(db, portfolio_id)
    if first_date is None:
        return False

    today = date.today()
    expected = _weekday_count(first_date, today)
    if expected == 0:
        return False

    result = await db.execute(
        select(func.count(func.distinct(PortfolioSnapshot.snapshot_date))).where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= first_date,
            PortfolioSnapshot.snapshot_date <= today,
        )
    )
    existing = int(result.scalar_one() or 0)
    return existing < expected


async def backfill_missing_snapshots_for_active_portfolios(
    db: AsyncSession,
) -> dict:
    result = await db.execute(
        select(Portfolio.id)
        .join(Transaction, Transaction.portfolio_id == Portfolio.id)
        .where(Portfolio.is_active.is_(True))
        .distinct()
    )
    portfolio_ids = [row.id for row in result.all()]

    processed = 0
    skipped = 0
    errors = 0
    snapshots = 0

    for portfolio_id in portfolio_ids:
        try:
            if not await snapshot_backfill_needed(db, portfolio_id):
                skipped += 1
                continue
            count = await backfill_snapshots(db, portfolio_id)
            processed += 1
            snapshots += count
        except Exception as exc:
            await db.rollback()
            errors += 1
            logger.error(
                "[snapshot_auto] portfolio=%s falhou: %s",
                portfolio_id,
                exc,
            )

    return {
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "snapshots": snapshots,
    }


async def _first_transaction_date(
    db: AsyncSession,
    portfolio_id: int,
) -> date | None:
    result = await db.execute(
        select(func.min(Transaction.date)).where(
            Transaction.portfolio_id == portfolio_id
        )
    )
    return result.scalar_one_or_none()
