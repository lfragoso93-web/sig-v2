"""
Router de metas de alocação por classe de ativo.

Endpoints:
  GET  /portfolios/{portfolio_id}/class-targets          -> lista todas as metas
  PUT  /portfolios/{portfolio_id}/class-targets/{type}   -> upsert de uma meta
  DELETE /portfolios/{portfolio_id}/class-targets/{type} -> remove uma meta
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.schemas.position import ClassTargetOut, ClassTargetIn
from app.services.class_target_service import get_targets, upsert_target, delete_target

router = APIRouter(tags=['class-targets'])


async def _get_portfolio(portfolio_id: int, user: User, db: AsyncSession) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user.id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail='Carteira nao encontrada.')
    return p


@router.get('/{portfolio_id}/class-targets', response_model=list[ClassTargetOut])
async def list_class_targets(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    targets = await get_targets(db, portfolio_id)
    return [ClassTargetOut(asset_type=t.asset_type, target_pct=float(t.target_pct)) for t in targets]


@router.put('/{portfolio_id}/class-targets/{asset_type}', response_model=ClassTargetOut)
async def set_class_target(
    portfolio_id: int,
    asset_type: str,
    body: ClassTargetIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    if body.target_pct < 0 or body.target_pct > 100:
        raise HTTPException(status_code=422, detail='target_pct deve estar entre 0 e 100.')
    target = await upsert_target(db, portfolio_id, asset_type.upper(), body.target_pct)
    return ClassTargetOut(asset_type=target.asset_type, target_pct=float(target.target_pct))


@router.delete('/{portfolio_id}/class-targets/{asset_type}', status_code=204)
async def remove_class_target(
    portfolio_id: int,
    asset_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_portfolio(portfolio_id, current_user, db)
    removed = await delete_target(db, portfolio_id, asset_type.upper())
    if not removed:
        raise HTTPException(status_code=404, detail='Meta nao encontrada.')
