from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional
from fastapi import HTTPException, status

from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.position import Position
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.quotes_service import get_prices


# ── Labels e normalização de tipos ──────────────────────────────────────────────────
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


def normalize_type(raw: str) -> str:
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


# ---------------------------------------------------------------------------
# CRUD assíncrono (usado pelos routers)
# ---------------------------------------------------------------------------

async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.id)
    )
    return result.scalars().all()


async def get_portfolio(db: AsyncSession, portfolio_id: int, user_id: int) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Carteira não encontrada',
        )
    return portfolio


async def create_portfolio(
    db: AsyncSession, user_id: int, data: PortfolioCreate
) -> Portfolio:
    portfolio = Portfolio(user_id=user_id, **data.model_dump())
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


async def update_portfolio(
    db: AsyncSession, portfolio_id: int, user_id: int, data: PortfolioUpdate
) -> Portfolio:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(portfolio, field, value)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


async def delete_portfolio(
    db: AsyncSession, portfolio_id: int, user_id: int
) -> None:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    await db.delete(portfolio)
    await db.flush()


# ---------------------------------------------------------------------------
# Lógica financeira — Preço Médio Ponderado
# ---------------------------------------------------------------------------

async def calc_raw_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """
    Calcula posições brutas (sem cotação) a partir do histórico de transações.
    Usa Preço Médio Ponderado: avg = total_cost / qty.
    A cada venda: total_cost -= avg * qty_vendida.
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date)
    )
    txs = result.scalars().all()

    pos: dict[tuple, dict] = {}
    for tx in txs:
        raw_type = tx.asset_type or 'OUTROS'
        norm     = normalize_type(raw_type)
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


def enrich_with_prices(items: list[dict], prices: dict[str, float]) -> list[dict]:
    """
    Enriquece posições brutas com cotação atual.
    current_price = None quando cotação indisponível — NUNCA usa avg como fallback.
    """
    enriched = []
    for item in items:
        ticker         = item['ticker']
        avg_price      = item['avg_price']
        quantity       = item['quantity']
        total_invested = item['total_invested']

        raw_price     = prices.get(ticker)  # None se ausente
        current_price = float(raw_price) if raw_price is not None else None

        effective_price = current_price if current_price is not None else avg_price
        current_value   = round(quantity * effective_price, 2)
        result_abs      = round(current_value - total_invested, 2) if current_price is not None else 0.0
        result_pct      = round(
            (result_abs / total_invested * 100)
            if total_invested > 0 and current_price is not None
            else 0.0,
            4,
        )

        enriched.append({
            **item,
            'current_price': round(current_price, 6) if current_price is not None else None,
            'current_value': current_value,
            'result_abs':    result_abs,
            'result_pct':    result_pct,
        })
    return enriched


async def calc_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """Orquestra: calcula posições brutas → busca cotações → enriquece."""
    raw    = await calc_raw_positions(db, portfolio_id)
    prices = await get_prices(raw)
    return enrich_with_prices(raw, prices)


async def sum_dividends(
    db: AsyncSession,
    portfolio_id: int,
    cutoff: Optional[date] = None,
) -> float:
    """Soma proventos recebidos. Se cutoff fornecido, filtra apenas os posteriores."""
    try:
        if cutoff:
            rows = await db.execute(
                text(
                    'SELECT total_value, value_per_unit, amount, quantity '
                    'FROM dividends '
                    'WHERE portfolio_id = :pid AND payment_date >= :cutoff'
                ),
                {'pid': portfolio_id, 'cutoff': cutoff},
            )
        else:
            rows = await db.execute(
                text(
                    'SELECT total_value, value_per_unit, amount, quantity '
                    'FROM dividends '
                    'WHERE portfolio_id = :pid'
                ),
                {'pid': portfolio_id},
            )
        total = 0.0
        for row in rows.fetchall():
            tv, vpu, amt, qty = row
            if tv is not None:
                total += float(tv)
            else:
                unit   = vpu or amt or 0.0
                q      = qty or 1.0
                total += float(unit) * float(q)
        return round(total, 2)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Recálculo de posições materializadas (usado internamente após transações)
# ---------------------------------------------------------------------------

async def recalc_positions(portfolio_id: int, db: AsyncSession) -> None:
    """
    Recalcula preço médio ponderado e quantidade atual
    para cada ativo da carteira, a partir do histórico de transações.

    Algoritmo:
      - Compra: pm = (pm_ant * qt_ant + qt_nova * preco + fees) / (qt_ant + qt_nova)
      - Venda:  pm não muda, apenas reduz quantidade
    """
    txs_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = txs_result.scalars().all()

    state: dict[str, dict] = defaultdict(
        lambda: {'qty': 0.0, 'avg_price': 0.0, 'asset_type': ''}
    )

    for tx in txs:
        s = state[tx.ticker]
        s['asset_type'] = tx.asset_type

        if tx.operation == OperationType.buy:
            total_cost = s['qty'] * s['avg_price'] + tx.quantity * tx.price + tx.fees
            new_qty    = s['qty'] + tx.quantity
            s['avg_price'] = total_cost / new_qty if new_qty > 0 else 0
            s['qty']       = new_qty
        else:
            s['qty'] = max(s['qty'] - tx.quantity, 0)

    active = {k: v for k, v in state.items() if v['qty'] > 1e-9}

    existing_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    existing = {p.ticker: p for p in existing_result.scalars().all()}

    for ticker in list(existing.keys()):
        if ticker not in active:
            await db.delete(existing[ticker])

    for ticker, data in active.items():
        if ticker in existing:
            pos           = existing[ticker]
            pos.quantity  = data['qty']
            pos.avg_price = data['avg_price']
        else:
            pos = Position(
                portfolio_id=portfolio_id,
                ticker=ticker,
                asset_type=data['asset_type'],
                quantity=data['qty'],
                avg_price=data['avg_price'],
            )
            db.add(pos)

    await db.flush()
