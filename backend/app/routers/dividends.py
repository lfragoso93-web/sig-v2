from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
from datetime import date, timedelta
from collections import defaultdict

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.dividend import Dividend
from app.schemas.dividend import DividendCreate, DividendOut, DividendSummary, MonthPoint

router = APIRouter(prefix="/portfolios/{portfolio_id}/dividends", tags=["dividends"])


def _get_portfolio(portfolio_id: int, user: User, db: Session) -> Portfolio:
    p = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user.id,
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Carteira n\u00e3o encontrada.")
    return p


@router.get("", response_model=List[DividendOut])
def list_dividends(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, current_user, db)
    return (
        db.query(Dividend)
        .filter(Dividend.portfolio_id == portfolio_id)
        .order_by(Dividend.payment_date.desc())
        .all()
    )


@router.post("", response_model=DividendOut, status_code=status.HTTP_201_CREATED)
def create_dividend(
    portfolio_id: int,
    payload: DividendCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, current_user, db)

    div = Dividend(
        portfolio_id=portfolio_id,
        ticker=payload.ticker.upper(),
        asset_type=payload.asset_type,
        type=payload.type,
        amount=payload.amount,
        quantity=payload.quantity,
        payment_date=payload.payment_date,
        ex_date=payload.ex_date,
    )
    db.add(div)
    db.commit()
    db.refresh(div)
    return div


@router.get("/summary", response_model=DividendSummary)
def dividend_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_portfolio(portfolio_id, current_user, db)

    dividends = (
        db.query(Dividend)
        .filter(Dividend.portfolio_id == portfolio_id)
        .all()
    )

    today = date.today()
    total_received = sum(d.amount * d.quantity for d in dividends if d.payment_date <= today)

    # Agrupar por m\u00eas (YYYY-MM)
    monthly_map: dict[str, float] = defaultdict(float)
    for d in dividends:
        if d.payment_date <= today:
            key = d.payment_date.strftime("%Y-%m")
            monthly_map[key] += d.amount * d.quantity

    monthly = [
        MonthPoint(month=k, amount=v)
        for k, v in sorted(monthly_map.items())
    ]

    # Proje\u00e7\u00e3o: m\u00e9dia dos \u00faltimos 6 meses * 12
    cutoff = today - timedelta(days=180)
    recent = [d for d in dividends if cutoff <= d.payment_date <= today]
    recent_total = sum(d.amount * d.quantity for d in recent)
    avg_monthly = recent_total / 6 if recent else 0
    total_projected = avg_monthly * 12

    return DividendSummary(
        total_received=total_received,
        total_projected=total_projected,
        monthly=monthly,
    )
