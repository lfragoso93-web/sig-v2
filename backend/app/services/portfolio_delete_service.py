import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete
from app.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "portfolio"

_PORTFOLIO_DEPENDENT_TABLES = (
    "dividends",
    "corporate_events",
    "fixed_income_investments",
    "goals",
    "irpf_reports",
    "portfolio_class_targets",
    "portfolio_positions",
    "portfolio_class_snapshots",
    "portfolio_snapshots",
    "transactions",
)


def _cache_key(portfolio_id: int, suffix: str) -> str:
    return f"{_CACHE_PREFIX}:{portfolio_id}:{suffix}"


async def _invalidate_portfolio_cache(portfolio_id: int) -> None:
    await cache_delete(_cache_key(portfolio_id, "summary"))
    await cache_delete(_cache_key(portfolio_id, "positions"))


async def _table_has_column(db: AsyncSession, table_name: str, column_name: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = :table_name
                  AND column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return bool(result.scalar())


async def _delete_from_table_by_portfolio(db: AsyncSession, table_name: str, portfolio_id: int) -> None:
    if not await _table_has_column(db, table_name, "portfolio_id"):
        logger.info(
            "[portfolio_delete] ignorando %s: tabela ausente ou sem portfolio_id",
            table_name,
        )
        return
    await db.execute(
        text(f"DELETE FROM {table_name} WHERE portfolio_id = :portfolio_id"),
        {"portfolio_id": portfolio_id},
    )


async def delete_portfolio_safely(db: AsyncSession, portfolio_id: int, user_id: int) -> None:
    result = await db.execute(
        text(
            """
            SELECT id, name, description
            FROM portfolios
            WHERE id = :portfolio_id AND user_id = :user_id
            """
        ),
        {"portfolio_id": portfolio_id, "user_id": user_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada")

    old_values: dict[str, Any] = {
        "name": row.get("name"),
        "description": row.get("description"),
    }

    try:
        await AuditLogService.log_action(
            db=db,
            user_id=user_id,
            action="DELETE",
            resource_type="Portfolio",
            resource_id=portfolio_id,
            portfolio_id=portfolio_id,
            old_values=old_values,
        )
        await db.flush()
    except Exception as exc:
        logger.warning("[portfolio_delete] falha ao registrar auditoria: %s", exc)
        await db.rollback()

    if await _table_has_column(db, "audit_logs", "portfolio_id"):
        await db.execute(
            text("UPDATE audit_logs SET portfolio_id = NULL WHERE portfolio_id = :portfolio_id"),
            {"portfolio_id": portfolio_id},
        )

    for table_name in _PORTFOLIO_DEPENDENT_TABLES:
        await _delete_from_table_by_portfolio(db, table_name, portfolio_id)

    result = await db.execute(
        text(
            """
            DELETE FROM portfolios
            WHERE id = :portfolio_id AND user_id = :user_id
            """
        ),
        {"portfolio_id": portfolio_id, "user_id": user_id},
    )

    if result.rowcount == 0:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Carteira nao encontrada")

    await db.commit()
    await _invalidate_portfolio_cache(portfolio_id)
