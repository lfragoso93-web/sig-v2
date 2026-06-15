from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.portfolio import Portfolio
from app.models.user import User
from app.integrations.fx_rate import get_usd_brl
from app.services.performance_service import (
    calc_portfolio_performance,
    calc_asset_performance,
    PortfolioPerformance,
    AssetPerformance,
)
from app.services.portfolio_snapshot_service import (
    get_daily_evolution,
    get_monthly_evolution,
    backfill_snapshots,
)

router = APIRouter(prefix="/api/v1/portfolios", tags=["performance"])


# ── Schemas ───────────────────────────────────────────────────────────────────────

class AssetPerfOut(BaseModel):
    ticker: str
    asset_type: str
    currency: str
    quantity: float
    avg_price_brl: float
    current_price_brl: float
    cost_basis: float
    current_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    return_pct: float
    fx_rate_current: Optional[float] = None
    allocation_pct: float = 0.0


class ByTypeOut(BaseModel):
    asset_type: str
    cost: float
    current: float
    pnl: float
    return_pct: float
    allocation_pct: float
    count: int


class SnapshotPoint(BaseModel):
    """Ponto de snapshot diário ou mensal — valor de mercado real."""
    date: str             # YYYY-MM-DD (diário) ou YYYY-MM (mensal via campo 'period')
    market_value: float
    cost_basis: float
    invested_total: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    return_pct: float


class SnapshotPointMonthly(BaseModel):
    """Ponto mensal — usa 'period' (YYYY-MM) para diferenciar do diário."""
    period: str
    market_value: float
    cost_basis: float
    invested_total: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    return_pct: float


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
    history: list[SnapshotPointMonthly]  # historico mensal via snapshots reais


class BackfillOut(BaseModel):
    portfolio_id: int
    snapshots_processed: int
    message: str


# ── Helper: verifica ownership da carteira ──────────────────────────────────────────

async def _assert_portfolio_owner(
    db: AsyncSession, portfolio_id: int, user_id: int
) -> None:
    result = await db.execute(
        select(Portfolio.id).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Carteira não encontrada")


# ── Endpoints existentes ───────────────────────────────────────────────────────────

@router.get("/{portfolio_id}/performance", response_model=PortfolioPerfOut)
async def get_portfolio_performance(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna rentabilidade completa da carteira."""
    perf = await calc_portfolio_performance(db, portfolio_id, current_user.id)

    total_current = perf.total_current or 1.0

    assets_out = [
        AssetPerfOut(
            ticker=a.ticker,
            asset_type=a.asset_type,
            currency=a.currency,
            quantity=a.quantity,
            avg_price_brl=a.avg_price_brl,
            current_price_brl=a.current_price_brl,
            cost_basis=a.cost_basis,
            current_value=a.current_value,
            unrealized_pnl=a.unrealized_pnl,
            realized_pnl=a.realized_pnl,
            total_pnl=a.total_pnl,
            return_pct=a.return_pct,
            fx_rate_current=a.fx_rate_current,
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

    # history agora vem de get_monthly_evolution() — valor de mercado real
    history_out = [
        SnapshotPointMonthly(**h)
        for h in perf.history
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
        history=history_out,
    )


@router.get("/{portfolio_id}/performance/{ticker}", response_model=AssetPerfOut)
async def get_asset_performance(
    portfolio_id: int,
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rentabilidade de um ativo especifico dentro da carteira."""
    from app.models.transaction import Transaction

    result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker.upper(),
        )
        .limit(1)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Ativo nao encontrado nesta carteira")

    fx = await get_usd_brl()
    # prices_brl pré-buscado para este ativo
    from app.services.quotes_service import get_prices
    raw = await get_prices([{"ticker": row.ticker, "asset_type": row.asset_type}], db=db)
    price = raw.get(row.ticker, 0.0)
    from app.services.performance_service import USD_TYPES
    prices_brl = {row.ticker: price * fx if row.asset_type in USD_TYPES else price}

    ap = await calc_asset_performance(
        db, portfolio_id, row.ticker, row.asset_type, fx, prices_brl
    )

    return AssetPerfOut(
        ticker=ap.ticker,
        asset_type=ap.asset_type,
        currency=ap.currency,
        quantity=ap.quantity,
        avg_price_brl=ap.avg_price_brl,
        current_price_brl=ap.current_price_brl,
        cost_basis=ap.cost_basis,
        current_value=ap.current_value,
        unrealized_pnl=ap.unrealized_pnl,
        realized_pnl=ap.realized_pnl,
        total_pnl=ap.total_pnl,
        return_pct=ap.return_pct,
        fx_rate_current=ap.fx_rate_current,
        allocation_pct=0.0,
    )


# ── Endpoints de evolução patrimonial (Sprint 5) ────────────────────────────────

@router.get(
    "/{portfolio_id}/evolution/daily",
    response_model=list[SnapshotPoint],
    summary="Evolução patrimonial diária",
)
async def get_daily_evolution_endpoint(
    portfolio_id: int,
    days: int = Query(default=365, ge=1, le=1825, description="Número de dias para trás (max 5 anos)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna série diária de valor de mercado da carteira.
    Ideal para gráfico de linha de evolução patrimonial.

    Cada ponto inclui: market_value, cost_basis, invested_total,
    unrealized_pnl, realized_pnl, total_pnl, return_pct.

    Requer que o scheduler já tenha gerado os snapshots.
    Use POST /evolution/backfill para popular o histórico inicial.
    """
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    data = await get_daily_evolution(db, portfolio_id, days=days)
    return [SnapshotPoint(**d) for d in data]


@router.get(
    "/{portfolio_id}/evolution/monthly",
    response_model=list[SnapshotPointMonthly],
    summary="Evolução patrimonial mensal",
)
async def get_monthly_evolution_endpoint(
    portfolio_id: int,
    months: int = Query(default=24, ge=1, le=120, description="Número de meses para trás (max 10 anos)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna o valor de mercado no último dia útil de cada mês.
    Ideal para gráfico de barras mensal com rentabilidade acumulada.

    O campo 'period' está no formato YYYY-MM.
    O campo 'return_pct' representa o retorno total acumulado até aquela data.
    """
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    data = await get_monthly_evolution(db, portfolio_id, months=months)
    return [SnapshotPointMonthly(**d) for d in data]


@router.post(
    "/{portfolio_id}/evolution/backfill",
    response_model=BackfillOut,
    summary="Popular histórico de snapshots",
)
async def backfill_evolution(
    portfolio_id: int,
    days_back: Optional[int] = Query(
        default=None,
        ge=1,
        le=1825,
        description="Limitar backfill aos últimos N dias (omitir = desde a 1a transacao)",
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Popula o histórico de snapshots diários da carteira.

    Deve ser chamado:
      - Uma vez após migrar do sistema legado (sem backfill_snapshots).
      - Após importar transações retroativas em lote.

    Otimizações automáticas:
      - Pula fins de semana (sem cotação nova).
      - Pula datas já existentes no banco (idempotente).
      - Commit a cada 30 dias para não travar a sessão.

    Opera em background: a resposta é imediata com contagem estimada.
    Para carteiras novas (pouco histórico) o processamento é síncrono.
    """
    await _assert_portfolio_owner(db, portfolio_id, current_user.id)
    count = await backfill_snapshots(db, portfolio_id, days_back=days_back)
    return BackfillOut(
        portfolio_id=portfolio_id,
        snapshots_processed=count,
        message=f"{count} snapshots gerados/atualizados com sucesso.",
    )
