"""
rentabilidade_service.py

Camada de agregacao sobre dados ja existentes (snapshots + posicoes).
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
from app.models.portfolio_position import PortfolioPosition
from app.models.asset import Asset
from app.services.quotes_service import get_current_price
from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_CACHE_TTL = 300
_PREFIX = "rent"


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
    """Soma de proventos pagos (status=RECEBIDO) opcionalmente a partir de 'since'."""
    try:
        from app.models.asset_dividend import AssetDividend
        q = (
            select(func.sum(AssetDividend.amount * AssetDividend.quantity))
            .where(
                AssetDividend.portfolio_id == portfolio_id,
                AssetDividend.status == "RECEBIDO",
            )
        )
        if since:
            q = q.where(AssetDividend.payment_date >= since)
        result = await db.execute(q)
        return Decimal(str(result.scalar_one() or 0))
    except Exception as e:
        logger.warning("[rentabilidade] erro ao somar proventos: %s", e)
        return Decimal("0")


# ─────────────────────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────────────────────

async def get_kpis(db: AsyncSession, portfolio_id: int) -> dict:
    """
    Retorna KPIs consolidados da carteira:
      - patrimonio_atual, custo_total, retorno_total_pct
      - retorno_mes_pct, retorno_12m_pct, retorno_desde_inicio_pct
      - ganho_nao_realizado, ganho_realizado, total_pnl
      - proventos_total, proventos_12m
    """
    cache_key = _key(portfolio_id, "kpis")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    today = date.today()

    snap_today = await _latest_snapshot(db, portfolio_id)
    snap_30d   = await _snapshot_at(db, portfolio_id, today - timedelta(days=30))
    snap_12m   = await _snapshot_at(db, portfolio_id, today - timedelta(days=365))
    snap_first = await _first_snapshot(db, portfolio_id)

    if snap_today is None:
        payload = {
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
        return payload

    def _ret_between(
        snap_end: PortfolioSnapshot,
        snap_start: Optional[PortfolioSnapshot],
    ) -> float:
        """
        Retorno simples entre dois snapshots:
          (market_value_end - market_value_start) / invested_start * 100
        Usa invested_total do snapshot inicial como base de capital.
        Se nao houver snapshot inicial usa o custo do snap_end.
        """
        if snap_start is None:
            return _safe_pct(snap_end.total_pnl, snap_end.invested_total)
        base = snap_start.market_value
        if not base or base == 0:
            return 0.0
        gain = snap_end.market_value - snap_start.market_value
        return round(float(gain / base * 100), 4)

    proventos_total = await _proventos_total(db, portfolio_id)
    proventos_12m   = await _proventos_total(db, portfolio_id, since=today - timedelta(days=365))

    ret_desde_inicio = (
        _safe_pct(snap_today.total_pnl, snap_today.invested_total)
        if snap_first is None
        else _ret_between(snap_today, snap_first)
    )

    payload = {
        "patrimonio_atual":          float(snap_today.market_value),
        "custo_total":               float(snap_today.cost_basis),
        "total_aportado":            float(snap_today.invested_total),
        "ganho_nao_realizado":       float(snap_today.unrealized_pnl),
        "ganho_realizado":           float(snap_today.realized_pnl),
        "total_pnl":                 float(snap_today.total_pnl),
        "retorno_total_pct":         float(snap_today.return_pct),
        "retorno_mes_pct":           _ret_between(snap_today, snap_30d),
        "retorno_12m_pct":           _ret_between(snap_today, snap_12m),
        "retorno_desde_inicio_pct":  ret_desde_inicio,
        "proventos_total":           float(proventos_total),
        "proventos_12m":             float(proventos_12m),
        "snapshot_date":             str(snap_today.snapshot_date),
    }

    await cache_set(cache_key, payload, ttl=_CACHE_TTL)
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Por ativo
# ─────────────────────────────────────────────────────────────────────────────

async def get_rentabilidade_por_ativo(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """
    Retorna rentabilidade por ativo incluindo:
      - Posicoes abertas: qty, custo, valor_atual, ganho nao-realizado
      - Posicoes zeradas: apenas lucro/prejuizo realizado
    """
    cache_key = _key(portfolio_id, "ativos")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Busca posicoes (abertas e zeradas com realized_profit != 0)
    pos_result = await db.execute(
        select(PortfolioPosition, Asset)
        .join(Asset, PortfolioPosition.asset_id == Asset.id)
        .where(PortfolioPosition.portfolio_id == portfolio_id)
    )
    rows = pos_result.all()

    items = []
    for pos, asset in rows:
        qty = float(pos.quantity)
        total_invested = float(pos.total_invested)
        avg_price = float(pos.average_price)
        realized = float(pos.realized_profit)

        asset_type_str = (
            asset.asset_type.value
            if hasattr(asset.asset_type, "value")
            else str(asset.asset_type)
        )

        if qty > 0:
            # Posicao aberta: busca cotacao atual
            current_price = await get_current_price(
                asset.ticker, asset_type=asset_type_str, db=db
            )
            if current_price:
                current_value = qty * current_price
            else:
                current_value = qty * avg_price
                logger.warning(
                    "[rentabilidade] sem cotacao para %s, usando preco medio",
                    asset.ticker,
                )
            unrealized = current_value - total_invested
            unrealized_pct = _safe_pct(
                Decimal(str(unrealized)), Decimal(str(total_invested))
            ) if total_invested > 0 else 0.0
            total_pnl = unrealized + realized
            total_invested_base = total_invested
        else:
            # Posicao zerada: sem valor atual
            current_value = 0.0
            unrealized = 0.0
            unrealized_pct = 0.0
            total_pnl = realized
            total_invested_base = 0.0

        if qty == 0 and realized == 0.0:
            continue

        total_pnl_pct = _safe_pct(
            Decimal(str(total_pnl)),
            Decimal(str(total_invested_base)) if total_invested_base > 0 else Decimal("1"),
        ) if total_invested_base > 0 else 0.0

        items.append({
            "ticker":           asset.ticker,
            "name":             asset.name,
            "asset_type":       asset_type_str,
            "quantity":         round(qty, 8),
            "avg_price":        round(avg_price, 4),
            "total_invested":   round(total_invested, 2),
            "current_value":    round(current_value, 2),
            "unrealized_pnl":   round(unrealized, 2),
            "unrealized_pct":   unrealized_pct,
            "realized_pnl":     round(realized, 2),
            "total_pnl":        round(total_pnl, 2),
            "total_pnl_pct":    total_pnl_pct,
            "is_open":          qty > 0,
        })

    items.sort(key=lambda x: abs(x["current_value"]), reverse=True)

    await cache_set(cache_key, items, ttl=_CACHE_TTL)
    return items


# ─────────────────────────────────────────────────────────────────────────────
# Por classe de ativo
# ─────────────────────────────────────────────────────────────────────────────

async def get_rentabilidade_por_classe(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """
    Agrega rentabilidade por classe de ativo (ACAO, FII, ETF_NACIONAL, etc.).
    Inclui percentual de alocacao sobre o patrimonio total.
    """
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
                "asset_type":     c,
                "total_invested": 0.0,
                "current_value":  0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl":   0.0,
                "total_pnl":      0.0,
                "count":          0,
            }
        g = classes[c]
        g["total_invested"] += a["total_invested"]
        g["current_value"]  += a["current_value"]
        g["unrealized_pnl"] += a["unrealized_pnl"]
        g["realized_pnl"]   += a["realized_pnl"]
        g["total_pnl"]       += a["total_pnl"]
        g["count"]           += 1

    patrimonio_total = sum(g["current_value"] for g in classes.values())

    result = []
    for c, g in classes.items():
        invested = g["total_invested"]
        pnl      = g["total_pnl"]
        result.append({
            "asset_type":       c,
            "total_invested":   round(g["total_invested"], 2),
            "current_value":    round(g["current_value"], 2),
            "unrealized_pnl":   round(g["unrealized_pnl"], 2),
            "realized_pnl":     round(g["realized_pnl"], 2),
            "total_pnl":        round(g["total_pnl"], 2),
            "total_pnl_pct":    _safe_pct(
                Decimal(str(pnl)),
                Decimal(str(invested)),
            ) if invested > 0 else 0.0,
            "alocacao_pct":     round(
                g["current_value"] / patrimonio_total * 100, 2
            ) if patrimonio_total > 0 else 0.0,
            "count":            g["count"],
        })

    result.sort(key=lambda x: x["current_value"], reverse=True)

    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result
