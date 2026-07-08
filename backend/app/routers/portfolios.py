from fastapi import APIRouter, Depends, status, BackgroundTasks, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioResponse,
    ClassTargetWithCurrent,
    ClassTargetUpsert,
    CSVImportResponse,
)
from app.services.portfolio_service import (
    create_portfolio,
    list_portfolios,
    get_portfolio,
    update_portfolio,
    get_portfolio_summary,
    get_portfolio_positions,
    get_asset_distribution,
)
from app.services.portfolio_delete_service import delete_portfolio_safely
from app.services.portfolio_snapshot_service import get_monthly_evolution, backfill_snapshots
from app.services.portfolio_class_evolution_service import get_monthly_evolution_by_class
from app.services.class_target_service import (
    get_targets_with_current,
    upsert_target,
    delete_target,
    VALID_ASSET_CLASSES,
)
from app.services import csv_import_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["portfolios"])


async def _backfill_bg(portfolio_id: int) -> None:
    """Roda backfill em background sem bloquear a resposta."""
    try:
        async with AsyncSessionLocal() as db:
            count = await backfill_snapshots(db, portfolio_id)
        logger.info("[snapshot_bg] portfolio=%s backfill concluido: %d snapshots", portfolio_id, count)
    except Exception as exc:
        logger.error("[snapshot_bg] portfolio=%s erro: %s", portfolio_id, exc)


@router.get("/", response_model=list[PortfolioResponse])
async def list_user_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_portfolios(db, current_user.id)


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_user_portfolio(
    data: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_portfolio(db, current_user.id, data)


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_user_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portfolio(db, portfolio_id, current_user.id)


@router.patch("/{portfolio_id}", response_model=PortfolioResponse)
async def update_user_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await update_portfolio(db, portfolio_id, current_user.id, data)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await delete_portfolio_safely(db, portfolio_id, current_user.id)
    return None


@router.get("/{portfolio_id}/summary")
async def portfolio_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portfolio_summary(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/positions")
async def portfolio_positions(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portfolio_positions(db, portfolio_id, current_user.id)


@router.get("/{portfolio_id}/asset-distribution")
async def asset_distribution(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_asset_distribution(db, portfolio_id, current_user.id)


# ---------------------------------------------------------------------------
# Sprint 5E — targets-with-current (alvo vs atual, BDR incluido)
# ---------------------------------------------------------------------------

@router.get(
    "/{portfolio_id}/targets-with-current",
    response_model=list[ClassTargetWithCurrent],
)
async def get_portfolio_targets_with_current(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_distribution = await get_asset_distribution(db, portfolio_id, current_user.id)
    return await get_targets_with_current(db, portfolio_id, current_distribution)


@router.put(
    "/{portfolio_id}/class-targets/{asset_type}",
    response_model=ClassTargetWithCurrent,
)
async def upsert_class_target(
    portfolio_id: int,
    asset_type: str,
    data: ClassTargetUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # asset_type da URL manda; body pode vir igual por conveniencia
    asset_type_norm = asset_type.upper()
    if asset_type_norm not in VALID_ASSET_CLASSES:
        raise HTTPException(status_code=400, detail="Classe de ativo invalida")
    return await upsert_target(db, portfolio_id, current_user.id, asset_type_norm, data.target_pct)


@router.delete(
    "/{portfolio_id}/class-targets/{asset_type}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_class_target(
    portfolio_id: int,
    asset_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset_type_norm = asset_type.upper()
    await delete_target(db, current_user.id, asset_type_norm)
    return None


@router.get("/{portfolio_id}/patrimonio-history")
async def patrimonio_history(
    portfolio_id: int,
    months: int = 12,
    asset_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await get_portfolio(db, portfolio_id, current_user.id)
    if asset_type:
        return await get_monthly_evolution_by_class(
            db,
            portfolio_id,
            months=months,
            asset_type=asset_type,
        )
    return await get_monthly_evolution(db, portfolio_id, months=months)


@router.post("/{portfolio_id}/snapshots/backfill", status_code=status.HTTP_202_ACCEPTED)
async def backfill_portfolio_snapshots(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await get_portfolio(db, portfolio_id, current_user.id)
    background_tasks.add_task(_backfill_bg, portfolio_id)
    return {"detail": "Backfill de snapshots iniciado"}


@router.post("/{portfolio_id}/import-csv", response_model=CSVImportResponse)
async def import_portfolio_csv(
    portfolio_id: int,
    file: UploadFile = File(...),
    dry_run: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await get_portfolio(db, portfolio_id, current_user.id)
    return await csv_import_service.import_transactions_csv(
        db=db,
        portfolio_id=portfolio_id,
        user_id=current_user.id,
        file=file,
        dry_run=dry_run,
    )
