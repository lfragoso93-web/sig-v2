from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.dividend import DividendCreate, DividendResponse
from app.services.dividend_service import (
    create_dividend,
    list_dividends,
    delete_dividend,
)
from app.services.dividend_backfill_service import run_backfill

router = APIRouter(tags=["dividends"])


@router.get("/{portfolio_id}/dividends", response_model=list[DividendResponse])
async def get_dividends(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await list_dividends(db, portfolio_id, current_user.id)


@router.post("/{portfolio_id}/dividends", response_model=DividendResponse, status_code=status.HTTP_201_CREATED)
async def add_dividend(
    portfolio_id: int,
    data: DividendCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_dividend(db, portfolio_id, current_user.id, data)


@router.delete("/{portfolio_id}/dividends/{dividend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dividend(
    portfolio_id: int,
    dividend_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await delete_dividend(db, dividend_id, portfolio_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Provento nao encontrado")
    return None


@router.post("/{portfolio_id}/dividends/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_dividends(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dispara o backfill de proventos historicos para todos os ativos
    da carteira. Execucao em background — retorna imediatamente.
    """
    # Verifica ownership
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Carteira nao encontrada.")

    # Busca tickers distintos da carteira
    rows = await db.execute(
        select(Transaction.ticker, Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    pairs = rows.all()  # list of (ticker, asset_type)

    if not pairs:
        return {"message": "Nenhum ativo encontrado na carteira.", "tickers": []}

    from app.models.asset import AssetType
    from app.core.database import AsyncSessionLocal

    async def _run_backfill_all():
        async with AsyncSessionLocal() as bg_db:
            for ticker, at_str in pairs:
                try:
                    at = AssetType(at_str) if isinstance(at_str, str) else at_str
                    await run_backfill(bg_db, ticker, at)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f"[sync] backfill falhou para {ticker}: {e}"
                    )

    background_tasks.add_task(_run_backfill_all)

    tickers = [t for t, _ in pairs]
    return {
        "message": f"Sync de proventos iniciado para {len(tickers)} ativo(s).",
        "tickers": tickers,
    }
