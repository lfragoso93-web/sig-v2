"""Ponto de entrada canônico do full market rebuild.

Reutiliza o orquestrador estável e substitui somente a etapa de snapshots pelo
backfill que usa os motores de valuation dedicados.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.services import full_market_rebuild_service as base_rebuild
from app.services.portfolio_canonical_valuation_service import (
    calculate_canonical_portfolio_totals,
)
from app.services.portfolio_snapshot_canonical_twr_service import (
    backfill_canonical_snapshots_with_returns,
)

logger = logging.getLogger(__name__)
_ZERO = Decimal("0")


async def _rebuild_all_canonical_twr_snapshots() -> dict:
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Portfolio.id)
            .join(Transaction, Transaction.portfolio_id == Portfolio.id)
            .where(Portfolio.is_active.is_(True))
            .distinct()
            .order_by(Portfolio.id.asc())
        )
        portfolio_ids = [row.id for row in rows.all()]

    processed = 0
    snapshots = 0
    errors = 0
    fixed_income_invested = _ZERO
    fixed_income_current = _ZERO
    fixed_income_income = _ZERO
    treasury_correction = _ZERO
    treasury_matched = 0
    treasury_unresolved = 0

    for portfolio_id in portfolio_ids:
        try:
            async with AsyncSessionLocal() as db:
                snapshots += await backfill_canonical_snapshots_with_returns(db, portfolio_id)
                latest = await calculate_canonical_portfolio_totals(db, portfolio_id, date.today())

            fixed_income_invested += Decimal(str(latest.get("fixed_income_invested", 0)))
            fixed_income_current += Decimal(str(latest.get("fixed_income_current", 0)))
            fixed_income_income += Decimal(str(latest.get("fixed_income_income", 0)))
            treasury_correction += Decimal(str(latest.get("treasury_correction", 0)))
            treasury_matched += int(latest.get("treasury_matched", 0) or 0)
            treasury_unresolved += int(latest.get("treasury_unresolved", 0) or 0)
            processed += 1
        except Exception:
            errors += 1
            logger.exception(
                "[full_market_rebuild_canonical] falha ao reconstruir TWR portfolio=%s",
                portfolio_id,
            )

    return {
        "portfolios": len(portfolio_ids),
        "processed": processed,
        "errors": errors,
        "snapshots": snapshots,
        "valuation_mode": "canonical",
        "fixed_income_invested": fixed_income_invested.quantize(Decimal("0.01")),
        "fixed_income_current": fixed_income_current.quantize(Decimal("0.01")),
        "fixed_income_income": fixed_income_income.quantize(Decimal("0.01")),
        "treasury_correction": treasury_correction.quantize(Decimal("0.01")),
        "treasury_matched": treasury_matched,
        "treasury_unresolved": treasury_unresolved,
    }


def _canonical_step_payload(summary, name: str) -> dict:
    """Converte resultados dataclass antes de montar o resumo operacional."""
    for step in summary.steps:
        if step.name != name:
            continue
        payload = base_rebuild._jsonable(step.result)
        return payload if isinstance(payload, dict) else {}
    return {}


def _log_canonical_valuation(summary) -> None:
    payload = _canonical_step_payload(summary, "twr_snapshots")
    logger.info(
        "[canonical_valuation] fixed_income_invested=%s fixed_income_current=%s "
        "fixed_income_income=%s treasury_correction=%s treasury_matched=%s "
        "treasury_unresolved=%s",
        payload.get("fixed_income_invested", 0),
        payload.get("fixed_income_current", 0),
        payload.get("fixed_income_income", 0),
        payload.get("treasury_correction", 0),
        payload.get("treasury_matched", 0),
        payload.get("treasury_unresolved", 0),
    )


async def run_full_market_rebuild():
    """Executa o orquestrador existente com a etapa TWR canônica."""
    original_snapshots = base_rebuild._rebuild_all_twr_snapshots
    original_step_payload = base_rebuild._step_payload
    base_rebuild._rebuild_all_twr_snapshots = _rebuild_all_canonical_twr_snapshots
    base_rebuild._step_payload = _canonical_step_payload
    try:
        result = await base_rebuild.run_full_market_rebuild()
        _log_canonical_valuation(result)
        return result
    finally:
        base_rebuild._rebuild_all_twr_snapshots = original_snapshots
        base_rebuild._step_payload = original_step_payload
