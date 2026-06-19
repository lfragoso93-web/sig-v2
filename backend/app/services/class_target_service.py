"""
Service para CRUD das metas de alocação por classe de ativo.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.portfolio_class_target import PortfolioClassTarget
from decimal import Decimal


async def get_targets(db: AsyncSession, portfolio_id: int) -> list[PortfolioClassTarget]:
    result = await db.execute(
        select(PortfolioClassTarget).where(PortfolioClassTarget.portfolio_id == portfolio_id)
    )
    return list(result.scalars().all())


async def get_targets_map(db: AsyncSession, portfolio_id: int) -> dict[str, float]:
    """Retorna {asset_type: target_pct} para uso rápido no portfolio_service."""
    targets = await get_targets(db, portfolio_id)
    return {t.asset_type: float(t.target_pct) for t in targets}


async def upsert_target(
    db: AsyncSession,
    portfolio_id: int,
    asset_type: str,
    target_pct: float,
) -> PortfolioClassTarget:
    """Cria ou atualiza a meta de uma classe. Usa upsert manual para compatibilidade."""
    result = await db.execute(
        select(PortfolioClassTarget).where(
            PortfolioClassTarget.portfolio_id == portfolio_id,
            PortfolioClassTarget.asset_type == asset_type,
        )
    )
    target = result.scalar_one_or_none()

    if target is None:
        target = PortfolioClassTarget(
            portfolio_id=portfolio_id,
            asset_type=asset_type,
            target_pct=Decimal(str(round(target_pct, 2))),
        )
        db.add(target)
    else:
        target.target_pct = Decimal(str(round(target_pct, 2)))

    await db.commit()
    await db.refresh(target)
    return target


async def delete_target(db: AsyncSession, portfolio_id: int, asset_type: str) -> bool:
    result = await db.execute(
        select(PortfolioClassTarget).where(
            PortfolioClassTarget.portfolio_id == portfolio_id,
            PortfolioClassTarget.asset_type == asset_type,
        )
    )
    target = result.scalar_one_or_none()
    if target is None:
        return False
    await db.delete(target)
    await db.commit()
    return True
