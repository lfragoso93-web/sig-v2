from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional
from fastapi import HTTPException, status

from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.position import Position
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.quotes_service import get_prices
from app.integrations.brapi import fetch_quotes_with_meta


# ---------------------------------------------------------------------------
# Labels e normalizacao de tipos
# ---------------------------------------------------------------------------

ASSET_LABELS: dict[str, str] = {
    'ACAO':              'Acoes',
    'ACAO_NACIONAL':     'Acoes',
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
# CRUD assincrono
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
            detail='Carteira nao encontrada',
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
# Logica financeira — Preco Medio Ponderado
#
# Regras confirmadas (Sprint 4):
#   - PM so e atualizado em COMPRAS: PM = (qty_atual*PM_atual + qty*preco + fees) / (qty_atual + qty)
#   - VENDA: qty diminui, total_cost diminui proporcionalmente (total_cost -= PM * qty_vendida)
#     O PM resultante e matematicamente identico ao anterior.
#   - fees de VENDA nao entram no PM — afetam apenas lucro realizado.
#   - Posicao zerada: qty <= 1e-9 — some da carteira.
#   - Sem cotacao: current_price=None, current_value=None, result_abs=None, result_pct=None.
#     NUNCA usar PM como fallback de cotacao.
# ---------------------------------------------------------------------------

async def calc_raw_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """
    Calcula posicoes brutas (sem cotacao) a partir do historico de transacoes.
    Retorna apenas posicoes com quantidade > 0.
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()

    # estado: (ticker, asset_type_normalizado) -> {qty, total_cost}
    pos: dict[tuple, dict] = {}

    for tx in txs:
        norm = normalize_type(tx.asset_type or 'OUTROS')
        key  = (tx.ticker, norm)
        if key not in pos:
            pos[key] = {
                'ticker':     tx.ticker,
                'asset_type': norm,
                'qty':        0.0,
                'total_cost': 0.0,
            }
        p = pos[key]

        qty_tx = float(tx.quantity)
        price  = float(tx.price)
        fees   = float(tx.fees or 0.0)

        if tx.operation == OperationType.buy:
            # PM = (custo_atual + custo_nova_compra_com_taxa) / (qty_atual + qty_nova)
            p['total_cost'] += qty_tx * price + fees
            p['qty']        += qty_tx
        else:
            # Venda: reduz qty e custo proporcional. PM nao muda.
            # fees de venda NAO entram no custo da posicao restante.
            if p['qty'] > 1e-9:
                pm = p['total_cost'] / p['qty']
                p['total_cost'] -= pm * qty_tx
                p['total_cost']  = max(p['total_cost'], 0.0)  # guard contra float drift
            p['qty'] -= qty_tx
            p['qty']  = max(p['qty'], 0.0)  # guard contra float drift

    items = []
    for p in pos.values():
        qty = p['qty']
        if qty > 1e-9:
            pm        = p['total_cost'] / qty
            total_inv = round(p['total_cost'], 2)
            items.append({
                'ticker':         p['ticker'],
                'asset_type':     p['asset_type'],
                'asset_label':    ASSET_LABELS.get(p['asset_type'], p['asset_type']),
                'quantity':       round(qty, 8),
                'avg_price':      round(pm, 6),
                'total_invested': total_inv,
            })
    return items


def enrich_with_prices(
    items: list[dict],
    prices: dict[str, float | None],
) -> list[dict]:
    """
    Enriquece posicoes brutas com cotacao atual.

    Regra: se cotacao indisponivel:
      current_price  = None
      current_value  = None   (NUNCA usar PM como fallback)
      result_abs     = None
      result_pct     = None
    """
    enriched = []
    for item in items:
        ticker         = item['ticker']
        quantity       = item['quantity']
        total_invested = item['total_invested']

        raw_price     = prices.get(ticker)
        current_price = float(raw_price) if raw_price is not None else None

        if current_price is not None:
            current_value = round(quantity * current_price, 2)
            result_abs    = round(current_value - total_invested, 2)
            result_pct    = round(
                (result_abs / total_invested * 100) if total_invested > 0 else 0.0,
                4,
            )
        else:
            current_value = None
            result_abs    = None
            result_pct    = None

        enriched.append({
            **item,
            'current_price': round(current_price, 6) if current_price is not None else None,
            'current_value': current_value,
            'result_abs':    result_abs,
            'result_pct':    result_pct,
        })
    return enriched


async def calc_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """
    Orquestra: posicoes brutas -> cotacoes (BR com logo, internacionais sem) -> enriquece.
    """
    from app.services.quotes_service import BR_TYPES
    import asyncio

    raw = await calc_raw_positions(db, portfolio_id)
    if not raw:
        return []

    br_tickers   = [p['ticker'] for p in raw if p['asset_type'].upper() in BR_TYPES]
    intl_items   = [p for p in raw if p['asset_type'].upper() not in BR_TYPES]
    intl_tickers = [p['ticker'] for p in intl_items]

    br_meta, intl_prices = await asyncio.gather(
        fetch_quotes_with_meta(br_tickers) if br_tickers   else _empty_dict(),
        get_prices(intl_items)             if intl_tickers else _empty_dict(),
    )

    enriched = []
    for item in raw:
        ticker     = item['ticker']
        quantity   = item['quantity']
        total_inv  = item['total_invested']
        asset_type = item['asset_type'].upper()

        from app.services.quotes_service import BR_TYPES as _BR
        if asset_type in _BR and ticker in br_meta:
            meta          = br_meta[ticker]
            current_price = meta.get('price')
            logo_url      = meta.get('logo_url')
        else:
            current_price = intl_prices.get(ticker)
            logo_url      = None

        if current_price is not None:
            current_value = round(quantity * float(current_price), 2)
            result_abs    = round(current_value - total_inv, 2)
            result_pct    = round(
                (result_abs / total_inv * 100) if total_inv > 0 else 0.0,
                4,
            )
        else:
            current_value = None
            result_abs    = None
            result_pct    = None

        enriched.append({
            **item,
            'logo_url':      logo_url,
            'current_price': round(float(current_price), 6) if current_price is not None else None,
            'current_value': current_value,
            'result_abs':    result_abs,
            'result_pct':    result_pct,
        })

    return enriched


async def _empty_dict() -> dict:
    return {}


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
# Recalculo de posicoes materializadas (Position table)
# ---------------------------------------------------------------------------

async def recalc_positions(portfolio_id: int, db: AsyncSession) -> None:
    """
    Recalcula PM ponderado e quantidade atual para cada ativo da carteira,
    a partir do historico completo de transacoes.

    Regras aplicadas:
      - PM atualizado apenas em compras
      - Venda: qty diminui, avg_price permanece (PM invariante em vendas)
      - fees de venda nao alteram PM
      - Posicoes com qty <= 1e-9 sao removidas da tabela Position
    """
    txs_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = txs_result.scalars().all()

    # estado: ticker -> {qty, avg_price, total_cost, asset_type}
    state: dict[str, dict] = defaultdict(
        lambda: {'qty': 0.0, 'avg_price': 0.0, 'total_cost': 0.0, 'asset_type': ''}
    )

    for tx in txs:
        s      = state[tx.ticker]
        s['asset_type'] = normalize_type(tx.asset_type or 'OUTROS')

        qty_tx = float(tx.quantity)
        price  = float(tx.price)
        fees   = float(tx.fees or 0.0)  # guard contra None

        if tx.operation == OperationType.buy:
            new_cost       = s['total_cost'] + qty_tx * price + fees
            new_qty        = s['qty'] + qty_tx
            s['avg_price'] = new_cost / new_qty if new_qty > 0 else 0.0
            s['total_cost'] = new_cost
            s['qty']        = new_qty
        else:
            # PM nao muda; apenas qty e total_cost diminuem
            cost_reduction  = s['avg_price'] * qty_tx
            s['total_cost'] = max(s['total_cost'] - cost_reduction, 0.0)
            s['qty']        = max(s['qty'] - qty_tx, 0.0)

    active = {k: v for k, v in state.items() if v['qty'] > 1e-9}

    existing_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    existing = {p.ticker: p for p in existing_result.scalars().all()}

    # Remove posicoes zeradas da tabela
    for ticker in list(existing.keys()):
        if ticker not in active:
            await db.delete(existing[ticker])

    # Upsert posicoes ativas
    for ticker, data in active.items():
        if ticker in existing:
            pos           = existing[ticker]
            pos.quantity  = data['qty']
            pos.avg_price = data['avg_price']
        else:
            pos = Position(
                portfolio_id = portfolio_id,
                ticker       = ticker,
                asset_type   = data['asset_type'],
                quantity     = data['qty'],
                avg_price    = data['avg_price'],
            )
            db.add(pos)

    await db.flush()
