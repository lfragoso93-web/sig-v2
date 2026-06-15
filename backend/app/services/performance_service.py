"""Calculo de rentabilidade por ativo e por carteira.

Terminologia:
  cost_basis      = quantidade_atual * preco_medio_BRL
  current_value   = quantidade_atual * cotacao_atual_BRL
  unrealized_pnl  = current_value - cost_basis
  realized_pnl    = soma de todas as vendas (preco_venda - preco_medio) * qtd
  total_pnl       = unrealized_pnl + realized_pnl
  return_pct      = total_pnl / cost_basis * 100

Ativos USD (STOCK, ETF_INTERNACIONAL):
  - cotacao_atual_BRL = cotacao_USD * fx_rate_atual

Mudancas Sprint 5:
  - _fetch_price_brl() agora usa quotes_service.get_prices(db=db)
    passando por cache L1 (Asset.last_price) e L2 (memoria) antes de ir a API.
  - _build_monthly_history() substituido por get_monthly_evolution() do
    portfolio_snapshot_service, que usa valor de MERCADO real (nao so custo).
  - USD_TYPES alinhado com asset_types.py.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import INTL_TYPES
from app.integrations.fx_rate import get_usd_brl
from app.models.asset import AssetType
from app.models.transaction import Transaction, OperationType
from app.models.portfolio import Portfolio
from app.services.quotes_service import get_prices
from app.services.portfolio_snapshot_service import get_monthly_evolution

logger = logging.getLogger(__name__)

# Tipos que cotam em USD (alinhado com asset_types.INTL_TYPES)
USD_TYPES = {at.value for at in INTL_TYPES}


# ── Estruturas de dados ─────────────────────────────────────────────────────────

@dataclass
class AssetPerformance:
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


@dataclass
class PortfolioPerformance:
    portfolio_id: int
    portfolio_name: str
    total_cost: float
    total_current: float
    total_unrealized: float
    total_realized: float
    total_pnl: float
    return_pct: float
    assets: list[AssetPerformance] = field(default_factory=list)
    by_type: dict[str, dict] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────────

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


async def _fetch_prices_brl(
    db: AsyncSession,
    tickers_types: list[tuple[str, str]],
    fx_current: float,
) -> dict[str, float]:
    """
    Busca cotacoes atuais via quotes_service (L1 banco → L2 memoria → L3 API).
    Converte USD→BRL para ativos internacionais.
    Retorna {ticker: price_brl}.
    """
    positions_payload = [
        {"ticker": t, "asset_type": at}
        for t, at in tickers_types
    ]
    raw = await get_prices(positions_payload, db=db)

    result: dict[str, float] = {}
    for ticker, asset_type in tickers_types:
        price = raw.get(ticker)
        if price is None:
            logger.warning("Cotacao indisponivel para %s", ticker)
            result[ticker] = 0.0
            continue
        if asset_type in USD_TYPES:
            result[ticker] = float(price) * fx_current
        else:
            result[ticker] = float(price)
    return result


# ── Calculo por ativo ─────────────────────────────────────────────────────────────

async def calc_asset_performance(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str,
    fx_current: float,
    prices_brl: dict[str, float],
) -> AssetPerformance:
    """
    Calcula rentabilidade de um ativo dentro de uma carteira.
    Recebe `prices_brl` pre-buscado em lote para evitar N chamadas a API.
    """
    is_usd = asset_type in USD_TYPES

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker       == ticker,
        )
        .order_by(Transaction.date.asc())
    )
    txs = result.scalars().all()

    qty          = 0.0
    cost_brl     = 0.0
    realized_pnl = 0.0

    for tx in txs:
        unit_price = float(tx.price)
        qty_tx     = float(tx.quantity)
        unit_brl   = unit_price * fx_current if is_usd else unit_price

        if tx.operation == OperationType.buy:
            qty      += qty_tx
            cost_brl += qty_tx * unit_brl
        elif tx.operation == OperationType.sell:
            sold = min(qty_tx, qty)
            if qty > 0:
                avg_brl       = _safe_div(cost_brl, qty)
                realized_pnl += sold * (unit_brl - avg_brl)
                cost_brl     -= sold * avg_brl
            qty      -= sold
            qty       = max(qty, 0.0)
            cost_brl  = max(cost_brl, 0.0)

    current_price_brl = prices_brl.get(ticker, 0.0)
    avg_price_brl     = _safe_div(cost_brl, qty)
    current_value     = qty * current_price_brl
    unrealized_pnl    = current_value - cost_brl
    total_pnl         = unrealized_pnl + realized_pnl
    return_pct        = _safe_div(total_pnl, cost_brl) * 100 if cost_brl else 0.0

    return AssetPerformance(
        ticker=ticker,
        asset_type=asset_type,
        currency="USD" if is_usd else "BRL",
        quantity=qty,
        avg_price_brl=avg_price_brl,
        current_price_brl=current_price_brl,
        cost_basis=cost_brl,
        current_value=current_value,
        unrealized_pnl=unrealized_pnl,
        realized_pnl=realized_pnl,
        total_pnl=total_pnl,
        return_pct=return_pct,
        fx_rate_current=fx_current if is_usd else None,
    )


# ── Calculo por carteira ───────────────────────────────────────────────────────────

async def calc_portfolio_performance(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> PortfolioPerformance:
    """Calcula rentabilidade consolidada de uma carteira."""
    port_result = await db.execute(
        select(Portfolio).where(
            Portfolio.id      == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    portfolio = port_result.scalar_one_or_none()
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(404, "Carteira nao encontrada")

    # Tickers distintos com posicao na carteira
    rows_result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    rows = rows_result.all()
    tickers_types = [(r.ticker, r.asset_type) for r in rows]

    # Busca fx e cotacoes em paralelo
    import asyncio
    fx_current, prices_brl = await asyncio.gather(
        get_usd_brl(),
        _fetch_prices_brl(db, tickers_types, 1.0),  # fx aplicado abaixo por ativo
    )
    # Re-aplica fx correto (a chamada acima usou fx=1.0 para nao duplicar)
    prices_brl_fx: dict[str, float] = {}
    raw_prices = await get_prices(
        [{"ticker": t, "asset_type": at} for t, at in tickers_types],
        db=db,
    )
    for ticker, asset_type in tickers_types:
        price = raw_prices.get(ticker, 0.0)
        prices_brl_fx[ticker] = price * fx_current if asset_type in USD_TYPES else price

    asset_perfs = await asyncio.gather(
        *[
            calc_asset_performance(
                db, portfolio_id, ticker, asset_type, fx_current, prices_brl_fx
            )
            for ticker, asset_type in tickers_types
        ]
    )
    asset_perfs = [p for p in asset_perfs if p.quantity > 0]

    total_cost       = sum(p.cost_basis     for p in asset_perfs)
    total_current    = sum(p.current_value  for p in asset_perfs)
    total_unrealized = sum(p.unrealized_pnl for p in asset_perfs)
    total_realized   = sum(p.realized_pnl   for p in asset_perfs)
    total_pnl        = total_unrealized + total_realized
    return_pct       = _safe_div(total_pnl, total_cost) * 100

    by_type: dict[str, dict] = {}
    for p in asset_perfs:
        t = p.asset_type
        if t not in by_type:
            by_type[t] = {"cost": 0.0, "current": 0.0, "pnl": 0.0, "count": 0}
        by_type[t]["cost"]    += p.cost_basis
        by_type[t]["current"] += p.current_value
        by_type[t]["pnl"]     += p.total_pnl
        by_type[t]["count"]   += 1
    for t, v in by_type.items():
        v["return_pct"]     = _safe_div(v["pnl"], v["cost"]) * 100
        v["allocation_pct"] = _safe_div(v["current"], total_current) * 100

    # Historico mensal via snapshots (valor de mercado real, nao apenas custo)
    history = await get_monthly_evolution(db, portfolio_id, months=24)

    return PortfolioPerformance(
        portfolio_id=portfolio_id,
        portfolio_name=portfolio.name,
        total_cost=total_cost,
        total_current=total_current,
        total_unrealized=total_unrealized,
        total_realized=total_realized,
        total_pnl=total_pnl,
        return_pct=return_pct,
        assets=asset_perfs,
        by_type=by_type,
        history=history,
    )
