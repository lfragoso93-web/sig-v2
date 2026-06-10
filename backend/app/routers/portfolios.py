from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate, PortfolioResponse
from app.schemas.auth import MessageResponse
from app.services.portfolio_service import (
    list_portfolios, create_portfolio, update_portfolio, delete_portfolio
)
from app.services.quotes_service import get_prices

router = APIRouter()

# ── Labels amigáveis ───────────────────────────────────────────────────────────────────
ASSET_LABELS: dict[str, str] = {
    'ACAO':              'Ações',
    'ACAO_NACIONAL':     'Ações',
    'FII':               'FIIs',
    'ETF_NACIONAL':      'ETFs Nacionais',
    'ETF_INT':           'ETFs Internacionais',
    'ETF_INTERNACIONAL': 'ETFs Internacionais',
    'STOCK':             'Stocks',
    'STOCKS':            'Stocks',
    'TESOURO':           'Tesouro Direto',
    'TESOURO_DIRETO':    'Tesouro Direto',
    'RENDA_FIXA':        'Renda Fixa',
    'CRIPTO':            'Criptomoedas',
    'CRIPTOMOEDA':       'Criptomoedas',
}


def _normalize_type(raw: str) -> str:
    mapping = {
        'ACAO':        'ACAO_NACIONAL',
        'ACOES':       'ACAO_NACIONAL',
        'ETF_INT':     'ETF_INTERNACIONAL',
        'ETF':         'ETF_NACIONAL',
        'TESOURO':     'TESOURO_DIRETO',
        'CRIPTO':      'CRIPTO',
        'CRIPTOMOEDA': 'CRIPTO',
        'STOCKS':      'STOCK',
    }
    upper = (raw or '').upper().strip()
    return mapping.get(upper, upper)


# ── Schemas ─────────────────────────────────────────────────────────────────────────
class PositionItem(BaseModel):
    ticker:         str
    asset_type:     str
    asset_label:    str
    quantity:       float
    avg_price:      float
    total_invested: float
    current_price:  float
    current_value:  float
    result_abs:     float
    result_pct:     float


class SummaryResponse(BaseModel):
    total_invested:           float
    total_current:            float
    result_abs:               float
    result_pct:               float
    positions_count:          int
    total_patrimonio:         float
    total_investido:          float
    lucro_total:              float
    variacao_valor:           float
    variacao_percentual:      float
    rentabilidade_total:      float
    dividendos_recebidos_12m: float
    total_proventos:          float


# ── Helper: posições brutas (sem cotacao) ────────────────────────────────────────
async def _calc_raw_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date)
    )
    txs = result.scalars().all()

    pos: dict[tuple, dict] = {}
    for tx in txs:
        raw_type = tx.asset_type or 'OUTROS'
        norm     = _normalize_type(raw_type)
        key      = (tx.ticker, norm)
        if key not in pos:
            pos[key] = {'qty': 0.0, 'total_cost': 0.0, 'ticker': tx.ticker, 'asset_type': norm}
        p = pos[key]
        if tx.operation == OperationType.buy:
            p['total_cost'] += tx.quantity * tx.price + (tx.fees or 0)
            p['qty']        += tx.quantity
        else:
            if p['qty'] > 0:
                avg = p['total_cost'] / p['qty']
                p['total_cost'] -= avg * tx.quantity
            p['qty'] -= tx.quantity

    items = []
    for p in pos.values():
        if p['qty'] > 1e-9:
            avg       = p['total_cost'] / p['qty'] if p['qty'] > 0 else 0.0
            total_inv = round(p['total_cost'], 2)
            items.append({
                'ticker':         p['ticker'],
                'asset_type':     p['asset_type'],
                'asset_label':    ASSET_LABELS.get(p['asset_type'], p['asset_type']),
                'quantity':       round(p['qty'], 8),
                'avg_price':      round(avg, 6),
                'total_invested': total_inv,
            })
    return items


def _enrich_with_prices(items: list[dict], prices: dict[str, float]) -> list[dict]:
    """Aplica cotacoes reais (ou fallback avg_price) e calcula result."""
    enriched = []
    for item in items:
        ticker        = item['ticker']
        avg_price     = item['avg_price']
        quantity      = item['quantity']
        total_invested= item['total_invested']

        current_price = prices.get(ticker) or avg_price   # fallback
        current_value = round(quantity * current_price, 2)
        result_abs    = round(current_value - total_invested, 2)
        result_pct    = round((result_abs / total_invested * 100) if total_invested > 0 else 0.0, 4)

        enriched.append({
            **item,
            'current_price': round(current_price, 6),
            'current_value': current_value,
            'result_abs':    result_abs,
            'result_pct':    result_pct,
        })
    return enriched


async def _calc_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """Posicoes completas com cotacao real."""
    raw    = await _calc_raw_positions(db, portfolio_id)
    prices = await get_prices(raw)       # busca BRAPI + yfinance
    return _enrich_with_prices(raw, prices)


# ── Rotas CRUD ──────────────────────────────────────────────────────────────────────

@router.get('/', response_model=list[PortfolioResponse])
async def list_my_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_portfolios(db, current_user.id)


@router.post('/', response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_my_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_portfolio(db, current_user.id, data)


@router.get('/{portfolio_id}', response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.portfolio_service import get_portfolio as _get
    return await _get(db, portfolio_id, current_user.id)


@router.put('/{portfolio_id}', response_model=PortfolioResponse)
async def update_my_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_portfolio(db, portfolio_id, current_user.id, data)


@router.delete('/{portfolio_id}', response_model=MessageResponse)
async def delete_my_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_portfolio(db, portfolio_id, current_user.id)
    return MessageResponse(message='Carteira excluída com sucesso')


# ── Summary ──────────────────────────────────────────────────────────────────────

@router.get('/{portfolio_id}/summary', response_model=SummaryResponse)
async def portfolio_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p_res = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    if not p_res.scalar_one_or_none():
        raise HTTPException(404, 'Carteira não encontrada')

    items          = await _calc_positions(db, portfolio_id)
    total_invested = sum(i['total_invested'] for i in items)
    total_current  = sum(i['current_value']  for i in items)
    result_abs     = round(total_current - total_invested, 2)
    result_pct     = round((result_abs / total_invested * 100) if total_invested > 0 else 0.0, 4)

    # Proventos
    from datetime import date, timedelta
    from app.models.provento import Provento
    cutoff   = date.today() - timedelta(days=365)
    prov_res = await db.execute(
        select(Provento).where(
            Provento.portfolio_id == portfolio_id,
            Provento.date >= cutoff,
        )
    )
    proventos_12m = sum(
        (p.value or 0) * (p.quantity or 1) for p in prov_res.scalars().all()
    )
    prov_all = await db.execute(
        select(Provento).where(Provento.portfolio_id == portfolio_id)
    )
    total_proventos = sum(
        (p.value or 0) * (p.quantity or 1) for p in prov_all.scalars().all()
    )

    return SummaryResponse(
        total_invested           = round(total_invested, 2),
        total_current            = round(total_current,  2),
        result_abs               = result_abs,
        result_pct               = result_pct,
        positions_count          = len(items),
        total_patrimonio         = round(total_current,  2),
        total_investido          = round(total_invested, 2),
        lucro_total              = result_abs,
        variacao_valor           = result_abs,
        variacao_percentual      = result_pct,
        rentabilidade_total      = result_pct,
        dividendos_recebidos_12m = round(proventos_12m,   2),
        total_proventos          = round(total_proventos, 2),
    )


# ── Positions ───────────────────────────────────────────────────────────────────

@router.get('/{portfolio_id}/positions', response_model=list[PositionItem])
async def portfolio_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    p_res = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    if not p_res.scalar_one_or_none():
        raise HTTPException(404, 'Carteira não encontrada')
    return await _calc_positions(db, portfolio_id)
