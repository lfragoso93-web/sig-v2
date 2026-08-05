"""
rentabilidade_service.py

Camada de agregação de rentabilidade.

Para RENDA_FIXA, não há conceito de cota/preço de mercado. Cada compra é
tratada como uma aplicação individual e o resultado é agrupado pelo serviço
fixed_income_valuation_service.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import OperationType, Transaction
from app.services.canonical_dividend_aggregation_service import (
    load_received_entitlement_totals,
)
from app.services.fixed_income_valuation_service import (
    RENDA_FIXA_TYPE,
    get_fixed_income_totals,
    get_fixed_income_valuations,
)
from app.services.fx_service import get_usd_brl_today
from app.services.portfolio_service import (
    calc_raw_positions,
    enrich_with_prices,
    normalize_type,
)
from app.services.quotes_service import get_prices
from app.services.realized_pnl_projection_reader import load_realized_pnl_by_ticker
from app.services.rentabilidade_cash_flow import calculate_net_contributed
from app.services.rentabilidade_runtime_policy import utc_today

logger = logging.getLogger(__name__)

_CACHE_TTL = 300
_CACHE_PREFIX = "rent"
_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _cache_key(portfolio_id: int, suffix: str) -> str:
    return f"{_CACHE_PREFIX}:{portfolio_id}:{suffix}"


def _safe_pct(gain: Decimal, base: Decimal) -> float:
    if base and base > 0:
        return round(float(gain / base * 100), 4)
    return 0.0


async def _snapshot_at(
    db: AsyncSession,
    portfolio_id: int,
    target: date,
) -> PortfolioSnapshot | None:
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date <= target,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> PortfolioSnapshot | None:
    return await _snapshot_at(db, portfolio_id, utc_today())


async def _first_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> PortfolioSnapshot | None:
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _snapshot_before_today(
    db: AsyncSession,
    portfolio_id: int,
    snap_today: PortfolioSnapshot,
) -> PortfolioSnapshot | None:
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date < snap_today.snapshot_date,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _proventos_totals(
    db: AsyncSession,
    portfolio_id: int,
    *,
    as_of: date,
) -> tuple[float, float]:
    """Return canonical received dividends for 12 months and all time."""
    try:
        return await load_received_entitlement_totals(
            db,
            portfolio_id,
            cutoff=as_of - timedelta(days=365),
            as_of=as_of,
        )
    except Exception as exc:  # noqa: BLE001 - provider fallback preserves availability
        logger.warning("[rentabilidade] erro ao somar proventos: %s", exc)
        return 0.0, 0.0


async def _load_transactions_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> tuple[dict[str, list], list]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = list(result.scalars().all())
    by_ticker: dict[str, list] = {}
    for tx in txs:
        key = tx.ticker.upper()
        by_ticker.setdefault(key, []).append(tx)
    return by_ticker, txs


async def _load_net_contributed_up_to(
    db: AsyncSession,
    portfolio_id: int,
    up_to: date,
) -> float:
    """Return net contributed cash through ``up_to`` in BRL."""
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= up_to,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = result.scalars().all()
    return calculate_net_contributed(
        transactions,
        buy_operation=OperationType.buy,
        sell_operation=OperationType.sell,
        usd_asset_types=_USD_ASSET_TYPES,
        normalize_asset_type=normalize_type,
    )


async def _positions_enriched_without_rf(db: AsyncSession, portfolio_id: int) -> list[dict]:
    positions_raw = await calc_raw_positions(db, portfolio_id)
    positions_raw = [
        p
        for p in positions_raw
        if normalize_type(p.get("asset_type")) != RENDA_FIXA_TYPE
    ]
    fx_today = await get_usd_brl_today(db)
    price_items = [
        {"ticker": p["ticker"], "asset_type": p["asset_type"]}
        for p in positions_raw
    ]
    try:
        prices = await get_prices(price_items, db) if price_items else {}
    except Exception as exc:  # noqa: BLE001 - quote fallback preserves availability
        logger.error("[rentabilidade] erro ao buscar precos: %s", exc)
        prices = {}
    return enrich_with_prices(positions_raw, prices, fx_today=fx_today)


async def _kpis_from_realtime(db: AsyncSession, portfolio_id: int) -> dict:
    enriched = await _positions_enriched_without_rf(db, portfolio_id)
    rf_totals = await get_fixed_income_totals(db, portfolio_id)

    total_invested = sum(p["total_invested"] for p in enriched) + float(
        rf_totals["invested_amount"]
    )
    current_value = sum(
        (
            e["current_value"]
            if e["current_value"] is not None
            else e["total_invested"]
        )
        for e in enriched
    ) + float(rf_totals["current_value"])

    unrealized_pnl = current_value - total_invested
    realized_map = await load_realized_pnl_by_ticker(db, portfolio_id)
    realized_pnl = sum(realized_map.values())
    total_pnl = unrealized_pnl + realized_pnl

    today = utc_today()
    proventos_12m, proventos_total = await _proventos_totals(
        db,
        portfolio_id,
        as_of=today,
    )
    retorno_total_pct = (total_pnl / total_invested * 100) if total_invested else 0.0

    retorno_mes_pct = 0.0
    retorno_12m_pct = 0.0
    try:
        primeiro_dia_mes = today.replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes - timedelta(days=1)
        aporte_liquido_inicio_mes = await _load_net_contributed_up_to(
            db,
            portfolio_id,
            ultimo_dia_mes_anterior,
        )
        if aporte_liquido_inicio_mes > 0:
            retorno_mes_pct = round(
                (current_value - aporte_liquido_inicio_mes)
                / aporte_liquido_inicio_mes
                * 100,
                4,
            )
    except Exception as exc:  # noqa: BLE001 - legacy fallback must remain non-blocking
        logger.warning("[rentabilidade] fallback retorno_mes_pct falhou: %s", exc)

    try:
        inicio_12m = today - timedelta(days=365)
        aporte_liquido_inicio_12m = await _load_net_contributed_up_to(
            db,
            portfolio_id,
            inicio_12m,
        )
        if aporte_liquido_inicio_12m > 0:
            retorno_12m_pct = round(
                (current_value - aporte_liquido_inicio_12m)
                / aporte_liquido_inicio_12m
                * 100,
                4,
            )
    except Exception as exc:  # noqa: BLE001 - legacy fallback must remain non-blocking
        logger.warning("[rentabilidade] fallback retorno_12m_pct falhou: %s", exc)

    return {
        "patrimonio_atual": round(current_value, 2),
        "custo_total": round(total_invested, 2),
        "total_aportado": round(total_invested, 2),
        "ganho_nao_realizado": round(unrealized_pnl, 2),
        "ganho_realizado": round(realized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "retorno_total_pct": round(retorno_total_pct, 4),
        "retorno_dia_pct": 0.0,
        "retorno_mes_pct": retorno_mes_pct,
        "retorno_12m_pct": retorno_12m_pct,
        "retorno_desde_inicio_pct": round(retorno_total_pct, 4),
        "proventos_total": round(proventos_total, 2),
        "proventos_12m": round(proventos_12m, 2),
        "snapshot_date": None,
    }


def _ret_between(
    snap_end: PortfolioSnapshot,
    snap_start: PortfolioSnapshot | None,
) -> float:
    if snap_start is None:
        base = snap_end.invested_total
        if not base or base == 0:
            return 0.0
        gain = snap_end.unrealized_pnl + snap_end.realized_pnl
        return round(float(gain / base * 100), 4)

    gain_unrealized = snap_end.unrealized_pnl - snap_start.unrealized_pnl
    gain_realized = snap_end.realized_pnl - snap_start.realized_pnl
    total_gain = gain_unrealized + gain_realized

    base = snap_start.market_value or snap_start.invested_total
    if not base or base == 0:
        return 0.0
    return round(float(total_gain / base * 100), 4)


async def get_kpis(db: AsyncSession, portfolio_id: int) -> dict:
    cache_key = _cache_key(portfolio_id, "kpis")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    today = utc_today()
    snap_today = await _latest_snapshot(db, portfolio_id)

    if snap_today is None:
        payload = await _kpis_from_realtime(db, portfolio_id)
        return payload

    snap_yesterday = await _snapshot_before_today(db, portfolio_id, snap_today)
    snap_mes = await _snapshot_at(
        db,
        portfolio_id,
        today.replace(day=1) - timedelta(days=1),
    )
    snap_12m = await _snapshot_at(db, portfolio_id, today - timedelta(days=365))
    snap_first = await _first_snapshot(db, portfolio_id)

    proventos_12m, proventos_total = await _proventos_totals(
        db,
        portfolio_id,
        as_of=today,
    )

    payload = {
        "patrimonio_atual": round(float(snap_today.market_value or 0), 2),
        "custo_total": round(float(snap_today.cost_basis or 0), 2),
        "total_aportado": round(float(snap_today.invested_total or 0), 2),
        "ganho_nao_realizado": round(float(snap_today.unrealized_pnl or 0), 2),
        "ganho_realizado": round(float(snap_today.realized_pnl or 0), 2),
        "total_pnl": round(
            float(
                (snap_today.unrealized_pnl or 0)
                + (snap_today.realized_pnl or 0)
            ),
            2,
        ),
        "retorno_total_pct": _ret_between(snap_today, None),
        "retorno_dia_pct": _ret_between(snap_today, snap_yesterday),
        "retorno_mes_pct": _ret_between(snap_today, snap_mes),
        "retorno_12m_pct": _ret_between(snap_today, snap_12m),
        "retorno_desde_inicio_pct": _ret_between(
            snap_today,
            snap_first if snap_first != snap_today else None,
        ),
        "proventos_total": round(proventos_total, 2),
        "proventos_12m": round(proventos_12m, 2),
        "snapshot_date": (
            snap_today.snapshot_date.isoformat()
            if snap_today.snapshot_date
            else None
        ),
    }

    await cache_set(cache_key, payload, ttl=_CACHE_TTL)
    return payload


async def get_rentabilidade_por_ativo(
    db: AsyncSession,
    portfolio_id: int,
) -> list[dict]:
    cache_key = _cache_key(portfolio_id, "ativos")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    by_ticker, _ = await _load_transactions_by_ticker(db, portfolio_id)
    realized_map = await load_realized_pnl_by_ticker(db, portfolio_id)
    enriched = await _positions_enriched_without_rf(db, portfolio_id)

    open_tickers: set[str] = set()
    result: list[dict] = []

    for pos in enriched:
        ticker = str(pos.get("ticker") or pos.get("asset_code") or "").upper()
        if not ticker:
            continue
        open_tickers.add(ticker)

        total_invested = float(pos.get("total_invested") or 0)
        current_value = float(
            pos.get("current_value")
            if pos.get("current_value") is not None
            else total_invested
        )
        unrealized_pnl = current_value - total_invested
        unrealized_pct = (
            _safe_pct(
                Decimal(str(unrealized_pnl)),
                Decimal(str(total_invested)),
            )
            if total_invested
            else 0.0
        )
        realized_pnl = realized_map.get(ticker, 0.0)
        total_pnl = unrealized_pnl + realized_pnl
        total_pct = (
            _safe_pct(Decimal(str(total_pnl)), Decimal(str(total_invested)))
            if total_invested
            else 0.0
        )

        result.append(
            {
                "ticker": ticker,
                "asset_type": pos.get("asset_type"),
                "quantity": float(pos.get("quantity") or 0),
                "avg_price": float(pos.get("avg_price") or 0),
                "current_price": float(pos.get("current_price") or 0),
                "total_invested": round(total_invested, 2),
                "current_value": round(current_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pct": unrealized_pct,
                "realized_pnl": round(realized_pnl, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pct": total_pct,
                "total_pnl_pct": total_pct,
                "is_open": True,
            }
        )

    for idx, valuation in enumerate(
        await get_fixed_income_valuations(db, portfolio_id)
    ):
        result.append(
            {
                "ticker": valuation.key.name,
                "name": valuation.key.name,
                "asset_type": RENDA_FIXA_TYPE,
                "quantity": float(valuation.applications_count),
                "avg_price": float(valuation.invested_amount),
                "current_price": float(valuation.current_value),
                "total_invested": float(valuation.invested_amount),
                "current_value": float(valuation.current_value),
                "unrealized_pnl": float(valuation.income_amount),
                "unrealized_pct": float(valuation.income_pct),
                "realized_pnl": 0.0,
                "total_pnl": float(valuation.income_amount),
                "total_pct": float(valuation.income_pct),
                "total_pnl_pct": float(valuation.income_pct),
                "is_open": True,
                "applications_count": valuation.applications_count,
                "sort_index": idx,
            }
        )

    for ticker, realized_pnl in realized_map.items():
        if ticker in open_tickers or realized_pnl == 0.0:
            continue
        ticker_txs = by_ticker.get(ticker, [])
        total_invested = sum(
            float(tx.quantity or 0) * float(tx.price or 0)
            for tx in ticker_txs
            if tx.operation == OperationType.buy
        )
        asset_type = None
        if ticker_txs:
            at = ticker_txs[0].asset_type
            asset_type = at.value if hasattr(at, "value") else str(at)
        if normalize_type(asset_type) == RENDA_FIXA_TYPE:
            continue
        total_pct = (
            _safe_pct(Decimal(str(realized_pnl)), Decimal(str(total_invested)))
            if total_invested
            else 0.0
        )
        result.append(
            {
                "ticker": ticker,
                "asset_type": asset_type,
                "quantity": 0.0,
                "avg_price": 0.0,
                "current_price": 0.0,
                "total_invested": round(total_invested, 2),
                "current_value": 0.0,
                "unrealized_pnl": 0.0,
                "unrealized_pct": 0.0,
                "realized_pnl": round(realized_pnl, 2),
                "total_pnl": round(realized_pnl, 2),
                "total_pct": total_pct,
                "total_pnl_pct": total_pct,
                "is_open": False,
            }
        )

    result.sort(key=lambda item: (not item["is_open"], -abs(item["total_pnl"])))
    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result


async def get_rentabilidade_por_classe(
    db: AsyncSession,
    portfolio_id: int,
) -> list[dict]:
    cache_key = _cache_key(portfolio_id, "classes")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    ativos = await get_rentabilidade_por_ativo(db, portfolio_id)
    agg: dict[str, dict] = {}
    for item in ativos:
        asset_type = str(item.get("asset_type") or "OUTROS").upper()
        if asset_type not in agg:
            agg[asset_type] = {
                "asset_type": asset_type,
                "total_invested": 0.0,
                "current_value": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "count": 0,
            }
        agg[asset_type]["total_invested"] += item["total_invested"]
        agg[asset_type]["current_value"] += item["current_value"]
        agg[asset_type]["unrealized_pnl"] += item["unrealized_pnl"]
        agg[asset_type]["realized_pnl"] += item["realized_pnl"]
        agg[asset_type]["count"] += 1

    total_portfolio = sum(value["current_value"] for value in agg.values())
    result: list[dict] = []
    for asset_type, value in agg.items():
        total_pnl = value["unrealized_pnl"] + value["realized_pnl"]
        unrealized_pct = (
            _safe_pct(
                Decimal(str(value["unrealized_pnl"])),
                Decimal(str(value["total_invested"])),
            )
            if value["total_invested"]
            else 0.0
        )
        total_pct = (
            _safe_pct(
                Decimal(str(total_pnl)),
                Decimal(str(value["total_invested"])),
            )
            if value["total_invested"]
            else 0.0
        )
        allocation_pct = (
            round(value["current_value"] / total_portfolio * 100, 4)
            if total_portfolio
            else 0.0
        )
        result.append(
            {
                "asset_type": asset_type,
                "total_invested": round(value["total_invested"], 2),
                "current_value": round(value["current_value"], 2),
                "unrealized_pnl": round(value["unrealized_pnl"], 2),
                "unrealized_pct": unrealized_pct,
                "realized_pnl": round(value["realized_pnl"], 2),
                "total_pnl": round(total_pnl, 2),
                "total_pct": total_pct,
                "total_pnl_pct": total_pct,
                "allocation_pct": allocation_pct,
                "alocacao_pct": allocation_pct,
                "count": value["count"],
            }
        )

    result.sort(key=lambda item: -item["current_value"])
    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result
