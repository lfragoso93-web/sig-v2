"""
Servico de auditoria para rastreamento de operações de usuários.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Type, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import joinedload
import json
from app.models.audit_log import AuditLog, AuditAction
from app.models.user import User
from app.schemas.audit_log import (
    AuditLogCreate, AuditLogResponse, AuditStatsResponse, 
    UserAuditStatsResponse, AuditLogCleanupResponse
)

logger = logging.getLogger(__name__)


class AuditLogService:
    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        portfolio_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Cria um novo registro de auditoria.
        Se old_values e new_values forem fornecidos, calcula as mudanças.
        """
        changes = None
        if old_values and new_values:
            changes = AuditLogService._calculate_changes(old_values, new_values)

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            portfolio_id=portfolio_id,
            old_values=old_values,
            new_values=new_values,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )
        db.add(audit_log)
        try:
            await db.flush()
        except Exception as e:
            logger.error(f"Erro ao criar audit log: {str(e)}")
            raise
        return audit_log

    @staticmethod
    def _calculate_changes(old_values: Dict[str, Any], new_values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula as mudanças entre old_values e new_values.
        Retorna apenas os campos que foram alterados.
        """
        changes = {}
        all_keys = set(old_values.keys()) | set(new_values.keys())
        
        for key in all_keys:
            old_val = old_values.get(key)
            new_val = new_values.get(key)
            
            if old_val != new_val:
                changes[key] = {
                    "old": old_val,
                    "new": new_val,
                }
        
        return changes if changes else None

    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        portfolio_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> tuple[list[AuditLog], int]:
        """
        Retorna logs de auditoria com filtros e paginação.
        Retorna (logs, total_count).
        """
        query = select(AuditLog).options(joinedload(AuditLog.user))
        filters = []

        if user_id:
            filters.append(AuditLog.user_id == user_id)
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        if action:
            filters.append(AuditLog.action == action)
        if portfolio_id:
            filters.append(AuditLog.portfolio_id == portfolio_id)
        if status:
            filters.append(AuditLog.status == status)
        if date_from:
            filters.append(AuditLog.created_at >= date_from)
        if date_to:
            filters.append(AuditLog.created_at <= date_to)
        if search:
            filters.append(
                or_(
                    AuditLog.resource_id.cast(str).contains(search),
                    AuditLog.error_message.contains(search)
                )
            )

        if filters:
            query = query.where(and_(*filters))

        # Count total
        count_query = select(func.count()).select_from(AuditLog)
        if filters:
            count_query = count_query.where(and_(*filters))
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()

        # Fetch paginated
        query = query.order_by(desc(AuditLog.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        logs = result.unique().scalars().all()

        return logs, total_count

    @staticmethod
    async def get_user_audit_logs(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Retorna logs de auditoria de um usuário específico."""
        return await AuditLogService.get_audit_logs(
            db,
            page=page,
            page_size=page_size,
            user_id=user_id,
        )

    @staticmethod
    async def get_portfolio_audit_logs(
        db: AsyncSession,
        portfolio_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Retorna logs de auditoria de um portfólio específico."""
        return await AuditLogService.get_audit_logs(
            db,
            page=page,
            page_size=page_size,
            portfolio_id=portfolio_id,
        )

    @staticmethod
    async def get_audit_log_by_id(db: AsyncSession, log_id: int) -> Optional[AuditLog]:
        """Retorna um log de auditoria específico."""
        result = await db.execute(
            select(AuditLog).where(AuditLog.id == log_id).options(joinedload(AuditLog.user))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_audit_stats(db: AsyncSession) -> AuditStatsResponse:
        """Retorna estatísticas gerais de auditoria."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())

        # Total logs
        total_result = await db.execute(select(func.count()).select_from(AuditLog))
        total_logs = total_result.scalar_one()

        # Logs today
        today_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= today_start)
        )
        logs_today = today_result.scalar_one()

        # Logs this week
        week_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.created_at >= week_start)
        )
        logs_this_week = week_result.scalar_one()

        # Failed operations
        failed_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.status != "SUCCESS")
        )
        failed_operations = failed_result.scalar_one()

        # Actions breakdown
        actions_result = await db.execute(
            select(AuditLog.action, func.count().label("count")).group_by(AuditLog.action)
        )
        actions_breakdown = {row[0]: row[1] for row in actions_result.all()}

        # Resource types breakdown
        resources_result = await db.execute(
            select(AuditLog.resource_type, func.count().label("count")).group_by(AuditLog.resource_type)
        )
        resources_breakdown = {row[0]: row[1] for row in resources_result.all()}

        return AuditStatsResponse(
            total_logs=total_logs,
            logs_today=logs_today,
            logs_this_week=logs_this_week,
            actions_breakdown=actions_breakdown,
            resource_types_breakdown=resources_breakdown,
            failed_operations=failed_operations,
        )

    @staticmethod
    async def get_user_audit_stats(db: AsyncSession, user_id: int) -> UserAuditStatsResponse:
        """Retorna estatísticas de auditoria de um usuário."""
        # Total actions
        total_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.user_id == user_id)
        )
        total_actions = total_result.scalar_one()

        # Failed actions
        failed_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(
                and_(AuditLog.user_id == user_id, AuditLog.status != "SUCCESS")
            )
        )
        failed_actions = failed_result.scalar_one()

        # Last action
        last_action_result = await db.execute(
            select(AuditLog.created_at)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
        last_action = last_action_result.scalar_one_or_none()

        # Actions breakdown
        actions_result = await db.execute(
            select(AuditLog.action, func.count().label("count"))
            .where(AuditLog.user_id == user_id)
            .group_by(AuditLog.action)
        )
        actions_breakdown = {row[0]: row[1] for row in actions_result.all()}

        return UserAuditStatsResponse(
            user_id=user_id,
            total_actions=total_actions,
            actions_breakdown=actions_breakdown,
            last_action=last_action,
            failed_actions=failed_actions,
        )

    @staticmethod
    async def cleanup_audit_logs(
        db: AsyncSession,
        days_to_keep: int = 90,
        dry_run: bool = True,
    ) -> AuditLogCleanupResponse:
        """
        Limpa logs de auditoria mais antigos que 'days_to_keep'.
        Se dry_run=True, apenas retorna quantos seria deletados.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Count logs to delete
        count_result = await db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.created_at < cutoff_date)
        )
        count = count_result.scalar_one()

        if not dry_run and count > 0:
            await db.execute(
                select(AuditLog).where(AuditLog.created_at < cutoff_date)
            )
            deleted_result = await db.execute(
                select(func.count()).select_from(AuditLog)
            )
            await db.execute(
                AuditLog.__table__.delete().where(AuditLog.created_at < cutoff_date)
            )
            await db.commit()

        return AuditLogCleanupResponse(
            deleted_count=count,
            freed_space_mb=count * 0.001,
        )
