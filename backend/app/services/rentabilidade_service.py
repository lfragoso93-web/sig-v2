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
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction, OperationType
from app.services.quotes_service import get_prices
from app.services.portfolio_service import (
    calc_raw_positions,
    normalize_type,
    enrich_with_prices,
)
from app.services.fixed_income_valuation_service import (
    RENDA_FIXA_TYPE,
    get_fixed_income_totals,
    get_fixed_income_valuations,
)
from app.services.fx_service import get_usd_brl_today
from app.core.cache import cache_get, cache_set, cache_delete

logger = logging.getLogger(__name__)

_CACHE_TTL = 300
_PREFIX = "rent"
_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _key(portfolio_id: int, suffix: str) -> str:
    return f"{_PREFIX}:{portfolio_id}:{suffix}"


def _safe_pct(gain: Decimal, base: Decimal) -> float:
    if base and base > 0:
        return round(float(gain / base * 100), 4)
    return 0.0


async def flush_rentabilidade_cache(portfolio_id: int) -> None:
    for suffix in ("kpis", "ativos", "classes"):
        try:
            await cache_delete(_key(portfolio_id, suffix))
        except Exception:
            pass


async def _snapshot_at(
    db: AsyncSession,
    portfolio_id: int,
    target: date,
) -> Optional[PortfolioSnapshot]:
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


async def _latest_snapshot(db: AsyncSession, portfolio_id: int) -> Optional[PortfolioSnapshot]:
    return await _snapshot_at(db, portfolio_id, date.today())


async def _first_snapshot(db: AsyncSession, portfolio_id: int) -> Optional[PortfolioSnapshot]:
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
) -> Optional[PortfolioSnapshot]:
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


async def _proventos_total(
    db: AsyncSession,
    portfolio_id: int,
    since: Optional[date] = None,
) -> Decimal:
    try:
        from app.models.dividend import Dividend, DividendStatus

        value_col = func.coalesce(
            func.sum(
                func.coalesce(Dividend.total_value, Dividend.net_value, Decimal("0"))
            ),
            Decimal("0"),
        )
        q = (
            select(value_col)
            .where(
                Dividend.portfolio_id == portfolio_id,
                Dividend.status == DividendStatus.RECEBIDO,
            )
        )
        if since:
            q = q.where(Dividend.payment_date >= since)
        result = await db.execute(q)
        return Decimal(str(result.scalar_one() or 0))
    except Exception as e:
        logger.warning("[rentabilidade] erro ao somar proventos: %s", e)
        return Decimal("0")


def _calc_realized_from_txs(txs: list) -> dict[str, float]:
    qty_map: dict[str, float] = {}
    cost_map: dict[str, float] = {}
    realized: dict[str, float] = {}

    for tx in txs:
        ticker = tx.ticker.upper()
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)

        asset_type_raw = (
            tx.asset_type.value if hasattr(tx.asset_type, "value") else str(tx.asset_type or "")
        ).upper()
        if normalize_type(asset_type_raw) == RENDA_FIXA_TYPE:
            # Renda Fixa é tratada por aplicação/accrual, não por PnL realizado de cotas.
            continue

        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or normalize_type(asset_type_raw) in _USD_ASSET_TYPES
        )

        fx_rate = 1.0
        if is_usd:
            saved = getattr(tx, "fx_rate", None)
            if saved is not None and float(saved or 0) > 0:
                fx_rate = float(saved)

        price_brl = price * fx_rate
        fees_brl = fees * fx_rate

        if ticker not in qty_map:
            qty_map[ticker] = 0.0
            cost_map[ticker] = 0.0
            realized[ticker] = 0.0

        if tx.operation == OperationType.buy:
            qty_map[ticker] += qty
            cost_map[ticker] += qty * price_brl + fees_brl
        elif tx.operation == OperationType.sell:
            sold = min(qty, qty_map[ticker])
            if qty_map[ticker] > 0:
                avg_brl = cost_map[ticker] / qty_map[ticker]
                realized[ticker] += sold * (price_brl - avg_brl)
                cost_map[ticker] -= sold * avg_brl
            qty_map[ticker] = max(0.0, qty_map[ticker] - sold)
            cost_map[ticker] = max(0.0, cost_map[ticker])

    return realized


async def _get_realized_pnl_by_ticker(db: AsyncSession, portfolio_id: int) -> dict[str, float]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = list(result.scalars().all())
    return _calc_realized_from_txs(txs)


async def _load_transactions_by_ticker(db: AsyncSession, portfolio_id: int) -> tuple[dict[str, list], list]:
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


async def _calc_invested_up_to(db: AsyncSession, portfolio_id: int, up_to: date) -> float:
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= up_to,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()

    total = 0.0
    for tx in txs:
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        op = tx.operation
        asset_type = normalize_type(tx.asset_type)
        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or asset_type in _USD_ASSET_TYPES
        )
        fx_rate = 1.0
        if is_usd:
            saved = getattr(tx, "fx_rate", None)
            if saved is not None and float(saved or 0) > 0:
                fx_rate = float(saved)
        value = qty * price * fx_rate + (fees * fx_rate if op == OperationType.buy else 0)
        if op == OperationType.buy:
            total += value
        elif op == OperationType.sell:
            total -= qty * price * fx_rate
    return total


async def _positions_enriched_without_rf(db: AsyncSession, portfolio_id: int) -> list[dict]:
    positions_raw = await calc_raw_positions(db, portfolio_id)
    positions_raw = [p for p in positions_raw if normalize_type(p.get("asset_type")) != RENDA_FIXA_TYPE]
    fx_today = await get_usd_brl_today(db)
    price_items = [{"ticker": p["ticker"], "asset_type": p["asset_type"]} for p in positions_raw]
    try:
        prices = await get_prices(price_items, db) if price_items else {}
    except Exception as e:
        logger.error("[rentabilidade] erro ao buscar precos: %s", e)
        prices = {}
    return enrich_with_prices(positions_raw, prices, fx_today=fx_today)


async def _kpis_from_realtime(db: AsyncSession, portfolio_id: int) -> dict:
    enriched = await _positions_enriched_without_rf(db, portfolio_id)
    rf_totals = await get_fixed_income_totals(db, portfolio_id)

    total_invested = sum(p["total_invested"] for p in enriched) + float(rf_totals["invested_amount"])
    current_value = sum(
        (e["current_value"] if e["current_value"] is not None else e["total_invested"])
        for e in enriched
    ) + float(rf_totals["current_value"])

    unrealized_pnl = current_value - total_invested
    realized_map = await _get_realized_pnl_by_ticker(db, portfolio_id)
    realized_pnl = sum(realized_map.values())
    total_pnl = unrealized_pnl + realized_pnl

    today = date.today()
    proventos_total = float(await _proventos_total(db, portfolio_id))
    proventos_12m = float(await _proventos_total(db, portfolio_id, since=today - timedelta(days=365)))
    retorno_total_pct = (total_pnl / total_invested * 100) if total_invested else 0.0

    retorno_mes_pct = 0.0
    retorno_12m_pct = 0.0
    try:
        primeiro_dia_mes = today.replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes - timedelta(days=1)
        custo_inicio_mes = await _calc_invested_up_to(db, portfolio_id, ultimo_dia_mes_anterior)
        if custo_inicio_mes > 0:
            retorno_mes_pct = round((current_value - custo_inicio_mes) / custo_inicio_mes * 100, 4)
    except Exception as e:
        logger.warning("[rentabilidade] fallback retorno_mes_pct falhou: %s", e)

    try:
        inicio_12m = today - timedelta(days=365)
        custo_inicio_12m = await _calc_invested_up_to(db, portfolio_id, inicio_12m)
        if custo_inicio_12m > 0:
            retorno_12m_pct = round((current_value - custo_inicio_12m) / custo_inicio_12m * 100, 4)
    except Exception as e:
        logger.warning("[rentabilidade] fallback retorno_12m_pct falhou: %s", e)

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


def _ret_between(snap_end: PortfolioSnapshot, snap_start: Optional[PortfolioSnapshot]) -> float:
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
    cache_key = _key(portfolio_id, "kpis")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    today = date.today()
    snap_today = await _latest_snapshot(db, portfolio_id)

    # Para carteiras sem snapshot, calcula em realtime já incluindo RF por aplicação.
    if snap_today is None:
        payload = await _kpis_from_realtime(db, portfolio_id)
        return payload

    snap_yesterday = await _snapshot_before_today(db, portfolio_id, snap_today)
    snap_mes = await _snapshot_at(db, portfolio_id, today.replace(day=1) - timedelta(days=1))
    snap_12m = await _snapshot_at(db, portfolio_id, today - timedelta(days=365))
    snap_first = await _first_snapshot(db, portfolio_id)

    proventos_total = float(await _proventos_total(db, portfolio_id))
    proventos_12m = float(await _proventos_total(db, portfolio_id, since=today - timedelta(days=365)))

    payload = {
        "patrimonio_atual": round(float(snap_today.market_value or 0), 2),
        "custo_total": round(float(snap_today.cost_basis or 0), 2),
        "total_aportado": round(float(snap_today.invested_total or 0), 2),
        "ganho_nao_realizado": round(float(snap_today.unrealized_pnl or 0), 2),
        "ganho_realizado": round(float(snap_today.realized_pnl or 0), 2),
        "total_pnl": round(float((snap_today.unrealized_pnl or 0) + (snap_today.realized_pnl or 0)), 2),
        "retorno_total_pct": _ret_between(snap_today, None),
        "retorno_dia_pct": _ret_between(snap_today, snap_yesterday),
        "retorno_mes_pct": _ret_between(snap_today, snap_mes),
        "retorno_12m_pct": _ret_between(snap_today, snap_12m),
        "retorno_desde_inicio_pct": _ret_between(snap_today, snap_first if snap_first != snap_today else None),
        "proventos_total": round(proventos_total, 2),
        "proventos_12m": round(proventos_12m, 2),
        "snapshot_date": snap_today.snapshot_date.isoformat() if snap_today.snapshot_date else None,
    }

    await cache_set(cache_key, payload, ttl=_CACHE_TTL)
    return payload


async def get_rentabilidade_por_ativo(db: AsyncSession, portfolio_id: int) -> list[dict]:
    cache_key = _key(portfolio_id, "ativos")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    by_ticker, flat_txs = await _load_transactions_by_ticker(db, portfolio_id)
    realized_map = _calc_realized_from_txs(flat_txs)
    enriched = await _positions_enriched_without_rf(db, portfolio_id)

    open_tickers: set[str] = set()
    result: list[dict] = []

    for pos in enriched:
        ticker = str(pos.get("ticker") or pos.get("asset_code") or "").upper()
        if not ticker:
            continue
        open_tickers.add(ticker)

        total_invested = float(pos.get("total_invested") or 0)
        current_value = float(pos.get("current_value") if pos.get("current_value") is not None else total_invested)
        unrealized_pnl = current_value - total_invested
        unrealized_pct = _safe_pct(Decimal(str(unrealized_pnl)), Decimal(str(total_invested))) if total_invested else 0.0
        realized_pnl = realized_map.get(ticker, 0.0)
        total_pnl = unrealized_pnl + realized_pnl
        total_pct = _safe_pct(Decimal(str(total_pnl)), Decimal(str(total_invested))) if total_invested else 0.0

        result.append({
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
        })

    for idx, v in enumerate(await get_fixed_income_valuations(db, portfolio_id)):
        result.append({
            "ticker": v.key.name,
            "name": v.key.name,
            "asset_type": RENDA_FIXA_TYPE,
            "quantity": float(v.applications_count),
            "avg_price": float(v.invested_amount),
            "current_price": float(v.current_value),
            "total_invested": float(v.invested_amount),
            "current_value": float(v.current_value),
            "unrealized_pnl": float(v.income_amount),
            "unrealized_pct": float(v.income_pct),
            "realized_pnl": 0.0,
            "total_pnl": float(v.income_amount),
            "total_pct": float(v.income_pct),
            "total_pnl_pct": float(v.income_pct),
            "is_open": True,
            "applications_count": v.applications_count,
            "sort_index": idx,
        })

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
        total_pct = _safe_pct(Decimal(str(realized_pnl)), Decimal(str(total_invested))) if total_invested else 0.0
        result.append({
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
        })

    result.sort(key=lambda x: (not x["is_open"], -abs(x["total_pnl"])))
    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result


async def get_rentabilidade_por_classe(db: AsyncSession, portfolio_id: int) -> list[dict]:
    cache_key = _key(portfolio_id, "classes")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    ativos = await get_rentabilidade_por_ativo(db, portfolio_id)
    agg: dict[str, dict] = {}
    for item in ativos:
        at = str(item.get("asset_type") or "OUTROS").upper()
        if at not in agg:
            agg[at] = {
                "asset_type": at,
                "total_invested": 0.0,
                "current_value": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "count": 0,
            }
        agg[at]["total_invested"] += item["total_invested"]
        agg[at]["current_value"] += item["current_value"]
        agg[at]["unrealized_pnl"] += item["unrealized_pnl"]
        agg[at]["realized_pnl"] += item["realized_pnl"]
        agg[at]["count"] += 1

    total_portfolio = sum(v["current_value"] for v in agg.values())
    result: list[dict] = []
    for at, v in agg.items():
        total_pnl = v["unrealized_pnl"] + v["realized_pnl"]
        unrealized_pct = _safe_pct(Decimal(str(v["unrealized_pnl"])), Decimal(str(v["total_invested"]))) if v["total_invested"] else 0.0
        total_pct = _safe_pct(Decimal(str(total_pnl)), Decimal(str(v["total_invested"]))) if v["total_invested"] else 0.0
        allocation_pct = round(v["current_value"] / total_portfolio * 100, 4) if total_portfolio else 0.0
        result.append({
            "asset_type": at,
            "total_invested": round(v["total_invested"], 2),
            "current_value": round(v["current_value"], 2),
            "unrealized_pnl": round(v["unrealized_pnl"], 2),
            "unrealized_pct": unrealized_pct,
            "realized_pnl": round(v["realized_pnl"], 2),
            "total_pnl": round(total_pnl, 2),
            "total_pct": total_pct,
            "total_pnl_pct": total_pct,
            "allocation_pct": allocation_pct,
            "alocacao_pct": allocation_pct,
            "count": v["count"],
        })

    result.sort(key=lambda x: -x["current_value"])
    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result
