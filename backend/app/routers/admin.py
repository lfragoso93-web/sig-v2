from fastapi import APIRouter, BackgroundTasks, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate, UserListResponse, UserResponse,
    UserAdminUpdate, AdminResetPasswordRequest,
)
from app.schemas.auth import MessageResponse
from app.schemas.config import SystemConfigResponse, SystemConfigUpdate, SystemConfigBulkUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.user_service import (
    create_user, list_users, get_user_by_id,
    admin_update_user, delete_user, count_users
)
from app.services.config_service import get_all_configs, update_config, bulk_update_configs
import math
import logging
import traceback

logger = logging.getLogger(__name__)

router = APIRouter()


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a SuperAdmins",
        )
    return current_user


# ── Gestão de Usuários ────────────────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=PaginatedResponse[UserListResponse])
async def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Lista todos os usuários com paginação e busca."""
    users, total = await list_users(db, page, page_size, search)
    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    data: UserCreate,
    role: UserRole = Query(UserRole.user),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Cria usuário (SuperAdmin pode definir role)."""
    return await create_user(db, data, role=role)


@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def admin_update_user_endpoint(
    user_id: int,
    data: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Edita qualquer campo do usuário incluindo role e status."""
    if user_id == current_user.id and data.role and data.role != UserRole.superadmin:
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio SuperAdmin")
    return await admin_update_user(db, user_id, data)


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Remove usuário permanentemente (cascade deleta carteiras e dados)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta")
    await delete_user(db, user_id)
    return MessageResponse(message="Usuário excluído com sucesso")


@router.put("/users/{user_id}/toggle-active", response_model=UserResponse)
async def admin_toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Ativa ou desativa um usuário."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.is_active = not user.is_active
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
async def admin_reset_password(
    user_id: int,
    data: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """
    Redefine a senha de qualquer usuário com um novo hash bcrypt v5.
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.hashed_password = hash_password(data.new_password)
    await db.commit()
    await db.refresh(user)
    return MessageResponse(
        message=f"Senha do usuário {user.email} redefinida com sucesso"
    )


# ── Estatísticas do sistema ───────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Estatísticas gerais do sistema para o painel admin."""
    total_users = await count_users(db)
    return {
        "total_users": total_users,
        "version": "2.0.0",
        "system": "SGI — Sistema de Gestão de Investimentos",
    }


# ── Configurações do sistema ──────────────────────────────────────────────────────────────────────────────

@router.get("/config", response_model=list[SystemConfigResponse])
async def admin_list_configs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Lista todas as configurações do sistema (incluindo privadas)."""
    return await get_all_configs(db, public_only=False)


@router.put("/config/{key}", response_model=SystemConfigResponse)
async def admin_update_config(
    key: str,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Atualiza uma configuração do sistema."""
    return await update_config(db, key, data.value)


@router.put("/config", response_model=list[SystemConfigResponse])
async def admin_bulk_update_config(
    data: SystemConfigBulkUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Atualiza múltiplas configurações de uma vez."""
    return await bulk_update_configs(db, data.configs)


# ── Seed de Ativos (BRAPI) ──────────────────────────────────────────────────────────────────────────────

async def _run_asset_seed_bg() -> None:
    """Wrapper para rodar o seed em BackgroundTask com sua propria sessao."""
    logger.info("[seed_bg] ========== INICIANDO SEED DE ATIVOS ==========")
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.asset_seed_service import run_asset_seed
        async with AsyncSessionLocal() as db:
            result = await run_asset_seed(db)
            logger.info(
                "[seed_bg] ========== SEED CONCLUIDO: created=%s updated=%s skipped=%s errors=%s ==========",
                result.created, result.updated, result.skipped, result.errors,
            )
    except Exception as e:
        logger.error(
            "[seed_bg] ========== SEED FALHOU: %s\n%s ==========",
            e,
            traceback.format_exc(),
        )


@router.post(
    "/assets/seed",
    status_code=status.HTTP_202_ACCEPTED,
)
async def admin_seed_assets(
    background_tasks: BackgroundTasks,
    _: User = Depends(require_superadmin),
):
    """
    Dispara o seed de ativos da B3 em background via BRAPI /v2/tickers.
    Restrito a SuperAdmins.
    """
    logger.info("[seed_bg] requisicao recebida — adicionando task ao background")
    background_tasks.add_task(_run_asset_seed_bg)
    return {
        "message": "Seed de ativos iniciado em background. Acompanhe pelo log do servidor.",
        "status": "accepted",
    }


# ── Backfill de Preços Históricos ────────────────────────────────────────────────────────────────────

@router.get("/prices/backfill/status")
async def admin_backfill_status(
    _: User = Depends(require_superadmin),
):
    """
    Retorna o status atual do backfill de preços históricos.

    Inclui: se está rodando, total de registros, cobertura por ativo,
    data do registro mais antigo e mais recente.
    """
    from app.services.price_history_backfill_service import get_backfill_status
    return await get_backfill_status()


async def _run_price_backfill_bg(force: bool = False) -> None:
    """Wrapper para rodar o backfill de precos em BackgroundTask."""
    logger.info("[backfill_bg] iniciando backfill de precos (force=%s)", force)
    try:
        from app.services.price_history_backfill_service import run_initial_backfill
        await run_initial_backfill(force=force)
    except Exception as e:
        logger.error(
            "[backfill_bg] backfill de precos falhou: %s\n%s",
            e, traceback.format_exc()
        )


@router.post(
    "/prices/backfill",
    status_code=status.HTTP_202_ACCEPTED,
)
async def admin_trigger_price_backfill(
    background_tasks: BackgroundTasks,
    force: bool = Query(
        False,
        description="Se true, reprocessa mesmo os ativos que já têm histórico"
    ),
    _: User = Depends(require_superadmin),
):
    """
    Dispara o backfill de preços históricos (10 anos) em background.

    Por padrao (force=False) só processa ativos sem histórico.
    Com force=True reprocessa todos os ativos.

    Use após reset do banco ou quando quiser forcar uma atualização completa.
    Restrito a SuperAdmins.
    """
    background_tasks.add_task(_run_price_backfill_bg, force)
    return {
        "message": f"Backfill de preços iniciado em background (force={force}). Acompanhe pelo log.",
        "status": "accepted",
        "force": force,
    }


# ── Backfill de Snapshots de Patrimônio ────────────────────────────────────────────────────────────

async def _run_snapshot_backfill_bg(portfolio_id: int | None, force: bool) -> None:
    """
    Roda o backfill de snapshots em background com sessão própria.

    - portfolio_id=None: processa TODOS os portfolios de TODOS os usuários.
    - force=True: apaga snapshots existentes antes de recalcular (recalculo completo).
    """
    logger.info(
        "[snapshot_backfill_bg] iniciando backfill portfolio_id=%s force=%s",
        portfolio_id or 'ALL', force,
    )
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.portfolio import Portfolio
        from app.services.portfolio_snapshot_service import (
            backfill_snapshots,
            invalidate_snapshots_from,
        )
        from sqlalchemy import select
        from datetime import date

        async with AsyncSessionLocal() as db:
            # Resolve lista de portfolio_ids a processar
            if portfolio_id is not None:
                portfolio_ids = [portfolio_id]
            else:
                result = await db.execute(select(Portfolio.id))
                portfolio_ids = [row.id for row in result.all()]

            logger.info(
                "[snapshot_backfill_bg] processando %d portfolio(s)",
                len(portfolio_ids),
            )

            total_snapshots = 0
            errors = 0

            for pid in portfolio_ids:
                try:
                    if force:
                        # Apaga todos os snapshots do portfolio para recalculo completo
                        deleted = await invalidate_snapshots_from(
                            db, pid, date.min, commit=True
                        )
                        logger.info(
                            "[snapshot_backfill_bg] portfolio=%s: %d snapshots deletados (force)",
                            pid, deleted,
                        )

                    count = await backfill_snapshots(db, pid)
                    total_snapshots += count
                    logger.info(
                        "[snapshot_backfill_bg] portfolio=%s: %d snapshots gerados",
                        pid, count,
                    )
                except Exception as e:
                    errors += 1
                    logger.error(
                        "[snapshot_backfill_bg] portfolio=%s falhou: %s\n%s",
                        pid, e, traceback.format_exc(),
                    )

            logger.info(
                "[snapshot_backfill_bg] CONCLUIDO: %d snapshots gerados, %d erros",
                total_snapshots, errors,
            )
    except Exception as e:
        logger.error(
            "[snapshot_backfill_bg] FALHA GERAL: %s\n%s",
            e, traceback.format_exc(),
        )


@router.post(
    "/snapshots/backfill",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Backfill de snapshots patrimoniais (todos os portfolios)",
)
async def admin_snapshot_backfill_all(
    background_tasks: BackgroundTasks,
    force: bool = Query(
        False,
        description=(
            "Se true, APAGA todos os snapshots existentes e recalcula do zero. "
            "Use após correção de bugs de cálculo (ex.: return_pct ou _ret_between)."
        ),
    ),
    _: User = Depends(require_superadmin),
):
    """
    Dispara o backfill de snapshots para TODOS os portfolios em background.

    - **force=false** (padrão): apenas gera snapshots faltantes (dias sem registro).
    - **force=true**: apaga todos os snapshots de cada portfolio e recalcula
      do zero — necessário após correções de bugs de cálculo como a correção
      de `return_pct` e `_ret_between` aplicada em 2026-06-26.

    Restrito a SuperAdmins. Acompanhe o progresso pelo log do servidor.
    """
    background_tasks.add_task(_run_snapshot_backfill_bg, None, force)
    return {
        "message": (
            f"Backfill de snapshots iniciado em background para TODOS os portfolios "
            f"(force={force}). Acompanhe pelo log do servidor."
        ),
        "status": "accepted",
        "scope": "all_portfolios",
        "force": force,
    }


@router.post(
    "/snapshots/backfill/{portfolio_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Backfill de snapshots patrimoniais (portfolio específico)",
)
async def admin_snapshot_backfill_one(
    portfolio_id: int,
    background_tasks: BackgroundTasks,
    force: bool = Query(
        False,
        description="Se true, apaga snapshots existentes do portfolio e recalcula do zero.",
    ),
    _: User = Depends(require_superadmin),
):
    """
    Dispara o backfill de snapshots para um portfolio específico em background.

    Útil para recalcular apenas um portfolio sem afetar os demais.
    Restrito a SuperAdmins.
    """
    background_tasks.add_task(_run_snapshot_backfill_bg, portfolio_id, force)
    return {
        "message": (
            f"Backfill de snapshots iniciado em background para portfolio {portfolio_id} "
            f"(force={force}). Acompanhe pelo log do servidor."
        ),
        "status": "accepted",
        "scope": f"portfolio_{portfolio_id}",
        "force": force,
    }


# ── Sync de Dividendos de FIIs ────────────────────────────────────────────────────────────────────

@router.get(
    "/fii-dividends/sync/status",
    summary="Status do último job de sync de dividendos FII",
)
async def admin_fii_dividends_sync_status(
    _: User = Depends(require_superadmin),
):
    """
    Retorna o status do último job de sincronização de dividendos de FIIs.

    Inclui: status (idle/running/success/error), lock info, cursor de data,
    métricas da última execução (tickers processados, upserted, erros) e
    timestamp de início/fim.

    Restrito a SuperAdmins.
    """
    from app.services.dividends_sync_service import get_sync_status
    return await get_sync_status()


async def _run_fii_dividends_sync_bg(force_bootstrap: bool) -> None:
    """Wrapper para rodar o sync de dividendos FII em BackgroundTask com sessão própria."""
    logger.info(
        "[fii_dividends_sync_bg] ========== INICIANDO SYNC FII DIVIDENDS (force_bootstrap=%s) ==========",
        force_bootstrap,
    )
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.dividends_sync_service import run_fii_dividends_sync
        async with AsyncSessionLocal() as db:
            result = await run_fii_dividends_sync(db, force_bootstrap=force_bootstrap)
        logger.info(
            "[fii_dividends_sync_bg] ========== SYNC CONCLUIDO: "
            "tickers=%s upserted=%s created=%s updated=%s errors=%s ==========",
            result.get("tickers_processed", 0),
            result.get("upserted", 0),
            result.get("created", 0),
            result.get("updated", 0),
            result.get("errors", 0),
        )
    except Exception as e:
        logger.error(
            "[fii_dividends_sync_bg] ========== SYNC FALHOU: %s\n%s ==========",
            e,
            traceback.format_exc(),
        )


@router.post(
    "/fii-dividends/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual do sync de dividendos FII",
)
async def admin_trigger_fii_dividends_sync(
    background_tasks: BackgroundTasks,
    force_bootstrap: bool = Query(
        False,
        description=(
            "Se true, ignora o cursor incremental e reprocessa os últimos 5 anos completos. "
            "Use após reset do banco ou para corrigir dados históricos."
        ),
    ),
    _: User = Depends(require_superadmin),
):
    """
    Dispara manualmente o sync de dividendos de FIIs em background.

    - **force_bootstrap=false** (padrão): modo incremental — busca a partir do
      cursor salvo (com 30 dias de overlap para absorver correções retroativas).
    - **force_bootstrap=true**: reprocessa os últimos 5 anos completos —
      útil após reset de banco ou para forçar recarga histórica.

    O job automático equivalente roda todo sábado às 6h BRT.
    Restrito a SuperAdmins.
    """
    background_tasks.add_task(_run_fii_dividends_sync_bg, force_bootstrap)
    return {
        "message": (
            f"Sync de dividendos FII iniciado em background "
            f"(force_bootstrap={force_bootstrap}). Acompanhe pelo log do servidor."
        ),
        "status": "accepted",
        "force_bootstrap": force_bootstrap,
    }
