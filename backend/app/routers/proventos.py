from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.schemas.dividend import (
    ProventosSummary, ProventoDistribution,
    ProventosEvolucao, ProventosHistoricoMes, ProventoItem
)
from app import services
from fastapi import HTTPException

router = APIRouter(prefix="/api/v1/portfolios/{portfolio_id}/proventos", tags=["proventos"])


def _get_portfolio(portfolio_id: int, db: Session, user: User) -> Portfolio:
    p = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user.id).first()
    if not p:
        raise HTTPException(404, "Carteira não encontrada")
    return p


@router.get("/summary", response_model=ProventosSummary)
def summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, db, current_user)
    from app.services.proventos_service import get_summary
    return get_summary(db, portfolio_id)


@router.get("/distribution", response_model=list[ProventoDistribution])
def distribution(
    portfolio_id: int,
    months: int = Query(12, ge=1, le=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, db, current_user)
    from app.services.proventos_service import get_distribution
    return get_distribution(db, portfolio_id, months)


@router.get("/evolucao", response_model=list[ProventosEvolucao])
def evolucao(
    portfolio_id: int,
    tipo: str = Query("mensal", regex="^(mensal|anual)$"),
    period: str = Query("12m", regex="^(12m|24m|ytd|all)$"),
    asset_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, db, current_user)
    from app.services.proventos_service import get_evolucao
    return get_evolucao(db, portfolio_id, tipo, period, asset_type)


@router.get("/historico-mensal", response_model=list[ProventosHistoricoMes])
def historico_mensal(
    portfolio_id: int,
    status: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, db, current_user)
    from app.services.proventos_service import get_historico_mensal
    return get_historico_mensal(db, portfolio_id, status, asset_type)


@router.get("", response_model=list[ProventoItem])
def list_proventos(
    portfolio_id: int,
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, db, current_user)
    from app.services.proventos_service import get_list
    return get_list(db, portfolio_id, year, status, asset_type)
