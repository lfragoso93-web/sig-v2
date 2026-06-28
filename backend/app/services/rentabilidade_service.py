"""
rentabilidade_service.py

Camada de agregacao sobre dados ja existentes (snapshots + transacoes).
Nao recalcula market_value nem cost_basis — delega ao portfolio_snapshot_service.

Endpoints servidos:
  GET /portfolios/{id}/rentabilidade/kpis
  GET /portfolios/{id}/rentabilidade/ativos
  GET /portfolios/{id}/rentabilidade/classes

Cache Redis (TTL 5 min, prefixo `rent:`):
  Degradacao gracosa se Redis indisponivel.
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
from app.models.asset import Asset
from app.services.quotes_service import get_prices
from app.services.portfolio_service import (
    calc_raw_positions,
    normalize_type,
    enrich_with_prices,
    _fetch_prices_batch,
)
from app.services.fx_service import get_usd_brl_today
from app.services.rf_calc_service import enrich_rf_positions
from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_CACHE_TTL = 300
_PREFIX = "rent"

# Tipos de ativos cotados em USD
_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}

# Tipos de RF sem cotação de mercado — usam rf_calc_service
_RF_TYPES = {"RENDA_FIXA"}


def _key(portfolio_id: int, suffix: str) -> str:
    return f"{_PREFIX}:{portfolio_id}:{suffix}"


def _safe_pct(gain: Decimal, base: Decimal) -> float:
    if base and base > 0:
        return round(float(gain / base * 100), 4)
    return 0.0


async def _snapshot_at(
    db: AsyncSession,
    portfolio_id: int,
    target: date,
) -> Optional[PortfolioSnapshot]:
    """Retorna o snapshot mais proximo (<=) de target."""
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
) -> Optional[PortfolioSnapshot]:
    return await _snapshot_at(db, portfolio_id, date.today())


async def _first_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> Optional[PortfolioSnapshot]:
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _proventos_total(
    db: AsyncSession,
    portfolio_id: int,
    since: Optional[date] = None,
) -> Decimal:
    """
    Soma de proventos recebidos da carteira.

    Usa a tabela `dividends` (Dividend), que tem vinculo direto com portfolio_id
    e os campos corretos: total_value / total_received / status.

    Ordem de preferencia para o valor:
      1. total_value   (campo principal, preenchido pelo backfill moderno)
      2. total_received (campo legado do backfill antigo)
    """
    try:
        from app.models.dividend import Dividend, DividendStatus

        # Soma total_value para registros com status RECEBIDO
        value_col = func.coalesce(
            func.sum(
                func.coalesce(Dividend.total_value, Dividend.total_received, Decimal("0"))
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
            q = q.where(
                Dividend.payment_date >= since,
            )
        result = await db.execute(q)
        return Decimal(str(result.scalar_one() or 0))
    except Exception as e:
        logger.warning("[rentabilidade] erro ao somar proventos: %s", e)
        return Decimal("0")


async def _get_realized_pnl_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, float]:
    """
    Calcula o lucro realizado acumulado por ticker a partir das transacoes de venda.
    Usa media ponderada movel (FIFO) para apurar custo na hora da venda.

    Para ativos USD (STOCK/ETF_INTERNACIONAL):
      - O custo medio e acumulado em BRL (via fx_rate da transacao de compra).
      - O preco de venda tambem e convertido para BRL usando fx_rate da venda.
      - Isso garante que o realized_pnl seja sempre em BRL.
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()

    qty_map: dict[str, float] = {}
    cost_map: dict[str, float] = {}  # sempre em BRL
    realized: dict[str, float] = {}
    is_usd_map: dict[str, bool] = {}

    for tx in txs:
        ticker = tx.ticker.upper()
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)

        # Determina se ativo e cotado em USD
        asset_type_raw = (
            tx.asset_type.value if hasattr(tx.asset_type, "value") else str(tx.asset_type or "")
        ).upper()
        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or normalize_type(asset_type_raw) in _USD_ASSET_TYPES
        )

        # Obtem fx_rate salvo na transacao (fallback 1.0 para BRL)
        fx_rate = 1.0
        if is_usd:
            saved = getattr(tx, "fx_rate", None)
            if saved is not None and float(saved or 0) > 0:
                fx_rate = float(saved)

        price_brl = price * fx_rate
        fees_brl = fees * fx_rate

        if ticker not in qty_map:
            qty_map[ticker] = 0.0
            cost_map[ticker] = 0.0  # BRL
            realized[ticker] = 0.0
            is_usd_map[ticker] = is_usd

        if tx.operation == OperationType.buy:
            qty_map[ticker] += qty
            cost_map[ticker] += qty * price_brl + fees_brl
        elif tx.operation == OperationType.sell:
            sold = min(qty, qty_map[ticker])
            if qty_map[ticker] > 0:
                avg_brl = cost_map[ticker] / qty_map[ticker]  # custo medio em BRL
                # preco de venda tambem em BRL
                realized[ticker] += sold * (price_brl - avg_brl)
                cost_map[ticker] -= sold * avg_brl
            qty_map[ticker] = max(0.0, qty_map[ticker] - sold)
            cost_map[ticker] = max(0.0, cost_map[ticker])

    return realized


async def _load_transactions_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, list]:
    """Carrega todas as transactions da carteira agrupadas por ticker."""
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()
    by_ticker: dict[str, list] = {}
    for tx in txs:
        key = tx.ticker.upper()
        by_ticker.setdefault(key, []).append(tx)
    return by_ticker


async def _kpis_from_realtime(db: AsyncSession, portfolio_id: int) -> dict:
    """
    Fallback: calcula KPIs diretamente das transacoes + cotacoes atuais.
    Usado quando nao existe snapshot para a carteira (ex.: carteira nova).
    """
    logger.info(
        "[rentabilidade] sem snapshot para portfolio=%s — calculando em tempo real",
        portfolio_id,
    )
    positions_raw = await calc_raw_positions(db, portfolio_id)
    if not positions_raw:
        return {
            "patrimonio_atual": 0.0,
            "custo_total": 0.0,
            "total_aportado": 0.0,
            "ganho_nao_realizado": 0.0,
            "ganho_realizado": 0.0,
            "total_pnl": 0.0,
            "retorno_total_pct": 0.0,
            "retorno_mes_pct": 0.0,
            "retorno_12m_pct": 0.0,
            "retorno_desde_inicio_pct": 0.0,
            "proventos_total": 0.0,
            "proventos_12m": 0.0,
            "snapshot_date": None,
        }

    fx_today = await get_usd_brl_today(db)
    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices, fx_today=fx_today)

    total_invested = sum(p["total_invested"] for p in enriched)
    current_value = sum(
        (e["current_value"] if e["current_value"] is not None else e["total_invested"])
        for e in enriched
    )
    unrealized_pnl = current_value - total_invested

    realized_map = await _get_realized_pnl_by_ticker(db, portfolio_id)
    realized_pnl = sum(realized_map.values())
    total_pnl = unrealized_pnl + realized_pnl

    from datetime import timedelta
    today = date.today()
    proventos_total = float(await _proventos_total(db, portfolio_id))
    proventos_12m = float(await _proventos_total(db, portfolio_id, since=today - timedelta(days=365)))

    # Retorno sobre custo das posicoes abertas (base correta sem distorcao de aportes)
    retorno_total_pct = (total_pnl / total_invested * 100) if total_invested else 0.0

    return {
        "patrimonio_atual": round(current_value, 2),
        "custo_total": round(total_invested, 2),
        "total_aportado": round(total_invested, 2),
        "ganho_nao_realizado": round(unrealized_pnl, 2),
        "ganho_realizado": round(realized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "retorno_total_pct": round(retorno_total_pct, 4),
        "retorno_mes_pct": 0.0,
        "retorno_12m_pct": 0.0,
        "retorno_desde_inicio_pct": round(retorno_total_pct, 4),
        "proventos_total": round(proventos_total, 2),
        "proventos_12m": round(proventos_12m, 2),
        "snapshot_date": None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# KPIs
# ──────────────────────────────────────────────────────────────────────────────

def _ret_between(
    snap_end: PortfolioSnapshot,
    snap_start: Optional[PortfolioSnapshot],
) -> float:
    """
    Calcula retorno percentual entre dois snapshots usando cost_basis como base.
    """
    if snap_start is None:
        base = snap_end.cost_basis
        if not base or base == 0:
            return 0.0
        gain = snap_end.unrealized_pnl + snap_end.realized_pnl
        return round(float(gain / base * 100), 4)

    gain_unrealized = snap_end.unrealized_pnl - snap_start.unrealized_pnl
    gain_realized = snap_end.realized_pnl - snap_start.realized_pnl
    total_gain = gain_unrealized + gain_realized

    base = snap_start.cost_basis
    if not base or base == 0:
        base = snap_end.cost_basis
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

    if snap_today is None:
        payload = await _kpis_from_realtime(db, portfolio_id)
        return payload

    snap_30d = await _snapshot_at(db, portfolio_id, today - timedelta(days=30))
    snap_12m = await _snapshot_at(db, portfolio_id, today - timedelta(days=365))
    snap_first = await _first_snapshot(db, portfolio_id)

    proventos_total = await _proventos_total(db, portfolio_id)
    proventos_12m = await _proventos_total(db, portfolio_id, since=today - timedelta(days=365))

    ret_total = float(snap_today.return_pct)
    ret_desde_inicio = _ret_between(snap_today, snap_first)

    payload = {
        "patrimonio_atual": float(snap_today.market_value),
        "custo_total": float(snap_today.cost_basis),
        "total_aportado": float(snap_today.invested_total),
        "ganho_nao_realizado": float(snap_today.unrealized_pnl),
        "ganho_realizado": float(snap_today.realized_pnl),
        "total_pnl": float(snap_today.total_pnl),
        "retorno_total_pct": ret_total,
        "retorno_mes_pct": _ret_between(snap_today, snap_30d),
        "retorno_12m_pct": _ret_between(snap_today, snap_12m),
        "retorno_desde_inicio_pct": ret_desde_inicio,
        "proventos_total": float(proventos_total),
        "proventos_12m": float(proventos_12m),
        "snapshot_date": str(snap_today.snapshot_date),
    }

    await cache_set(cache_key, payload, ttl=_CACHE_TTL)
    return payload


# ──────────────────────────────────────────────────────────────────────────────
# Por ativo
# ──────────────────────────────────────────────────────────────────────────────

async def get_rentabilidade_por_ativo(db: AsyncSession, portfolio_id: int) -> list[dict]:
    cache_key = _key(portfolio_id, "ativos")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    positions_raw = await calc_raw_positions(db, portfolio_id)
    realized_map = await _get_realized_pnl_by_ticker(db, portfolio_id)

    prices_input = [
        {"ticker": p["ticker"], "asset_type": p["asset_type"]}
        for p in positions_raw
    ]
    prices_map: dict[str, float] = {}
    if prices_input:
        try:
            prices_map = await get_prices(prices_input, db)
        except Exception as e:
            logger.error("[rentabilidade] erro ao buscar cotacoes: %s", e)

    # ── Calcula current_value estimado para posicoes de RENDA_FIXA ──────────
    txs_by_ticker = await _load_transactions_by_ticker(db, portfolio_id)
    rf_values: dict[str, float] = {}
    try:
        rf_values = await enrich_rf_positions(positions_raw, txs_by_ticker)
    except Exception as e:
        logger.warning("[rentabilidade] enrich_rf_positions falhou: %s", e)
    # ────────────────────────────────────────────────────────────────────────

    tickers_all = list({p["ticker"] for p in positions_raw} | set(realized_map.keys()))
    asset_names: dict[str, str] = {}
    asset_types_db: dict[str, str] = {}
    if tickers_all:
        res = await db.execute(
            select(Asset.ticker, Asset.name, Asset.asset_type)
            .where(Asset.ticker.in_(tickers_all))
        )
        for row in res.all():
            asset_names[row.ticker] = row.name or row.ticker
            asset_types_db[row.ticker] = (
                row.asset_type.value
                if hasattr(row.asset_type, "value")
                else str(row.asset_type)
            )

    items: list[dict] = []

    open_tickers: set[str] = set()
    for p in positions_raw:
        ticker = p["ticker"]
        open_tickers.add(ticker)
        asset_type = asset_types_db.get(ticker) or normalize_type(p.get("asset_type", ""))
        qty = p["quantity"]
        total_invested = p["total_invested"]
        avg_price = p["avg_price"]
        realized = realized_map.get(ticker, 0.0)

        current_price = prices_map.get(ticker)

        is_usd = p.get("is_usd", False)
        if is_usd and current_price is not None:
            try:
                fx_today = await get_usd_brl_today(db)
                current_price = current_price * fx_today
            except Exception:
                pass

        # ── RF: usa current_value calculado por rf_calc_service ─────────────
        if asset_type in _RF_TYPES and ticker in rf_values:
            current_value = rf_values[ticker]
        elif current_price:
            current_value = qty * current_price
        else:
            current_value = qty * avg_price
            if asset_type not in _RF_TYPES:
                logger.warning(
                    "[rentabilidade] sem cotacao para %s, usando preco medio", ticker
                )
        # ────────────────────────────────────────────────────────────────────

        unrealized = current_value - total_invested
        unrealized_pct = _safe_pct(
            Decimal(str(unrealized)), Decimal(str(total_invested))
        ) if total_invested > 0 else 0.0
        total_pnl = unrealized + realized
        total_pnl_pct = _safe_pct(
            Decimal(str(total_pnl)), Decimal(str(total_invested))
        ) if total_invested > 0 else 0.0

        items.append({
            "ticker": ticker,
            "name": asset_names.get(ticker, ticker),
            "asset_type": asset_type,
            "quantity": round(qty, 8),
            "avg_price": round(avg_price, 4),
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "unrealized_pnl": round(unrealized, 2),
            "unrealized_pct": unrealized_pct,
            "realized_pnl": round(realized, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": total_pnl_pct,
            "is_open": True,
        })

    for ticker, realized in realized_map.items():
        if ticker in open_tickers:
            continue
        if realized == 0.0:
            continue
        asset_type = asset_types_db.get(ticker, "OUTRO")
        items.append({
            "ticker": ticker,
            "name": asset_names.get(ticker, ticker),
            "asset_type": asset_type,
            "quantity": 0.0,
            "avg_price": 0.0,
            "total_invested": 0.0,
            "current_value": 0.0,
            "unrealized_pnl": 0.0,
            "unrealized_pct": 0.0,
            "realized_pnl": round(realized, 2),
            "total_pnl": round(realized, 2),
            "total_pnl_pct": 0.0,
            "is_open": False,
        })

    items.sort(key=lambda x: abs(x["current_value"]), reverse=True)

    await cache_set(cache_key, items, ttl=_CACHE_TTL)
    return items


# ──────────────────────────────────────────────────────────────────────────────
# Por classe de ativo
# ──────────────────────────────────────────────────────────────────────────────

async def get_rentabilidade_por_classe(db: AsyncSession, portfolio_id: int) -> list[dict]:
    cache_key = _key(portfolio_id, "classes")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    ativos = await get_rentabilidade_por_ativo(db, portfolio_id)

    classes: dict[str, dict] = {}
    for a in ativos:
        c = a["asset_type"]
        if c not in classes:
            classes[c] = {
                "asset_type": c,
                "total_invested": 0.0,
                "current_value": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "total_pnl": 0.0,
                "count": 0,
            }
        g = classes[c]
        g["total_invested"] += a["total_invested"]
        g["current_value"] += a["current_value"]
        g["unrealized_pnl"] += a["unrealized_pnl"]
        g["realized_pnl"] += a["realized_pnl"]
        g["total_pnl"] += a["total_pnl"]
        g["count"] += 1

    patrimonio_total = sum(g["current_value"] for g in classes.values())

    result = []
    for c, g in classes.items():
        invested = g["total_invested"]
        pnl = g["total_pnl"]
        result.append({
            "asset_type": c,
            "total_invested": round(g["total_invested"], 2),
            "current_value": round(g["current_value"], 2),
            "unrealized_pnl": round(g["unrealized_pnl"], 2),
            "realized_pnl": round(g["realized_pnl"], 2),
            "total_pnl": round(g["total_pnl"], 2),
            "total_pnl_pct": _safe_pct(
                Decimal(str(pnl)),
                Decimal(str(invested)),
            ) if invested > 0 else 0.0,
            "alocacao_pct": round(
                g["current_value"] / patrimonio_total * 100, 2
            ) if patrimonio_total > 0 else 0.0,
            "count": g["count"],
        })

    result.sort(key=lambda x: x["current_value"], reverse=True)

    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result
