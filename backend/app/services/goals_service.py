"""Service de metas financeiras com projeção automática de data.

Tipos de meta:
  PATRIMONIO     - alvo = valor total do patrimônio desejado
  PROVENTOS      - alvo = renda mensal de proventos desejada (R$/mês)
  RENTABILIDADE  - alvo = rentabilidade acumulada desejada (%)
  LIVRE          - alvo = qualquer valor; current_value informado pelo usuário

Projeção de data:
  meses = (target_value - current_value) / monthly_contribution
  projected_date = agora + meses
  (válido quando monthly_contribution > 0 e meta não concluída)
"""
from __future__ import annotations

from typing import Optional
from datetime import date, datetime, timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.goal import Goal
from app.schemas.goal import GoalCreate, GoalUpdate
from app.services.portfolio_service import get_portfolio_summary
from app.services.canonical_dividend_entitlement import EntitlementReason
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _calc_projection(
    current: float,
    target: float,
    monthly: Optional[float],
) -> tuple[Optional[float], Optional[datetime]]:
    """Retorna (months_to_goal, projected_date) ou (None, None)."""
    if not target or target <= 0:
        return None, None
    if current >= target:
        return 0.0, None  # já concluído
    if not monthly or monthly <= 0:
        return None, None  # sem aporte projetado
    months = (target - current) / monthly
    proj = datetime.now(timezone.utc) + relativedelta(months=+round(months))
    return round(months, 1), proj


def _enrich(goal: Goal, current_value: float | None = None) -> dict:
    resolved_current_value = (
        float(goal.current_value or 0.0)
        if current_value is None
        else float(current_value)
    )
    target_val = (
        float(goal.target_value)
        if goal.target_value is not None
        else 0.0
    )
    progress = 0.0
    if target_val > 0:
        progress = min(resolved_current_value / target_val * 100, 100.0)

    months_to_goal, projected_date = _calc_projection(
        resolved_current_value,
        target_val,
        goal.monthly_contribution,
    )

    return {
        "id": goal.id,
        "portfolio_id": goal.portfolio_id,
        "goal_type": goal.goal_type,
        "name": goal.name,
        "target_value": target_val,
        "current_value": resolved_current_value,
        "base_value": float(goal.base_value or 0.0),
        "monthly_contribution": goal.monthly_contribution,
        "target_date": goal.target_date,
        "description": goal.description,
        "is_active": bool(getattr(goal, "is_active", True)),
        "created_at": goal.created_at,
        "updated_at": getattr(goal, "updated_at", None),
        "progress_pct": round(progress, 2),
        "is_completed": bool(
            target_val > 0 and resolved_current_value >= target_val
        ),
        "months_to_goal": months_to_goal,
        "projected_date": projected_date,
    }


# ---------------------------------------------------------------------------
# queries básicas de KPI para resolver current_value automático
# ---------------------------------------------------------------------------

async def _get_patrimonio_atual(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> float:
    """Use the canonical summary; portfolio_positions is not the ledger."""
    summary = await get_portfolio_summary(db, portfolio_id, user_id)
    return float(summary["total_patrimonio"])


async def _get_proventos_mensais(db: AsyncSession, portfolio_id: int) -> float:
    """Return average monthly net BRL entitlements paid in last 12 months."""
    today = date.today()
    cutoff_12m = today + relativedelta(months=-12)
    entitlements = await load_portfolio_dividend_entitlements(
        db,
        portfolio_id,
    )
    total_12m = sum(
        (
            item.entitlement.net_amount
            for item in entitlements
            if item.entitlement.reason is EntitlementReason.ELIGIBLE
            and item.entitlement.currency == "BRL"
            and item.event.payment_date is not None
            and cutoff_12m <= item.event.payment_date <= today
        ),
        Decimal("0"),
    )
    return round(float(total_12m / Decimal("12")), 2)


async def _get_rentabilidade_atual(
    db: AsyncSession, portfolio_id: int
) -> float:
    """Rentabilidade acumulada do portfólio (snapshot mais recente)."""
    from app.models.portfolio_snapshot import PortfolioSnapshot
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.date.desc())
        .limit(1)
    )
    snap = result.scalar_one_or_none()
    if snap and hasattr(snap, 'total_return_pct'):
        return float(snap.total_return_pct or 0.0)
    return 0.0


async def _resolve_current_value(
    db: AsyncSession,
    portfolio_id: int,
    goal_type: str,
    provided_current: float,
    user_id: int | None = None,
) -> float:
    """Para tipos auto, busca valor real; LIVRE usa valor informado."""
    if goal_type == "PATRIMONIO":
        if user_id is None:
            raise ValueError("user_id is required to resolve portfolio value")
        return await _get_patrimonio_atual(db, portfolio_id, user_id)
    if goal_type == "PROVENTOS":
        return await _get_proventos_mensais(db, portfolio_id)
    if goal_type == "RENTABILIDADE":
        return await _get_rentabilidade_atual(db, portfolio_id)
    return provided_current  # LIVRE


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def list_goals(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[dict]:
    result = await db.execute(
        select(Goal)
        .where(Goal.portfolio_id == portfolio_id)
        .order_by(Goal.created_at.desc())
    )
    payloads = []
    for goal in result.scalars().all():
        current_value = await _resolve_current_value(
            db,
            portfolio_id,
            goal.goal_type,
            float(goal.current_value or 0.0),
            user_id=user_id,
        )
        payloads.append(_enrich(goal, current_value=current_value))
    return payloads


async def get_goal(
    db: AsyncSession,
    goal_id: int,
    portfolio_id: int,
    user_id: int,
) -> Optional[dict]:
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id, Goal.portfolio_id == portfolio_id
        )
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        return None
    current_value = await _resolve_current_value(
        db,
        portfolio_id,
        goal.goal_type,
        float(goal.current_value or 0.0),
        user_id=user_id,
    )
    return _enrich(goal, current_value=current_value)


async def create_goal(
    db: AsyncSession, data: GoalCreate, user_id: int
) -> dict:
    current = await _resolve_current_value(
        db,
        data.portfolio_id,
        data.goal_type,
        data.current_value,
        user_id=user_id,
    )
    goal = Goal(
        portfolio_id=data.portfolio_id,
        goal_type=data.goal_type,
        name=data.name,
        target_value=data.target_value,
        current_value=current,
        base_value=current,
        monthly_contribution=data.monthly_contribution,
        target_date=data.target_date,
        description=data.description,
        is_active=data.is_active,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return _enrich(goal)


async def update_goal(
    db: AsyncSession,
    goal_id: int,
    portfolio_id: int,
    data: GoalUpdate,
    user_id: int,
) -> Optional[dict]:
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id, Goal.portfolio_id == portfolio_id
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "current_value" and goal.goal_type != "LIVRE":
            continue
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal)
    current_value = await _resolve_current_value(
        db,
        portfolio_id,
        goal.goal_type,
        float(goal.current_value or 0.0),
        user_id=user_id,
    )
    return _enrich(goal, current_value=current_value)


async def delete_goal(
    db: AsyncSession, goal_id: int, portfolio_id: int
) -> bool:
    result = await db.execute(
        select(Goal).where(
            Goal.id == goal_id, Goal.portfolio_id == portfolio_id
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        return False
    await db.delete(goal)
    await db.commit()
    return True
