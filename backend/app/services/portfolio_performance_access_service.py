"""Authorized entrypoints for portfolio performance read surfaces."""
from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.services.performance_service import get_portfolio_performance
from app.services.portfolio_class_reconciliation_service import (
    reconcile_latest_class_snapshots,
)
from app.services.portfolio_class_snapshot_read_service import (
    get_class_twr_availability,
    get_daily_class_evolution,
    get_monthly_class_evolution,
)
from app.services.portfolio_snapshot_read_service import (
    get_enriched_daily_evolution,
    get_enriched_monthly_evolution,
)
from app.services.rentabilidade_asset_result_service import get_canonical_asset_results
from app.services.rentabilidade_benchmark_service import get_persisted_monthly_benchmarks
from app.services.rentabilidade_class_service import get_canonical_class_performance
from app.services.rentabilidade_kpi_service import get_rentabilidade_kpis
from app.services.rentabilidade_reconciliation_service import reconcile_rentabilidade_page


READ_PORTFOLIO_RENTABILIDADE = "read:portfolio_rentabilidade"
READ_PORTFOLIO_PERFORMANCE = "read:portfolio_performance"


async def _authorize(
    db: AsyncSession,
    access: PortfolioAccessContext,
    permission: str,
) -> int:
    try:
        await get_accessible_portfolio(db, access, required_permission=permission)
    except PortfolioAccessDenied:
        raise
    if access.user_id is None:
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")
    return access.user_id


async def get_authorized_performance(
    db: AsyncSession, access: PortfolioAccessContext
) -> dict:
    user_id = await _authorize(db, access, READ_PORTFOLIO_PERFORMANCE)
    return await get_portfolio_performance(db, access.portfolio_id, user_id)


async def get_authorized_daily_evolution(
    db: AsyncSession, access: PortfolioAccessContext, *, days: int
) -> list[dict]:
    await _authorize(db, access, READ_PORTFOLIO_PERFORMANCE)
    return await get_enriched_daily_evolution(db, access.portfolio_id, days=days)


async def get_authorized_monthly_evolution(
    db: AsyncSession, access: PortfolioAccessContext, *, months: int
) -> list[dict]:
    await _authorize(db, access, READ_PORTFOLIO_PERFORMANCE)
    return await get_enriched_monthly_evolution(db, access.portfolio_id, months=months)


async def get_authorized_class_availability(
    db: AsyncSession, access: PortfolioAccessContext
) -> list[dict]:
    await _authorize(db, access, READ_PORTFOLIO_PERFORMANCE)
    return await get_class_twr_availability(db, access.portfolio_id)


async def get_authorized_class_reconciliation(
    db: AsyncSession, access: PortfolioAccessContext
) -> dict:
    await _authorize(db, access, READ_PORTFOLIO_PERFORMANCE)
    return await reconcile_latest_class_snapshots(db, access.portfolio_id)


async def get_authorized_class_daily_evolution(
    db: AsyncSession,
    access: PortfolioAccessContext,
    asset_type: str,
    *,
    days: int,
) -> list[dict]:
    await _authorize(db, access, READ_PORTFOLIO_PERFORMANCE)
    return await get_daily_class_evolution(
        db, access.portfolio_id, asset_type, days=days
    )


async def get_authorized_class_monthly_evolution(
    db: AsyncSession,
    access: PortfolioAccessContext,
    asset_type: str,
    *,
    months: int,
) -> list[dict]:
    await _authorize(db, access, READ_PORTFOLIO_PERFORMANCE)
    return await get_monthly_class_evolution(
        db, access.portfolio_id, asset_type, months=months
    )


async def get_authorized_rentabilidade_kpis(
    db: AsyncSession, access: PortfolioAccessContext
) -> dict:
    user_id = await _authorize(db, access, READ_PORTFOLIO_RENTABILIDADE)
    return await get_rentabilidade_kpis(db, access.portfolio_id, user_id)


async def get_authorized_rentabilidade_assets(
    db: AsyncSession, access: PortfolioAccessContext
) -> list[dict]:
    user_id = await _authorize(db, access, READ_PORTFOLIO_RENTABILIDADE)
    return await get_canonical_asset_results(db, access.portfolio_id, user_id)


async def get_authorized_rentabilidade_classes(
    db: AsyncSession, access: PortfolioAccessContext
) -> list[dict]:
    user_id = await _authorize(db, access, READ_PORTFOLIO_RENTABILIDADE)
    return await get_canonical_class_performance(db, access.portfolio_id, user_id)


async def get_authorized_monthly_benchmarks(
    db: AsyncSession,
    access: PortfolioAccessContext,
    *,
    months: int,
    end_date: date | None = None,
) -> dict:
    await _authorize(db, access, READ_PORTFOLIO_RENTABILIDADE)
    return await get_persisted_monthly_benchmarks(db, months=months, end_date=end_date)


async def get_authorized_rentabilidade_reconciliation(
    db: AsyncSession, access: PortfolioAccessContext
) -> dict:
    user_id = await _authorize(db, access, READ_PORTFOLIO_RENTABILIDADE)
    return await reconcile_rentabilidade_page(db, access.portfolio_id, user_id)
