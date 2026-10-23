from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.core.log_safety import sanitize_log_value
from app.models.user import User, UserRole
from app.models.admin_backup_operation import (
    AdminBackupOperation,
    BackupOperationStatus,
    BackupOperationType,
)
from app.schemas.admin import (
    AdminRestoreRequest,
    AdminBackupOperationsResponse,
    AdminSmtpStatusResponse,
    AdminSmtpTestRequest,
    AdminSmtpTestResponse,
)
from app.schemas.user import (
    UserCreate, UserListResponse, UserResponse,
    UserAdminUpdate, UserRoleUpdate, AdminResetPasswordRequest,
)
from app.schemas.auth import MessageResponse
from app.schemas.config import SystemConfigResponse, SystemConfigUpdate, SystemConfigBulkUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.user_service import (
    create_user, list_users, get_user_by_id,
    admin_update_user, delete_user, count_users, count_active_superadmins
)
from app.services.config_service import get_all_configs, update_config, bulk_update_configs
from app.services import backup_service
from app.schemas.audit_log import (
    PaginatedAuditLogs, AuditLogDetailResponse, AuditStatsResponse,
    UserAuditStatsResponse, AuditLogCleanupResponse
)
from app.services.audit_log_service import AuditLogService
from datetime import datetime
from uuid import uuid4
import logging
import traceback
import os
import math

logger = logging.getLogger(__name__)

router = APIRouter()


def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a SuperAdmins",
        )
    return current_user


async def _record_database_backup_action(
    db: AsyncSession,
    current_user: User,
    request: Request,
    *,
    action: str,
    audit_status: str,
    new_values: dict | None = None,
    error_message: str | None = None,
):
    user_agent = request.headers.get("user-agent")
    audit_log = await AuditLogService.log_action(
        db=db,
        user_id=current_user.id,
        action=action,
        resource_type="DatabaseBackup",
        new_values=new_values,
        ip_address=request.client.host if request.client else None,
        user_agent=sanitize_log_value(user_agent) if user_agent else None,
        status=audit_status,
        error_message=error_message,
    )
    await db.commit()
    return audit_log


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
    user = await create_user(db, data, role=role)
    try:
        from app.services.email_service import send_welcome_email
        await send_welcome_email(user.email, user.name or user.email)
    except Exception as exc:
        logger.warning("Falha ao enviar e-mail de boas-vindas ao criar usuário pelo admin: %s", exc)
    return user


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


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def admin_update_user_role_endpoint(
    user_id: int,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Altera apenas o perfil do usuario."""
    if user_id == current_user.id and data.role != UserRole.superadmin:
        raise HTTPException(status_code=400, detail="Voce nao pode remover seu proprio SuperAdmin")
    return await admin_update_user(db, user_id, UserAdminUpdate(role=data.role))


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """Remove usuário permanentemente (cascade deleta carteiras e dados)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta")
    target_user = await get_user_by_id(db, user_id)
    email = target_user.email if target_user else None
    name = (target_user.name or target_user.email) if target_user else None
    await delete_user(db, user_id)
    if email:
        try:
            from app.services.email_service import send_account_deleted_email
            await send_account_deleted_email(email, name or email)
        except Exception as exc:
            logger.warning("Falha ao enviar e-mail de exclusão de conta pelo admin: %s", exc)
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
    if user.role == UserRole.superadmin and user.is_active and await count_active_superadmins(db) <= 1:
        raise HTTPException(status_code=400, detail="Nao e possivel remover o ultimo SuperAdmin ativo")
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    try:
        from app.services.email_service import send_account_status_email
        await send_account_status_email(user.email, user.name or user.email, user.is_active)
    except Exception as exc:
        logger.warning("Falha ao enviar e-mail de status da conta: %s", exc)
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
    try:
        from app.services.email_service import send_password_changed_email
        await send_password_changed_email(
            user.email,
            user.name or user.email,
            origin="redefinição pelo administrador",
        )
    except Exception as exc:
        logger.warning("Falha ao enviar e-mail de redefinição de senha pelo admin: %s", exc)
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
        from app.services.portfolio_snapshot_canonical_twr_service import (
            backfill_canonical_snapshots_with_returns,
        )
        from app.services.portfolio_snapshot_service import invalidate_snapshots_from
        from sqlalchemy import select
        from datetime import date

        async with AsyncSessionLocal() as db:
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
                        deleted = await invalidate_snapshots_from(
                            db, pid, date.min, commit=True
                        )
                        logger.info(
                            "[snapshot_backfill_bg] portfolio=%s: %d snapshots deletados (force)",
                            pid, deleted,
                        )

                    count = await backfill_canonical_snapshots_with_returns(db, pid)
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


# ── Backup & Restore de Banco de Dados ────────────────────────────────────────────────

async def _create_backup_operation(
    db: AsyncSession,
    user_id: int,
    operation_type: BackupOperationType,
    backup_filename: str | None = None,
) -> AdminBackupOperation:
    operation = AdminBackupOperation(
        id=uuid4(),
        operation_type=operation_type,
        status=BackupOperationStatus.QUEUED,
        requested_by_user_id=user_id,
        backup_filename=backup_filename,
    )
    db.add(operation)
    return operation


@router.post(
    "/database/backup",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Criar backup do banco de dados",
)
async def admin_create_database_backup(
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """
    Cria um backup completo do banco de dados em background usando pg_dump.

    O arquivo de backup é comprimido com gzip e armazenado localmente.
    Restrito a SuperAdmins.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL não configurado"
        )

    logger.info("[backup] Requisição de backup recebida — adicionando task ao background")
    operation = await _create_backup_operation(
        db, current_user.id, BackupOperationType.BACKUP
    )
    await _record_database_backup_action(
        db,
        current_user,
        request,
        action="BACKUP",
        audit_status="SUCCESS",
        new_values={"request_status": "accepted"},
    )
    background_tasks.add_task(
        backup_service.run_database_backup_operation, operation.id, db_url
    )

    return {
        "message": "Backup do banco iniciado em background. Acompanhe pelo log do servidor.",
        "status": "accepted",
        "operation_id": str(operation.id),
    }


@router.get(
    "/database/operations",
    response_model=AdminBackupOperationsResponse,
    summary="Consultar operações de backup e restore",
)
async def admin_list_database_operations(
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            select(AdminBackupOperation)
            .order_by(desc(AdminBackupOperation.created_at))
            .limit(limit)
        )
    except SQLAlchemyError as exc:
        logger.warning("[backup_ops] Operation status table is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Status das operações indisponível",
        ) from exc
    operations = list(result.scalars().all())
    return {"operations": operations, "count": len(operations)}


@router.get(
    "/database/backups",
    summary="Listar backups disponíveis",
)
async def admin_list_database_backups(
    _: User = Depends(require_superadmin),
):
    """
    Lista todos os backups do banco de dados disponíveis.

    Retorna informações de tamanho, data de criação e filename para restauração.
    Restrito a SuperAdmins.
    """
    result = await backup_service.list_backups()
    return result


@router.get(
    "/database/backups/{backup_filename}",
    response_class=FileResponse,
    summary="Baixar um backup",
)
async def admin_download_database_backup(
    backup_filename: str,
    _: User = Depends(require_superadmin),
):
    """Baixa um backup existente; restrito a SuperAdmins."""
    try:
        backup_path = backup_service.get_backup_download_path(backup_filename)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de backup inválido",
        ) from exc

    if backup_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup não encontrado",
        )

    return FileResponse(
        path=backup_path,
        media_type="application/gzip",
        filename=backup_filename,
    )


@router.post(
    "/database/restore",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Restaurar banco de dados a partir de um backup",
)
async def admin_restore_database(
    data: AdminRestoreRequest,
    request: Request,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """
    Restaura o banco de dados a partir de um backup em background.

    **CUIDADO**: Esta operação sobrescreve TODOS os dados do banco com os dados do backup.

    Args:
        data.backup_filename: Nome exato do arquivo listado em GET /database/backups.

    Restrito a SuperAdmins.
    """
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credenciais inválidas",
        )

    backup_filename = data.backup_filename
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL não configurado"
        )

    backups = await backup_service.list_backups()
    valid_files = [b["filename"] for b in backups["backups"]]

    if backup_filename not in valid_files:
        raise HTTPException(
            status_code=404,
            detail=f"Backup não encontrado. Backups disponíveis: {valid_files}"
        )

    logger.warning(
        "[restore] Requisição de restore recebida para: %s — adicionando task ao background",
        sanitize_log_value(backup_filename)
    )
    operation = await _create_backup_operation(
        db,
        current_user.id,
        BackupOperationType.RESTORE,
        sanitize_log_value(backup_filename),
    )
    await _record_database_backup_action(
        db,
        current_user,
        request,
        action="RESTORE",
        audit_status="SUCCESS",
        new_values={
            "backup_filename": sanitize_log_value(backup_filename),
            "request_status": "accepted",
        },
    )
    background_tasks.add_task(
        backup_service.run_database_restore_operation,
        operation.id,
        db_url,
        backup_filename,
    )

    return {
        "message": f"Restauração iniciada em background a partir de {backup_filename}. Acompanhe pelo log do servidor.",
        "status": "accepted",
        "operation_id": str(operation.id),
        "backup_filename": backup_filename,
        "warning": "Esta operação sobrescreve TODOS os dados do banco",
    }


@router.delete(
    "/database/backups/{backup_filename}",
    summary="Deletar um backup",
)
async def admin_delete_database_backup(
    backup_filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superadmin),
):
    """
    Deleta um arquivo de backup.

    Args:
        backup_filename: Nome do arquivo a deletar

    Restrito a SuperAdmins.
    """
    audit_log = await _record_database_backup_action(
        db,
        current_user,
        request,
        action="DELETE",
        audit_status="REQUESTED",
        new_values={
            "backup_filename": sanitize_log_value(backup_filename),
            "operation_status": "requested",
        },
    )
    result = await backup_service.delete_backup(backup_filename)

    if not result["success"]:
        audit_log.status = "FAILURE"
        audit_log.error_message = "Backup deletion failed"
        await db.commit()
        raise HTTPException(
            status_code=404,
            detail="Não foi possível remover o backup",
        )

    audit_log.status = "SUCCESS"
    audit_log.new_values = {
        "backup_filename": sanitize_log_value(backup_filename),
        "operation_status": "completed",
    }
    await db.commit()

    return {
        "message": f"Backup {backup_filename} deletado com sucesso",
        "backup_id": result["backup_id"],
    }


# ── Logs de Auditoria ────────────────────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=PaginatedAuditLogs)
async def admin_list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user_id: int = Query(None),
    resource_type: str = Query(None),
    action: str = Query(None),
    portfolio_id: int = Query(None),
    status: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """
    Lista logs de auditoria com filtros e paginação.

    Filtros:
    - user_id: ID do usuário
    - resource_type: Tipo de recurso (Portfolio, Transaction, etc)
    - action: Tipo de ação (CREATE, UPDATE, DELETE, etc)
    - portfolio_id: ID da carteira
    - status: Status (SUCCESS, FAILED, PARTIAL)
    - date_from: Data inicial (ISO format)
    - date_to: Data final (ISO format)
    - search: Busca por resource_id ou erro

    Restrito a SuperAdmins.
    """
    date_from_dt = None
    date_to_dt = None

    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="date_from inválido. Use ISO format")

    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="date_to inválido. Use ISO format")

    logs, total = await AuditLogService.get_audit_logs(
        db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        portfolio_id=portfolio_id,
        status=status,
        date_from=date_from_dt,
        date_to=date_to_dt,
        search=search,
    )

    return {
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "portfolio_id": log.portfolio_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.get("/audit-logs/{log_id}", response_model=AuditLogDetailResponse)
async def admin_get_audit_log_detail(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """
    Retorna detalhes completos de um log de auditoria.
    Inclui valores antigos, novos e mudanças em JSON.

    Restrito a SuperAdmins.
    """
    log = await AuditLogService.get_audit_log_by_id(db, log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Log não encontrado")

    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "portfolio_id": log.portfolio_id,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "status": log.status,
        "error_message": log.error_message,
        "old_values": log.old_values,
        "new_values": log.new_values,
        "changes": log.changes,
        "created_at": log.created_at,
    }


@router.get("/audit-logs/user/{user_id}", response_model=PaginatedAuditLogs)
async def admin_get_user_audit_logs(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """
    Retorna logs de auditoria de um usuário específico.

    Restrito a SuperAdmins.
    """
    logs, total = await AuditLogService.get_user_audit_logs(
        db,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )

    return {
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "portfolio_id": log.portfolio_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.get("/audit-logs/stats", response_model=AuditStatsResponse)
async def admin_get_audit_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """
    Retorna estatísticas gerais de auditoria.

    Inclui: total de logs, logs de hoje, desta semana, breakdown de ações,
    tipos de recursos, e operações que falharam.

    Restrito a SuperAdmins.
    """
    return await AuditLogService.get_audit_stats(db)


@router.get("/audit-logs/user/{user_id}/stats", response_model=UserAuditStatsResponse)
async def admin_get_user_audit_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """
    Retorna estatísticas de auditoria de um usuário.

    Inclui: total de ações, breakdown de ações, última ação, ações falhadas.

    Restrito a SuperAdmins.
    """
    return await AuditLogService.get_user_audit_stats(db, user_id)


@router.delete("/audit-logs/cleanup", response_model=AuditLogCleanupResponse)
async def admin_cleanup_audit_logs(
    days_to_keep: int = Query(90, ge=30, le=365, description="Dias de logs a manter"),
    dry_run: bool = Query(True, description="Se True, apenas simula a limpeza"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """
    Limpa logs de auditoria mais antigos que 'days_to_keep'.

    Se dry_run=True (padrão), apenas retorna quantos seriam deletados sem realmente deletar.
    Se dry_run=False, realmente deleta os logs antigos.

    Restrito a SuperAdmins.
    """
    return await AuditLogService.cleanup_audit_logs(db, days_to_keep, dry_run)


# -----------------------------------------------------------------------------
# Cobertura de mercado por ativo (Issue #130 - Bloco 2)
# -----------------------------------------------------------------------------

@router.get("/coverage", response_model=list[dict])
async def list_asset_coverage(
    limit: int = Query(100, ge=1, le=500),
    status: str | None = Query(None),
    _: User = Depends(require_superadmin),
):
    """Diagnóstico protegido de cobertura de endpoints de mercado por ativo."""
    from app.services.asset_coverage_service import asset_coverage_service
    reports = await asset_coverage_service.list_all_coverages(limit=limit)
    if status:
        reports = [r for r in reports if r.status.upper() == status.upper()]
    return [r.to_dict() for r in reports]


@router.post("/coverage/clear", response_model=dict)
async def clear_asset_coverage(
    ticker: str | None = Query(None),
    _: User = Depends(require_superadmin),
):
    """Limpa cache de cobertura de um ticker ou de todos os ativos."""
    from app.services.asset_coverage_service import asset_coverage_service
    cleared = await asset_coverage_service.clear_coverage(ticker=ticker)
    return {"status": "ok", "cleared_count": cleared}


# -----------------------------------------------------------------------------
# Diagnóstico e Teste de SMTP (Brevo / E-mails Transacionais)
# -----------------------------------------------------------------------------

@router.get("/smtp/status", response_model=AdminSmtpStatusResponse)
async def admin_get_smtp_status(
    _: User = Depends(require_superadmin),
):
    """Retorna o status atual de configuração do servidor SMTP (sem expor segredos)."""
    from app.services.email_service import get_smtp_status
    return get_smtp_status()


@router.post("/smtp/test", response_model=AdminSmtpTestResponse)
async def admin_test_smtp(
    data: AdminSmtpTestRequest,
    _: User = Depends(require_superadmin),
):
    """Testa a conexão, autenticação e disparo de e-mail via SMTP."""
    from app.services.email_service import send_smtp_test_email
    return await send_smtp_test_email(str(data.to_email))


@router.post("/smtp/notify-dividends", response_model=dict)
async def admin_trigger_dividend_notifications(
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Dispara a verificação e envio de avisos de proventos creditados na data atual."""
    from app.services.dividend_notification_service import notify_daily_dividend_payments
    return await notify_daily_dividend_payments(db, force=force)

