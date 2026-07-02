"""
Servico de snapshots diarios de patrimonio.

SEMANTICA DOS CAMPOS CALCULADOS
================================
Os snapshots capturam o retorno de PRECO puro da carteira, sem proventos.

  total_pnl  = realized_pnl + unrealized_pnl
               Lucro/prejuizo de compra e venda e valorizacao de preco.
               NAO inclui dividendos, JCP, rendimentos de RF nem outros
               proventos recebidos. Estes ficam em app.models.dividend.

  return_pct = total_pnl / (cost_basis + max(realized_pnl, 0)) * 100
               Percentual de retorno de preco sobre capital empregado.
               Usa cost_basis + realized positivo como denominador para
               evitar distorcao quando ha muitas vendas (invested_total
               diminui com resgates, podendo inflar o percentual).
               Fallback: invested_total quando nao ha posicoes abertas.

RETORNO TOTAL COM PROVENTOS (uso no rentabilidade_service)
==========================================================
  Se a UI precisar exibir retorno total incluindo proventos:
    retorno_total_com_prov = (total_pnl + proventos_total) / base * 100
  Onde proventos_total vem de _proventos_total() no rentabilidade_service.
  O campo retorno_total_pct do payload de /kpis NAO inclui proventos;
  os campos proventos_total e proventos_12m sao expostos separadamente
  para que o frontend calcule e exiba o retorno total conforme necessidade.

FLUXO DE ATUALIZACAO
====================
  backfill_snapshots  : reconstroi historico completo dia a dia (semanal/sob demanda)
  refresh_today_snapshot : atualiza o snapshot de hoje (chamado apos cada transacao)
  invalidate_snapshots_from : remove snapshots a partir de uma data (ex: correcao de transacao)

OTIMIZACOES DE QUERY (Bloco 2)
================================
  [Q1 CORRIGIDO] _calc_totals: Asset buscado em batch antes do loop de posicoes.
  Antes: 1 SELECT por ticker (N+1). Depois: 1 SELECT com IN(tickers).
  Impacto em backfill 1 ano com 20 tickers: 5.000 queries -> 250 queries.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, case, text, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction, OperationType
from app.services.price_history_service import get_price_at_date, persist_daily_prices

logger = logging.getLogger(__name__)

# Tipos cotados em USD
_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


class _TickerState:
    """Acumula custo sempre em BRL (independente da moeda original)."""
    __slots__ = ("ticker", "asset_type", "qty", "cost", "realized_pnl", "is_usd")

    def __init__(self, ticker: str, asset_type: str, is_usd: bool = False):
        self.ticker = ticker
        self.asset_type = asset_type
        self.qty = Decimal("0")
        self.cost = Decimal("0")          # sempre em BRL
        self.realized_pnl = Decimal("0")  # sempre em BRL
        self.is_usd = is_usd

    def buy(self, qty: Decimal, price_brl: Decimal, fees_brl: Decimal = Decimal("0")) -> None:
        """price_brl e fees_brl ja devem estar convertidos para BRL."""
        self.qty += qty
        self.cost += qty * price_brl + fees_brl

    def sell(self, qty: Decimal, price_brl: Decimal) -> None:
        """price_brl ja deve estar convertido para BRL."""
        sold = min(qty, self.qty)
        if self.qty > 0:
            avg = self.cost / self.qty
            self.realized_pnl += sold * (price_brl - avg)
            self.cost -= sold * avg
        self.qty -= sold
        self.qty = max(self.qty, Decimal("0"))
        self.cost = max(self.cost, Decimal("0"))

    @property
    def avg_price(self) -> Decimal:
        return self.cost / self.qty if self.qty > 0 else Decimal("0")


def _safe_div(a: Decimal, b: Decimal) -> Decimal:
    return a / b if b else Decimal("0")


async def invalidate_snapshots_from(
    db: AsyncSession,
    portfolio_id: int,
    from_date: date,
    commit: bool = False,
) -> int:
    stmt = delete(PortfolioSnapshot).where(
        PortfolioSnapshot.portfolio_id == portfolio_id,
        PortfolioSnapshot.snapshot_date >= from_date,
    )
    result = await db.execute(stmt)
    deleted = result.rowcount
    if commit:
        await db.commit()
    logger.info(
        "[snapshot] invalidate portfolio=%s from=%s — %s snapshots removidos",
        portfolio_id, from_date, deleted,
    )
    return deleted


async def _build_positions_at(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, _TickerState]:
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()

    states: dict[str, _TickerState] = {}
    for tx in txs:
        key = tx.ticker.upper()

        asset_type_raw = (
            tx.asset_type.value if hasattr(tx.asset_type, "value") else str(tx.asset_type or "")
        ).upper()
        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or asset_type_raw in _USD_ASSET_TYPES
        )

        fx_rate = Decimal("1")
        if is_usd:
            saved = getattr(tx, "fx_rate", None)
            if saved is not None and float(saved or 0) > 0:
                fx_rate = Decimal(str(saved))

        if key not in states:
            states[key] = _TickerState(key, tx.asset_type, is_usd=is_usd)
        s = states[key]

        qty = Decimal(str(tx.quantity))
        price_brl = Decimal(str(tx.price)) * fx_rate
        fees_brl = Decimal(str(tx.fees or 0)) * fx_rate

        if tx.operation == OperationType.buy:
            s.buy(qty, price_brl, fees_brl)
        elif tx.operation == OperationType.sell:
            s.sell(qty, price_brl)

    return {k: v for k, v in states.items() if v.qty > 0}


async def _calc_totals(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict:
    positions = await _build_positions_at(db, portfolio_id, target_date)
    if not positions:
        return {
            "market_value": Decimal("0"),
            "cost_basis": Decimal("0"),
            "invested_total": Decimal("0"),
            "realized_pnl": Decimal("0"),
            "unrealized_pnl": Decimal("0"),
            "total_pnl": Decimal("0"),
            "return_pct": Decimal("0"),
        }

    date_str = target_date.isoformat()
    market_value = Decimal("0")
    cost_basis = Decimal("0")
    realized_pnl = Decimal("0")

    # ------------------------------------------------------------------
    # [Q1 FIX] Busca asset_type de todos os tickers em uma unica query
    # antes de entrar no loop, eliminando o N+1 que existia antes.
    # ------------------------------------------------------------------
    tickers_list = list(positions.keys())
    asset_rows = await db.execute(
        select(Asset.ticker, Asset.asset_type)
        .where(Asset.ticker.in_(tickers_list))
    )
    asset_type_map: dict[str, AssetType] = {
        r.ticker: r.asset_type for r in asset_rows.all()
    }

    fx_snapshot: Optional[float] = None
    has_usd = any(s.is_usd for s in positions.values())
    if has_usd:
        try:
            from app.services.fx_service import get_usd_brl_for_date
            fx_snapshot = await get_usd_brl_for_date(db, target_date)
        except Exception:
            try:
                from app.services.fx_service import get_usd_brl_today
                fx_snapshot = await get_usd_brl_today(db)
            except Exception:
                fx_snapshot = 1.0

    # ------------------------------------------------------------------
    # FIX N+1: Carrega todos os preços de uma vez usando batch
    # ------------------------------------------------------------------
    from app.services.price_history_service import get_prices_at_date_batch
    
    tickers_with_types = []
    for ticker, state in positions.items():
        asset_type = asset_type_map.get(ticker)
        if asset_type is None:
            try:
                asset_type = AssetType(state.asset_type)
            except (ValueError, KeyError):
                asset_type = AssetType.ACAO
        tickers_with_types.append((ticker, asset_type))
    
    # Carrega todos os preços em uma única operação
    prices_map = await get_prices_at_date_batch(db, tickers_with_types, date_str)
    
    for ticker, state in positions.items():
        close = prices_map.get(ticker)
        if close is None:
            close = float(state.avg_price)
            logger.warning(
                "[snapshot] sem cotacao para %s em %s - usando avg_price como proxy",
                ticker, date_str,
            )

        close_brl = close
        if state.is_usd and fx_snapshot:
            close_brl = close * fx_snapshot

        market_value += state.qty * Decimal(str(close_brl))
        cost_basis += state.cost
        realized_pnl += state.realized_pnl

    invested_result = await db.execute(
        select(
            func.sum(
                case(
                    (
                        Transaction.operation == OperationType.buy,
                        (
                            Transaction.price
                            * func.coalesce(Transaction.fx_rate, 1.0)
                            * Transaction.quantity
                            + func.coalesce(Transaction.fees, 0)
                            * func.coalesce(Transaction.fx_rate, 1.0)
                        ),
                    ),
                    else_=-(
                        Transaction.price
                        * func.coalesce(Transaction.fx_rate, 1.0)
                        * Transaction.quantity
                    ),
                )
            )
        ).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= target_date,
        )
    )
    invested_total = Decimal(str(invested_result.scalar_one() or 0))

    unrealized_pnl = market_value - cost_basis
    total_pnl = realized_pnl + unrealized_pnl
    # NOTA: total_pnl NAO inclui proventos. Ver docstring do modulo.

    # -------------------------------------------------------------------------
    # return_pct: retorno de preco sobre capital empregado.
    # ATENCAO: este valor e "retorno de preco". Para retorno total com
    # proventos ver documentacao do modulo acima.
    # -------------------------------------------------------------------------
    realized_positive = max(realized_pnl, Decimal("0"))
    return_base = cost_basis + realized_positive
    if return_base > 0:
        return_pct = _safe_div(total_pnl, return_base) * 100
    elif invested_total > 0:
        return_pct = _safe_div(total_pnl, invested_total) * 100
    else:
        return_pct = Decimal("0")

    return {
        "market_value": market_value.quantize(Decimal("0.01")),
        "cost_basis": cost_basis.quantize(Decimal("0.01")),
        "invested_total": invested_total.quantize(Decimal("0.01")),
        "realized_pnl": realized_pnl.quantize(Decimal("0.01")),
        "unrealized_pnl": unrealized_pnl.quantize(Decimal("0.01")),
        "total_pnl": total_pnl.quantize(Decimal("0.01")),
        "return_pct": return_pct.quantize(Decimal("0.0001")),
    }


async def _upsert_snapshot(
    db: AsyncSession,
    portfolio_id: int,
    snapshot_date: date,
    totals: dict,
) -> None:
    stmt = (
        pg_insert(PortfolioSnapshot)
        .values(
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            **totals,
        )
        .on_conflict_do_update(
            constraint="uq_snapshot_portfolio_date",
            set_={
                "market_value": totals["market_value"],
                "cost_basis": totals["cost_basis"],
                "invested_total": totals["invested_total"],
                "realized_pnl": totals["realized_pnl"],
                "unrealized_pnl": totals["unrealized_pnl"],
                "total_pnl": totals["total_pnl"],
                "return_pct": totals["return_pct"],
            },
        )
    )
    await db.execute(stmt)


async def _prefetch_price_history(
    db: AsyncSession,
    portfolio_id: int,
    days_back: int,
) -> None:
    result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    tickers = result.all()
    if not tickers:
        return

    logger.info(
        "[snapshot] pre-fetch FORCADO de historico para %d tickers (days_back=%d)",
        len(tickers), days_back,
    )
    for row in tickers:
        ticker = row.ticker.upper()
        try:
            asset_type = AssetType(row.asset_type)
        except ValueError:
            asset_type = AssetType.ACAO
        logger.info(
            "[snapshot] pre-fetch %s (%s) days_back=%d",
            ticker, asset_type.value, days_back,
        )
        await persist_daily_prices(db, ticker, asset_type, days_back=days_back, force=True)


async def calc_snapshot_at_date(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
    commit: bool = True,
    prefetch: bool = False,
) -> dict:
    if prefetch:
        days_back = (date.today() - target_date).days + 6
        await _prefetch_price_history(db, portfolio_id, days_back)

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

    total_days = (date.today() - start).days + 1

    existing = await db.execute(
        select(PortfolioSnapshot.snapshot_date)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= start,
            PortfolioSnapshot.snapshot_date < date.today(),
        )
    )
    existing_dates = {r.snapshot_date for r in existing.all()}

    await _prefetch_price_history(db, portfolio_id, days_back=total_days)

    count = 0
    cursor = start
    today = date.today()

    while cursor <= today:
        if cursor.weekday() < 5 and cursor not in existing_dates:
            totals = await _calc_totals(db, portfolio_id, cursor)
            await _upsert_snapshot(db, portfolio_id, cursor, totals)
            count += 1
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
    return await calc_snapshot_at_date(
        db, portfolio_id, date.today(), commit=True, prefetch=True
    )


async def get_daily_evolution(
    db: AsyncSession,
    portfolio_id: int,
    days: int = 365,
) -> list[dict]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= since,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "date": str(r.snapshot_date),
            "market_value": float(r.market_value),
            "cost_basis": float(r.cost_basis),
            "invested_total": float(r.invested_total),
            "unrealized_pnl": float(r.unrealized_pnl),
            "realized_pnl": float(r.realized_pnl),
            "total_pnl": float(r.total_pnl),
            "return_pct": float(r.return_pct),
        }
        for r in rows
    ]


async def get_monthly_evolution(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 24,
) -> list[dict]:
    since = date.today() - timedelta(days=months * 31)
    sub = (
        select(
            func.date_trunc("month", PortfolioSnapshot.snapshot_date).label("month"),
            func.max(PortfolioSnapshot.snapshot_date).label("last_date"),
        )
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date >= since,
        )
        .group_by(text("1"))
        .subquery()
    )

    result = await db.execute(
        select(PortfolioSnapshot)
        .join(sub, PortfolioSnapshot.snapshot_date == sub.c.last_date)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "date": r.snapshot_date.strftime("%Y-%m-%d"),
            "value": float(r.market_value),
            "invested": float(r.invested_total),
            "period": r.snapshot_date.strftime("%Y-%m"),
            "market_value": float(r.market_value),
            "cost_basis": float(r.cost_basis),
            "invested_total": float(r.invested_total),
            "unrealized_pnl": float(r.unrealized_pnl),
            "realized_pnl": float(r.realized_pnl),
            "total_pnl": float(r.total_pnl),
            "return_pct": float(r.return_pct),
        }
        for r in rows
    ]
