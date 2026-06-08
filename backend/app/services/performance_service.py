"""Calculo de rentabilidade por ativo e por carteira.

Terminologia:
  cost_basis      = quantidade_atual * preco_medio_BRL
  current_value   = quantidade_atual * cotacao_atual_BRL
  unrealized_pnl  = current_value - cost_basis
  realized_pnl    = soma de todas as vendas (preco_venda - preco_medio) * qtd
  total_pnl       = unrealized_pnl + realized_pnl
  return_pct      = total_pnl / cost_basis * 100

Ativos USD (STOCK, ETF_INTERNACIONAL, REIT):
  - cotacao_atual_BRL = cotacao_USD * fx_rate_atual
  - fx_variation      = (fx_atual - fx_medio) / fx_medio * 100
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy import func, and_, extract, case
from sqlalchemy.orm import Session

from app.integrations.fx_rate import get_usd_brl
from app.integrations.brapi import get_quote  # retorna regularMarketPrice
from app.models.asset import Asset
from app.models.transaction import Transaction, TransactionType
from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)

USD_TYPES = {"STOCK", "ETF_INTERNACIONAL", "REIT"}


# ─── Estruturas de dados ──────────────────────────────────────────────────────

@dataclass
class AssetPerformance:
    ticker: str
    asset_type: str
    currency: str
    quantity: float
    avg_price: float          # preco medio em moeda original
    avg_price_brl: float      # preco medio em BRL
    current_price: float      # cotacao atual em moeda original
    current_price_brl: float  # cotacao atual em BRL
    cost_basis: float         # custo total em BRL
    current_value: float      # valor atual em BRL
    unrealized_pnl: float     # ganho/perda nao realizado em BRL
    realized_pnl: float       # ganho/perda realizado em BRL
    total_pnl: float          # unrealized + realized em BRL
    return_pct: float         # retorno percentual total
    fx_rate_avg: Optional[float] = None   # fx medio das compras
    fx_rate_current: Optional[float] = None  # fx atual
    fx_variation_pct: Optional[float] = None  # variacao cambial %


@dataclass
class PortfolioPerformance:
    portfolio_id: int
    portfolio_name: str
    total_cost: float           # total investido (BRL)
    total_current: float        # valor atual total (BRL)
    total_unrealized: float     # pnl nao realizado
    total_realized: float       # pnl realizado
    total_pnl: float
    return_pct: float
    assets: list[AssetPerformance] = field(default_factory=list)
    # agrupamentos
    by_type: dict[str, dict] = field(default_factory=dict)  # por tipo de ativo
    history: list[dict] = field(default_factory=list)       # evolucao mensal


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


async def _fetch_price_brl(ticker: str, asset_type: str, fx_current: float) -> float:
    """Busca cotacao atual. Retorna 0.0 se falhar."""
    try:
        price = await get_quote(ticker)
        if asset_type in USD_TYPES:
            return float(price) * fx_current
        return float(price)
    except Exception as e:
        logger.warning(f"Cotacao indisponivel para {ticker}: {e}")
        return 0.0


async def _fetch_price_orig(ticker: str) -> float:
    """Cotacao atual na moeda original."""
    try:
        return float(await get_quote(ticker))
    except Exception:
        return 0.0


# ─── Calculo por ativo ─────────────────────────────────────────────────────────

async def calc_asset_performance(
    db: Session,
    portfolio_id: int,
    asset: Asset,
    fx_current: float,
) -> AssetPerformance:
    """Calcula rentabilidade de um ativo dentro de uma carteira."""
    is_usd = asset.asset_type in USD_TYPES

    txs = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_id == asset.id,
        )
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    qty = 0.0
    cost_brl = 0.0          # custo acumulado em BRL
    realized_pnl = 0.0
    total_fx_weighted = 0.0  # para calcular fx medio ponderado
    total_qty_bought = 0.0

    for tx in txs:
        unit_brl = float(tx.price_brl or tx.price)
        qty_tx = float(tx.quantity)

        if tx.transaction_type in (TransactionType.COMPRA, TransactionType.BONIFICACAO):
            qty += qty_tx
            cost_brl += qty_tx * unit_brl
            if is_usd and tx.fx_rate:
                total_fx_weighted += qty_tx * float(tx.fx_rate)
                total_qty_bought += qty_tx

        elif tx.transaction_type == TransactionType.VENDA:
            sold = min(qty_tx, qty)
            if qty > 0:
                avg_brl = _safe_div(cost_brl, qty)
                sell_brl = float(tx.price_brl or tx.price)
                realized_pnl += sold * (sell_brl - avg_brl)
                cost_brl -= sold * avg_brl
            qty -= sold
            qty = max(qty, 0.0)
            cost_brl = max(cost_brl, 0.0)

        elif tx.transaction_type == TransactionType.DESDOBRAMENTO:
            qty += qty_tx  # acrescenta cotas sem custo

        elif tx.transaction_type == TransactionType.GRUPAMENTO:
            qty = max(qty - qty_tx, 0.0)

    # cotacao atual
    current_price_orig = await _fetch_price_orig(asset.ticker)
    if is_usd:
        current_price_brl = current_price_orig * fx_current
    else:
        current_price_brl = current_price_orig

    avg_price_brl = _safe_div(cost_brl, qty)
    avg_price_orig = avg_price_brl / fx_current if (is_usd and fx_current) else avg_price_brl

    current_value = qty * current_price_brl
    unrealized_pnl = current_value - cost_brl
    total_pnl = unrealized_pnl + realized_pnl
    return_pct = _safe_div(total_pnl, cost_brl) * 100 if cost_brl else 0.0

    # variacao cambial
    fx_avg = _safe_div(total_fx_weighted, total_qty_bought) if total_qty_bought else None
    fx_variation = None
    if is_usd and fx_avg and fx_current:
        fx_variation = _safe_div(fx_current - fx_avg, fx_avg) * 100

    return AssetPerformance(
        ticker=asset.ticker,
        asset_type=asset.asset_type,
        currency="USD" if is_usd else "BRL",
        quantity=qty,
        avg_price=avg_price_orig,
        avg_price_brl=avg_price_brl,
        current_price=current_price_orig,
        current_price_brl=current_price_brl,
        cost_basis=cost_brl,
        current_value=current_value,
        unrealized_pnl=unrealized_pnl,
        realized_pnl=realized_pnl,
        total_pnl=total_pnl,
        return_pct=return_pct,
        fx_rate_avg=fx_avg,
        fx_rate_current=fx_current if is_usd else None,
        fx_variation_pct=fx_variation,
    )


# ─── Calculo por carteira ──────────────────────────────────────────────────────

async def calc_portfolio_performance(
    db: Session,
    portfolio_id: int,
    user_id: int,
) -> PortfolioPerformance:
    """Calcula rentabilidade consolidada de uma carteira."""
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if not portfolio:
        from fastapi import HTTPException
        raise HTTPException(404, "Carteira nao encontrada")

    # ativos com posicao aberta
    asset_ids = (
        db.query(Transaction.asset_id)
        .filter(Transaction.portfolio_id == portfolio_id)
        .distinct()
        .all()
    )
    assets = [
        db.query(Asset).filter(Asset.id == aid[0]).first()
        for aid in asset_ids
    ]
    assets = [a for a in assets if a]

    fx_current = await get_usd_brl()

    # calcula por ativo em paralelo
    import asyncio
    asset_perfs = await asyncio.gather(
        *[calc_asset_performance(db, portfolio_id, a, fx_current) for a in assets]
    )
    # filtra ativos com posicao zerada
    asset_perfs = [p for p in asset_perfs if p.quantity > 0]

    total_cost      = sum(p.cost_basis     for p in asset_perfs)
    total_current   = sum(p.current_value  for p in asset_perfs)
    total_unrealized= sum(p.unrealized_pnl for p in asset_perfs)
    total_realized  = sum(p.realized_pnl   for p in asset_perfs)
    total_pnl       = total_unrealized + total_realized
    return_pct      = _safe_div(total_pnl, total_cost) * 100

    # agrupamento por tipo
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
        v["return_pct"] = _safe_div(v["pnl"], v["cost"]) * 100
        v["allocation_pct"] = _safe_div(v["current"], total_current) * 100

    # evolucao mensal (snapshot de patrimônio por mes)
    history = _build_monthly_history(db, portfolio_id)

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


# ─── Evolucao mensal ──────────────────────────────────────────────────────────

def _build_monthly_history(db: Session, portfolio_id: int) -> list[dict]:
    """Retorna aporte mensal acumulado para grafico de evolucao do patrimônio."""
    rows = (
        db.query(
            extract("year",  Transaction.transaction_date).label("year"),
            extract("month", Transaction.transaction_date).label("month"),
            func.sum(
                case(
                    (Transaction.transaction_type.in_([TransactionType.COMPRA, TransactionType.BONIFICACAO]),
                     Transaction.total_value),
                    else_=0,
                )
            ).label("inflow"),
            func.sum(
                case(
                    (Transaction.transaction_type == TransactionType.VENDA,
                     Transaction.total_value),
                    else_=0,
                )
            ).label("outflow"),
        )
        .filter(Transaction.portfolio_id == portfolio_id)
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    history = []
    cumulative = 0.0
    for r in rows:
        net = float(r.inflow or 0) - float(r.outflow or 0)
        cumulative += net
        history.append({
            "period": f"{int(r.year):04d}-{int(r.month):02d}",
            "inflow": float(r.inflow or 0),
            "outflow": float(r.outflow or 0),
            "net_invested": cumulative,
        })
    return history
