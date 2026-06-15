"""
Servico de snapshots diários de patrimônio.

Fluxo de cálculo para uma data D:
  1. Carrega todas as transactions da carteira até D (inclusive).
  2. Calcula qty líquida e custo médio por ticker (FIFO simplificado).
  3. Para cada ticker com qty > 0, busca o preco de fechamento em D
     via get_price_at_date() — banco primeiro, API só se necessario.
  4. Agrega: market_value, cost_basis, invested_total, realized_pnl,
             unrealized_pnl, total_pnl, return_pct.
  5. Persiste em portfolio_snapshots com INSERT ON CONFLICT DO UPDATE.

Funções públicas:
  - calc_snapshot_at_date()   : calcula e persiste snapshot de 1 data.
  - backfill_snapshots()      : preenche histórico desde a 1a transacao.
  - get_daily_evolution()     : retorna série diária para gráficos.
  - get_monthly_evolution()   : agrega a série diária por mês.
  - refresh_today_snapshot()  : atualiza o snapshot do dia corrente
                                (chamado pelo scheduler após atualizar cotacoes).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction, OperationType
from app.services.price_history_service import get_price_at_date

logger = logging.getLogger(__name__)


# ── estrutura interna de posicao ────────────────────────────────────────────────────

class _TickerState:
    """Acumula qty, custo medio e realized_pnl para um ticker ate a data D."""
    __slots__ = ("ticker", "asset_type", "qty", "cost", "realized_pnl")

    def __init__(self, ticker: str, asset_type: str):
        self.ticker       = ticker
        self.asset_type   = asset_type
        self.qty          = Decimal("0")
        self.cost         = Decimal("0")   # custo total das acoes em carteira
        self.realized_pnl = Decimal("0")

    def buy(self, qty: Decimal, price: Decimal) -> None:
        self.qty  += qty
        self.cost += qty * price

    def sell(self, qty: Decimal, price: Decimal) -> None:
        sold = min(qty, self.qty)
        if self.qty > 0:
            avg           = self.cost / self.qty
            self.realized_pnl += sold * (price - avg)
            self.cost    -= sold * avg
        self.qty  -= sold
        self.qty   = max(self.qty,  Decimal("0"))
        self.cost  = max(self.cost, Decimal("0"))

    @property
    def avg_price(self) -> Decimal:
        return self.cost / self.qty if self.qty > 0 else Decimal("0")


# ── helpers ──────────────────────────────────────────────────────────────────────────

def _safe_div(a: Decimal, b: Decimal) -> Decimal:
    return a / b if b else Decimal("0")


async def _build_positions_at(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, _TickerState]:
    """
    Reconstroi as posicoes (qty + custo medio + realized_pnl) de uma
    carteira considerando apenas as transacoes ate target_date (inclusive).
    """
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date         <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()

    states: dict[str, _TickerState] = {}
    for tx in txs:
        key = tx.ticker.upper()
        if key not in states:
            states[key] = _TickerState(key, tx.asset_type)
        s   = states[key]
        qty   = Decimal(str(tx.quantity))
        price = Decimal(str(tx.price))
        if tx.operation == OperationType.buy:
            s.buy(qty, price)
        elif tx.operation == OperationType.sell:
            s.sell(qty, price)

    # Remove tickers completamente zerados
    return {k: v for k, v in states.items() if v.qty > 0}


async def _calc_totals(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict:
    """
    Calcula todos os campos necessarios para um PortfolioSnapshot.
    Retorna dict com os valores ou None se nao houver posicoes.
    """
    positions = await _build_positions_at(db, portfolio_id, target_date)
    if not positions:
        return {
            "market_value":   Decimal("0"),
            "cost_basis":     Decimal("0"),
            "invested_total": Decimal("0"),
            "realized_pnl":   Decimal("0"),
            "unrealized_pnl": Decimal("0"),
            "total_pnl":      Decimal("0"),
            "return_pct":     Decimal("0"),
        }

    date_str     = target_date.isoformat()
    market_value = Decimal("0")
    cost_basis   = Decimal("0")
    realized_pnl = Decimal("0")

    for ticker, state in positions.items():
        # Busca asset para obter asset_type enum
        asset_result = await db.execute(
            select(Asset).where(Asset.ticker == ticker)
        )
        asset = asset_result.scalar_one_or_none()
        asset_type = AssetType(state.asset_type) if asset is None else asset.asset_type

        close = await get_price_at_date(db, ticker, asset_type, date_str)
        if close is None:
            # sem cotacao: usa custo medio como proxy (nao distorce o calculo)
            close = float(state.avg_price)
            logger.warning(
                "[snapshot] sem cotacao para %s em %s — usando avg_price como proxy",
                ticker, date_str,
            )

        market_value += state.qty * Decimal(str(close))
        cost_basis   += state.cost
        realized_pnl += state.realized_pnl

    # invested_total: soma liquida de aportes (compras - vendas a preco de custo)
    invested_result = await db.execute(
        select(
            func.sum(
                func.case(
                    (Transaction.operation == OperationType.buy,
                     Transaction.price * Transaction.quantity),
                    else_=-(Transaction.price * Transaction.quantity),
                )
            )
        ).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date         <= target_date,
        )
    )
    invested_total = Decimal(str(invested_result.scalar_one() or 0))

    unrealized_pnl = market_value - cost_basis
    total_pnl      = realized_pnl + unrealized_pnl
    return_pct     = _safe_div(total_pnl, invested_total) * 100 if invested_total > 0 else Decimal("0")

    return {
        "market_value":   market_value.quantize(Decimal("0.01")),
        "cost_basis":     cost_basis.quantize(Decimal("0.01")),
        "invested_total": invested_total.quantize(Decimal("0.01")),
        "realized_pnl":   realized_pnl.quantize(Decimal("0.01")),
        "unrealized_pnl": unrealized_pnl.quantize(Decimal("0.01")),
        "total_pnl":      total_pnl.quantize(Decimal("0.01")),
        "return_pct":     return_pct.quantize(Decimal("0.0001")),
    }


async def _upsert_snapshot(
    db: AsyncSession,
    portfolio_id: int,
    snapshot_date: date,
    totals: dict,
) -> None:
    """INSERT ON CONFLICT DO UPDATE — seguro para rodar multiplas vezes no mesmo dia."""
    stmt = (
        pg_insert(PortfolioSnapshot)
        .values(
            portfolio_id  = portfolio_id,
            snapshot_date = snapshot_date,
            **totals,
        )
        .on_conflict_do_update(
            constraint="uq_snapshot_portfolio_date",
            set_={
                "market_value":   totals["market_value"],
                "cost_basis":     totals["cost_basis"],
                "invested_total": totals["invested_total"],
                "realized_pnl":   totals["realized_pnl"],
                "unrealized_pnl": totals["unrealized_pnl"],
                "total_pnl":      totals["total_pnl"],
                "return_pct":     totals["return_pct"],
            },
        )
    )
    await db.execute(stmt)


# ── API publica ─────────────────────────────────────────────────────────────────────────

async def calc_snapshot_at_date(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
    commit: bool = True,
) -> dict:
    """
    Calcula e persiste o snapshot de uma carteira em target_date.
    Retorna o dict de totais calculados.
    """
    totals = await _calc_totals(db, portfolio_id, target_date)
    await _upsert_snapshot(db, portfolio_id, target_date, totals)
    if commit:
        await db.commit()
    logger.info(
        "[snapshot] portfolio=%s date=%s market_value=%s return_pct=%s%%",
        portfolio_id, target_date, totals["market_value"], totals["return_pct"],
    )
    return totals


async def backfill_snapshots(
    db: AsyncSession,
    portfolio_id: int,
    days_back: Optional[int] = None,
) -> int:
    """
    Preenche historico de snapshots desde a primeira transacao da carteira
    (ou desde `days_back` dias atras, se fornecido).

    Otimizacao: pula datas que ja tem snapshot persistido e cujo
    snapshot_date < hoje (dados imutaveis no passado).

    Retorna numero de snapshots inseridos/atualizados.
    """
    # Data da primeira transacao
    first_tx = await db.execute(
        select(func.min(Transaction.date))
        .where(Transaction.portfolio_id == portfolio_id)
    )
    first_date = first_tx.scalar_one_or_none()
    if first_date is None:
        return 0

    start = first_date
    if days_back is not None:
        start = max(start, date.today() - timedelta(days=days_back))

    # Snapshots ja existentes no intervalo (para pular)
    existing = await db.execute(
        select(PortfolioSnapshot.snapshot_date)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= start,
            PortfolioSnapshot.snapshot_date <  date.today(),  # hoje sempre recalcula
        )
    )
    existing_dates = {r.snapshot_date for r in existing.all()}

    count  = 0
    cursor = start
    today  = date.today()

    while cursor <= today:
        # Pula fins de semana (mercado fechado — sem cotacao nova)
        if cursor.weekday() < 5 and cursor not in existing_dates:
            totals = await _calc_totals(db, portfolio_id, cursor)
            await _upsert_snapshot(db, portfolio_id, cursor, totals)
            count += 1

            # Commit a cada 30 dias para nao acumular transacao enorme
            if count % 30 == 0:
                await db.commit()

        cursor += timedelta(days=1)

    await db.commit()
    logger.info(
        "[snapshot] backfill portfolio=%s: %s snapshots processados (start=%s)",
        portfolio_id, count, start,
    )
    return count


async def refresh_today_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> dict:
    """
    Atualiza o snapshot do dia corrente.
    Chamado pelo scheduler apos update_all_quotes().
    Usa commit=True internamente.
    """
    return await calc_snapshot_at_date(db, portfolio_id, date.today(), commit=True)


async def get_daily_evolution(
    db: AsyncSession,
    portfolio_id: int,
    days: int = 365,
) -> list[dict]:
    """
    Retorna serie diaria de snapshots para graficos de evolucao patrimonial.
    Lista ordenada por data asc.
    """
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id  == portfolio_id,
            PortfolioSnapshot.snapshot_date >= since,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "date":           str(r.snapshot_date),
            "market_value":   float(r.market_value),
            "cost_basis":     float(r.cost_basis),
            "invested_total": float(r.invested_total),
            "unrealized_pnl": float(r.unrealized_pnl),
            "realized_pnl":   float(r.realized_pnl),
            "total_pnl":      float(r.total_pnl),
            "return_pct":     float(r.return_pct),
        }
        for r in rows
    ]


async def get_monthly_evolution(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 24,
) -> list[dict]:
    """
    Agrega a serie diaria por mes (ultimo snapshot disponivel do mes).
    Retorna lista ordenada por periodo asc — ideal para grafico de barras mensal.
    """
    since = date.today() - timedelta(days=months * 31)

    # Subconsulta: maior data de snapshot por mes
    sub = (
        select(
            func.date_trunc("month", PortfolioSnapshot.snapshot_date).label("month"),
            func.max(PortfolioSnapshot.snapshot_date).label("last_date"),
        )
        .where(
            PortfolioSnapshot.portfolio_id  == portfolio_id,
            PortfolioSnapshot.snapshot_date >= since,
        )
        .group_by(text("1"))
        .subquery()
    )

    result = await db.execute(
        select(PortfolioSnapshot)
        .join(
            sub,
            PortfolioSnapshot.snapshot_date == sub.c.last_date,
        )
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "period":         r.snapshot_date.strftime("%Y-%m"),
            "market_value":   float(r.market_value),
            "cost_basis":     float(r.cost_basis),
            "invested_total": float(r.invested_total),
            "unrealized_pnl": float(r.unrealized_pnl),
            "realized_pnl":   float(r.realized_pnl),
            "total_pnl":      float(r.total_pnl),
            "return_pct":     float(r.return_pct),
        }
        for r in rows
    ]
