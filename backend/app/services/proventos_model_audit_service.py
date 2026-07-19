"""Inventário read-only para a normalização segura do modelo de proventos."""

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend
from app.models.dividends_sync_job import DividendsSyncJob


@dataclass(frozen=True)
class ProventosModelAudit:
    """Contagens que precisam chegar a zero antes da contração do schema."""

    asset_events: int
    portfolio_rights: int
    unlinked_portfolio_rights: int
    duplicate_materialization_groups: int
    ex_date_mismatches: int
    payment_date_mismatches: int
    quantity_mismatches: int
    value_per_unit_mismatches: int
    legacy_sync_job_rows: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _different(
    canonical: ColumnElement[Any],
    legacy: ColumnElement[Any],
) -> ColumnElement[bool]:
    """Compara colunas de forma null-safe e portável entre SQLite/PostgreSQL."""
    return or_(
        canonical != legacy,
        and_(canonical.is_(None), legacy.is_not(None)),
        and_(canonical.is_not(None), legacy.is_(None)),
    )


async def _count(
    db: AsyncSession,
    model: type[Any],
    condition: ColumnElement[bool] | None = None,
) -> int:
    statement = select(func.count()).select_from(model)
    if condition is not None:
        statement = statement.where(condition)
    return int((await db.execute(statement)).scalar_one())


async def audit_proventos_model(db: AsyncSession) -> ProventosModelAudit:
    """Lê o estado de compatibilidade do modelo sem alterar a sessão ou o banco."""
    duplicate_groups = (
        select(Dividend.portfolio_id, Dividend.asset_dividend_id)
        .where(Dividend.asset_dividend_id.is_not(None))
        .group_by(Dividend.portfolio_id, Dividend.asset_dividend_id)
        .having(func.count(Dividend.id) > 1)
        .subquery()
    )
    duplicate_count = int(
        (
            await db.execute(
                select(func.count()).select_from(duplicate_groups)
            )
        ).scalar_one()
    )

    return ProventosModelAudit(
        asset_events=await _count(db, AssetDividend),
        portfolio_rights=await _count(db, Dividend),
        unlinked_portfolio_rights=await _count(
            db, Dividend, Dividend.asset_dividend_id.is_(None)
        ),
        duplicate_materialization_groups=duplicate_count,
        ex_date_mismatches=await _count(
            db, Dividend, _different(Dividend.ex_date, Dividend.date_ex)
        ),
        payment_date_mismatches=await _count(
            db,
            Dividend,
            _different(Dividend.payment_date, Dividend.date_pagamento),
        ),
        quantity_mismatches=await _count(
            db, Dividend, _different(Dividend.quantity, Dividend.quantity_on_date)
        ),
        value_per_unit_mismatches=await _count(
            db,
            Dividend,
            _different(Dividend.value_per_unit, Dividend.value_per_share),
        ),
        legacy_sync_job_rows=await _count(db, DividendsSyncJob),
    )
