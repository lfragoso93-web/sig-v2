from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.performance_service import (
    calc_portfolio_performance,
    calc_asset_performance,
    PortfolioPerformance,
    AssetPerformance,
)
from app.models.asset import Asset
from app.integrations.fx_rate import get_usd_brl
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/portfolios", tags=["performance"])


# ─── Schemas de resposta ──────────────────────────────────────────────────────

class AssetPerfOut(BaseModel):
    ticker: str
    asset_type: str
    currency: str
    quantity: float
    avg_price: float
    avg_price_brl: float
    current_price: float
    current_price_brl: float
    cost_basis: float
    current_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    return_pct: float
    fx_rate_avg: Optional[float]
    fx_rate_current: Optional[float]
    fx_variation_pct: Optional[float]
    allocation_pct: float = 0.0  # preenchido no endpoint


class ByTypeOut(BaseModel):
    asset_type: str
    cost: float
    current: float
    pnl: float
    return_pct: float
    allocation_pct: float
    count: int


class HistoryPoint(BaseModel):
    period: str
    inflow: float
    outflow: float
    net_invested: float


class PortfolioPerfOut(BaseModel):
    portfolio_id: int
    portfolio_name: str
    total_cost: float
    total_current: float
    total_unrealized: float
    total_realized: float
    total_pnl: float
    return_pct: float
    assets: list[AssetPerfOut]
    by_type: list[ByTypeOut]
    history: list[HistoryPoint]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{portfolio_id}/performance", response_model=PortfolioPerfOut)
async def get_portfolio_performance(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna rentabilidade completa da carteira."""
    perf = await calc_portfolio_performance(db, portfolio_id, current_user.id)

    total_current = perf.total_current or 1.0  # evitar div/zero

    assets_out = [
        AssetPerfOut(
            **{k: getattr(a, k) for k in AssetPerfOut.model_fields if hasattr(a, k)},
            allocation_pct=(a.current_value / total_current * 100) if total_current else 0.0,
        )
        for a in perf.assets
    ]

    by_type_out = [
        ByTypeOut(
            asset_type=t,
            cost=v["cost"],
            current=v["current"],
            pnl=v["pnl"],
            return_pct=v["return_pct"],
            allocation_pct=v["allocation_pct"],
            count=v["count"],
        )
        for t, v in perf.by_type.items()
    ]

    return PortfolioPerfOut(
        portfolio_id=perf.portfolio_id,
        portfolio_name=perf.portfolio_name,
        total_cost=perf.total_cost,
        total_current=perf.total_current,
        total_unrealized=perf.total_unrealized,
        total_realized=perf.total_realized,
        total_pnl=perf.total_pnl,
        return_pct=perf.return_pct,
        assets=assets_out,
        by_type=by_type_out,
        history=perf.history,
    )


@router.get("/{portfolio_id}/performance/{ticker}", response_model=AssetPerfOut)
async def get_asset_performance(
    portfolio_id: int,
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rentabilidade de um ativo especifico dentro da carteira."""
    asset = db.query(Asset).filter(Asset.ticker == ticker.upper()).first()
    if not asset:
        from fastapi import HTTPException
        raise HTTPException(404, "Ativo nao encontrado")

    fx = await get_usd_brl()
    ap = await calc_asset_performance(db, portfolio_id, asset, fx)

    return AssetPerfOut(
        **{k: getattr(ap, k) for k in AssetPerfOut.model_fields if hasattr(ap, k)},
        allocation_pct=0.0,
    )
