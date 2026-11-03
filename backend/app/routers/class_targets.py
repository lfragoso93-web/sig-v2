"""
Router de metas de alocação por classe de ativo.

Endpoints:
  GET  /portfolios/{portfolio_id}/class-targets          -> lista todas as metas
  PUT  /portfolios/{portfolio_id}/class-targets/{type}   -> upsert de uma meta
  DELETE /portfolios/{portfolio_id}/class-targets/{type} -> remove uma meta
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.position import ClassTargetOut, ClassTargetIn, ClassTargetBulkIn
from app.services.portfolio_objectives_access_service import (
    READ_PORTFOLIO_CLASS_TARGETS,
    WRITE_PORTFOLIO_CLASS_TARGETS,
    delete_authorized_class_target,
    get_authorized_class_targets,
    set_authorized_class_target,
    set_authorized_class_targets,
)
import math

router = APIRouter(tags=['class-targets'])


def _access_context(
    portfolio_id: int, user: User, permission: str
) -> PortfolioAccessContext:
    if portfolio_id <= 0:
        raise HTTPException(status_code=404, detail='Carteira nao encontrada ou sem permissao')
    return PortfolioAccessContext.for_user(
        user_id=user.id,
        portfolio_id=portfolio_id,
        permissions=frozenset({permission}),
    )


@router.get('/{portfolio_id}/class-targets', response_model=list[ClassTargetOut])
async def list_class_targets(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    access = _access_context(portfolio_id, current_user, READ_PORTFOLIO_CLASS_TARGETS)
    targets = await get_authorized_class_targets(db, access)
    return [ClassTargetOut(asset_type=t.asset_type, target_pct=float(t.target_pct)) for t in targets]


@router.put('/{portfolio_id}/class-targets', response_model=list[ClassTargetOut])
async def set_class_targets_bulk(
    portfolio_id: int,
    body: ClassTargetBulkIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    access = _access_context(portfolio_id, current_user, WRITE_PORTFOLIO_CLASS_TARGETS)
    items: list[tuple[str, float]] = []
    for item in body.targets:
        if not math.isfinite(item.target_pct) or item.target_pct < 0 or item.target_pct > 100:
            raise HTTPException(
                status_code=422,
                detail=f'O percentual de {item.asset_type} deve estar entre 0 e 100.',
            )
        items.append((item.asset_type.upper(), item.target_pct))
    targets = await set_authorized_class_targets(db, access, items)
    return [ClassTargetOut(asset_type=t.asset_type, target_pct=float(t.target_pct)) for t in targets]


@router.put('/{portfolio_id}/class-targets/{asset_type}', response_model=ClassTargetOut)
async def set_class_target(
    portfolio_id: int,
    asset_type: str,
    body: ClassTargetIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    access = _access_context(portfolio_id, current_user, WRITE_PORTFOLIO_CLASS_TARGETS)
    if not math.isfinite(body.target_pct) or body.target_pct < 0 or body.target_pct > 100:
        raise HTTPException(status_code=422, detail='O percentual da meta deve estar entre 0% e 100%.')
    target = await set_authorized_class_target(
        db, access, asset_type.upper(), body.target_pct
    )
    return ClassTargetOut(asset_type=target.asset_type, target_pct=float(target.target_pct))


@router.delete('/{portfolio_id}/class-targets/{asset_type}', status_code=204)
async def remove_class_target(
    portfolio_id: int,
    asset_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    access = _access_context(portfolio_id, current_user, WRITE_PORTFOLIO_CLASS_TARGETS)
    removed = await delete_authorized_class_target(db, access, asset_type.upper())
    if not removed:
        raise HTTPException(status_code=404, detail='Meta nao encontrada.')
