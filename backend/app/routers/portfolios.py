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
    delete_portfolio,
    get_portfolio_summary,
    get_portfolio_positions,
    get_asset_distribution,
)
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
    await delete_portfolio(db, portfolio_id, current_user.id)
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
    summary="Distribuicao alvo vs atual por classe (Sprint 5E)",
)
async def targets_with_current(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna lista combinada: alocacao atual da carteira vs. meta configurada.
    BDR incluido explicitamente (Issue #79).
    """
    await get_portfolio(db, portfolio_id, current_user.id)
    distribution = await get_asset_distribution(db, portfolio_id, current_user.id)
    # get_asset_distribution pode retornar dict com chave 'distribution' ou lista direta
    if isinstance(distribution, dict):
        dist_list = distribution.get("distribution", distribution.get("data", []))
    else:
        dist_list = distribution
    return await get_targets_with_current(db, portfolio_id, dist_list)


@router.put(
    "/{portfolio_id}/targets",
    summary="Upsert de meta de alocacao por classe (Sprint 5E)",
)
async def upsert_class_target(
    portfolio_id: int,
    body: ClassTargetUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria ou atualiza a meta de alocacao para um asset_type. BDR suportado."""
    await get_portfolio(db, portfolio_id, current_user.id)
    at = body.asset_type.upper()
    if at not in VALID_ASSET_CLASSES:
        raise HTTPException(
            status_code=422,
            detail=f"asset_type invalido. Valores aceitos: {sorted(VALID_ASSET_CLASSES)}",
        )
    target = await upsert_target(db, portfolio_id, at, body.target_pct)
    return {"asset_type": target.asset_type, "target_pct": float(target.target_pct)}


@router.delete(
    "/{portfolio_id}/targets/{asset_type}",
    status_code=204,
    summary="Remove meta de alocacao por classe (Sprint 5E)",
)
async def delete_class_target(
    portfolio_id: int,
    asset_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a meta de alocacao de um asset_type especifico."""
    await get_portfolio(db, portfolio_id, current_user.id)
    removed = await delete_target(db, portfolio_id, asset_type.upper())
    if not removed:
        raise HTTPException(status_code=404, detail="Meta nao encontrada.")


@router.get("/{portfolio_id}/patrimonio-history")
async def patrimonio_history(
    portfolio_id: int,
    months: int = 12,
    asset_type: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evolucao patrimonial mensal.
    Sem asset_type: usa snapshots diarios (patrimonio total real).
    Com asset_type: calcula mes a mes somando qty*preco para a classe filtrada.

    FIX Bug3: se snapshots estiverem vazios, dispara backfill automatico em background
    e retorna calculo on-the-fly via class_evolution (sem asset_type usa todos os tickers).
    """
    await get_portfolio(db, portfolio_id, current_user.id)

    if asset_type:
        return await get_monthly_evolution_by_class(
            db, portfolio_id, months=months, asset_type=asset_type
        )

    # Modo "Todas as classes": usa snapshots
    data = await get_monthly_evolution(db, portfolio_id, months=months)

    # FIX: se nao ha snapshots, dispara backfill em bg e faz calculo on-the-fly com todas as classes
    if not data:
        logger.info(
            "[patrimonio_history] sem snapshots para portfolio=%s — disparando backfill bg",
            portfolio_id,
        )
        background_tasks.add_task(_backfill_bg, portfolio_id)

        # Calcula on-the-fly agregando todas as classes
        from app.models.transaction import Transaction
        from app.models.asset import Asset
        from sqlalchemy import select as sa_select
        import asyncio

        classes_result = await db.execute(
            sa_select(Asset.asset_type)
            .join(Transaction, Transaction.ticker == Asset.ticker)
            .where(Transaction.portfolio_id == portfolio_id)
            .distinct()
        )
        classes = [row.asset_type.value for row in classes_result.all()]

        if not classes:
            # fallback via asset_type na transacao
            tx_classes = await db.execute(
                sa_select(Transaction.asset_type)
                .where(Transaction.portfolio_id == portfolio_id)
                .distinct()
            )
            classes = [
                (row.asset_type.value if hasattr(row.asset_type, 'value') else str(row.asset_type))
                for row in tx_classes.all()
                if row.asset_type
            ]

        tasks = [
            get_monthly_evolution_by_class(db, portfolio_id, months=months, asset_type=c)
            for c in classes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Agregar por data
        from collections import defaultdict
        aggregated: dict[str, dict] = defaultdict(lambda: {"value": 0.0, "invested": 0.0})
        for res in results:
            if isinstance(res, Exception):
                continue
            for point in res:
                aggregated[point["date"]]["value"] += point.get("value", 0)
                aggregated[point["date"]]["invested"] += point.get("invested", 0)

        data = [
            {"date": d, "value": round(v["value"], 2), "invested": round(v["invested"], 2)}
            for d, v in sorted(aggregated.items())
        ]

    return data


@router.post("/{portfolio_id}/import-csv", response_model=CSVImportResponse, tags=["csv-import"])
async def import_csv(
    portfolio_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Importa transacoes de um arquivo CSV.

    Validacao:
    - Verifica headers obrigatorios
    - Valida tipos de dados
    - Valida datas
    - Valida asset_types e operations

    Retorna:
    - success: bool
    - imported_count: numero de transacoes importadas
    - skipped_count: numero de linhas puladas
    - error_count: numero de erros
    - rows: lista de validacoes por linha
    - global_errors: erros globais do CSV
    """
    await get_portfolio(db, portfolio_id, current_user.id)

    try:
        content = await file.read()
        content_str = content.decode('utf-8')
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Error reading file: {str(e)}"
        )

    result = await csv_import_service.import_csv_transactions(
        content_str,
        portfolio_id,
        current_user.id,
        db
    )

    return result
