"""Fonte canônica para os KPIs consolidados de uma carteira.

Patrimônio, investido, resultado e cobertura usam valuation intradiário. TWR e
metadados de performance usam o último snapshot fechado. Proventos usam apenas
valores monetários efetivamente recebidos, pela data de pagamento.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.models.asset import Asset
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.schemas.portfolio_summary import PortfolioSummaryResponse
from app.services.dividend_aggregation_service import sum_received_dividends
from app.services.fixed_income_valuation_service import get_fixed_income_totals
from app.services.fx_service import get_usd_brl_today
from app.services.portfolio_reconciliation_service import reconcile_snapshot_summary
from app.services.portfolio_service import (
    _MARKET_PRICE_TYPES,
    _cache_key,
    _non_fixed_income_enriched,
    get_portfolio,
)
from app.services.realized_pnl_service import get_realized_pnl

logger = logging.getLogger(__name__)
_CACHE_TTL = 120
_SUMMARY_VERSION = "summary.v2"


@dataclass(frozen=True, slots=True)
class PortfolioSummaryInput:
    total_invested: float
    current_value: float
    dividends_12m: float = 0.0
    total_dividends: float = 0.0
    realized_pnl: float = 0.0
    has_partial_prices: bool = False
    assets_without_price: tuple[str, ...] = ()
    usd_brl_rate: float = 1.0
    accumulated_twr_pct: float | None = None
    daily_twr_pct: float | None = None


def build_portfolio_summary(data: PortfolioSummaryInput) -> dict:
    """Monta exclusivamente os campos financeiros canônicos do Resumo."""
    total_invested = float(data.total_invested)
    current_value = float(data.current_value)
    unrealized_pnl = current_value - total_invested
    variation_pct = unrealized_pnl / total_invested * 100 if total_invested else 0.0
    realized_pnl = float(data.realized_pnl)
    total_dividends = float(data.total_dividends)
    total_profit = unrealized_pnl + realized_pnl + total_dividends
    fallback_return_pct = total_profit / total_invested * 100 if total_invested else 0.0
    total_return_pct = (
        float(data.accumulated_twr_pct)
        if data.accumulated_twr_pct is not None
        else fallback_return_pct
    )

    return {
        "total_patrimonio": round(current_value, 2),
        "total_investido": round(total_invested, 2),
        "lucro_total": round(total_profit, 2),
        "variacao_valor": round(unrealized_pnl, 2),
        "variacao_percentual": round(variation_pct, 4),
        "rentabilidade_total": round(total_return_pct, 4),
        "rentabilidade_acumulada": round(total_return_pct, 4),
        "rentabilidade_diaria": (
            round(float(data.daily_twr_pct), 6)
            if data.daily_twr_pct is not None
            else None
        ),
        "rentabilidade_source": (
            "snapshot_twr" if data.accumulated_twr_pct is not None else "valuation_fallback"
        ),
        "dividendos_recebidos_12m": round(float(data.dividends_12m), 2),
        "total_proventos": round(total_dividends, 2),
        "ganho_nao_realizado": round(unrealized_pnl, 2),
        "ganho_realizado": round(realized_pnl, 2),
        "has_partial_prices": bool(data.has_partial_prices),
        "assets_without_price": list(data.assets_without_price),
        "usd_brl_rate": round(float(data.usd_brl_rate), 4),
    }


def _validate_summary_contract(payload: dict) -> dict:
    """Rejeita campos extras, ausentes ou tipos incompatíveis antes da resposta."""
    return PortfolioSummaryResponse.model_validate(payload).model_dump()


async def _get_latest_snapshot(db: AsyncSession, portfolio_id: int) -> PortfolioSnapshot | None:
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _get_intraday_valuation(db: AsyncSession, portfolio_id: int) -> dict:
    enriched = await _non_fixed_income_enriched(db, portfolio_id)
    fixed_income = await get_fixed_income_totals(db, portfolio_id)
    total_invested = sum(position["total_invested"] for position in enriched) + float(
        fixed_income["invested_amount"]
    )
    current_value = sum(
        position["current_value"]
        if position["current_value"] is not None
        else position["total_invested"]
        for position in enriched
    ) + float(fixed_income["current_value"])

    price_eligible_positions = [
        position
        for position in enriched
        if position["asset_type"] in _MARKET_PRICE_TYPES
    ]
    assets_without_price = tuple(
        position["ticker"]
        for position in price_eligible_positions
        if position.get("current_price") is None
    )
    price_assets_total = len(price_eligible_positions)
    price_assets_covered = price_assets_total - len(assets_without_price)
    price_coverage_pct = (
        price_assets_covered / price_assets_total * 100
        if price_assets_total
        else 100.0
    )

    tickers = [position["ticker"] for position in enriched]
    valuation_updated_at = None
    if tickers:
        result = await db.execute(
            select(func.max(Asset.last_price_updated_at)).where(Asset.ticker.in_(tickers))
        )
        updated_at = result.scalar_one_or_none()
        valuation_updated_at = updated_at.isoformat() if updated_at else None
    return {
        "total_invested": total_invested,
        "current_value": current_value,
        "assets_without_price": assets_without_price,
        "price_assets_total": price_assets_total,
        "price_assets_covered": price_assets_covered,
        "price_coverage_pct": round(price_coverage_pct, 2),
        "valuation_updated_at": valuation_updated_at,
    }


async def _get_received_dividend_totals(db: AsyncSession, portfolio_id: int) -> tuple[float, float]:
    today = date.today()
    cutoff_12m = (datetime.now(timezone.utc) - timedelta(days=365)).date()
    total_12m = await sum_received_dividends(
        db,
        portfolio_id,
        cutoff=cutoff_12m,
        as_of=today,
    )
    total = await sum_received_dividends(db, portfolio_id, as_of=today)
    return total_12m, total


def _quality_metadata(valuation: dict) -> dict:
    assets_without_price = tuple(valuation.get("assets_without_price", ()))
    total = int(valuation.get("price_assets_total", len(assets_without_price)))
    covered = int(valuation.get("price_assets_covered", max(0, total - len(assets_without_price))))
    coverage = valuation.get("price_coverage_pct")
    if coverage is None:
        coverage = covered / total * 100 if total else 100.0
    return {
        "price_assets_total": total,
        "price_assets_covered": covered,
        "price_coverage_pct": round(float(coverage), 2),
    }


async def _build_summary_from_latest_snapshot(
    db: AsyncSession,
    portfolio_id: int,
    snapshot: PortfolioSnapshot,
) -> dict:
    valuation = await _get_intraday_valuation(db, portfolio_id)
    dividends_12m, total_dividends = await _get_received_dividend_totals(db, portfolio_id)
    realized_pnl = await get_realized_pnl(db, portfolio_id)

    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=valuation["total_invested"],
            current_value=valuation["current_value"],
            dividends_12m=dividends_12m,
            total_dividends=total_dividends,
            realized_pnl=realized_pnl,
            has_partial_prices=bool(valuation["assets_without_price"]),
            assets_without_price=valuation["assets_without_price"],
            usd_brl_rate=await get_usd_brl_today(db),
            accumulated_twr_pct=float(snapshot.accumulated_return_pct),
            daily_twr_pct=float(snapshot.daily_return_pct),
        )
    )
    summary.update(
        {
            "summary_version": _SUMMARY_VERSION,
            "snapshot_id": getattr(snapshot, "id", None),
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "performance_as_of": snapshot.snapshot_date.isoformat(),
            "proventos_as_of": date.today().isoformat(),
            "proventos_source": "received_cash_dividends",
            "valuation_mode": "intraday",
            "valuation_updated_at": valuation["valuation_updated_at"],
            "summary_source": "intraday_valuation_with_snapshot_twr",
            "return_is_estimated": bool(snapshot.return_is_estimated),
            **_quality_metadata(valuation),
        }
    )
    reconciliation = reconcile_snapshot_summary(
        snapshot,
        summary,
        valuation_mode="intraday",
    )
    summary["reconciliation"] = reconciliation
    summary["is_reconciled"] = reconciliation["is_reconciled"]
    if not reconciliation["is_reconciled"]:
        logger.error(
            "[summary_reconciliation] portfolio=%s snapshot_date=%s failed_fields=%s checks=%s",
            portfolio_id,
            snapshot.snapshot_date,
            reconciliation["failed_fields"],
            reconciliation["checks"],
        )
    return summary


async def _build_summary_from_valuation_fallback(db: AsyncSession, portfolio_id: int) -> dict:
    valuation = await _get_intraday_valuation(db, portfolio_id)
    dividends_12m, total_dividends = await _get_received_dividend_totals(db, portfolio_id)
    realized_pnl = await get_realized_pnl(db, portfolio_id)
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=valuation["total_invested"],
            current_value=valuation["current_value"],
            dividends_12m=dividends_12m,
            total_dividends=total_dividends,
            realized_pnl=realized_pnl,
            has_partial_prices=bool(valuation["assets_without_price"]),
            assets_without_price=valuation["assets_without_price"],
            usd_brl_rate=await get_usd_brl_today(db),
        )
    )
    summary.update(
        {
            "summary_version": _SUMMARY_VERSION,
            "snapshot_id": None,
            "snapshot_date": None,
            "performance_as_of": None,
            "proventos_as_of": date.today().isoformat(),
            "proventos_source": "received_cash_dividends",
            "valuation_mode": "intraday",
            "valuation_updated_at": valuation["valuation_updated_at"],
            "summary_source": "valuation_fallback",
            "return_is_estimated": True,
            "is_reconciled": None,
            "reconciliation": None,
            **_quality_metadata(valuation),
        }
    )
    return summary


async def get_canonical_portfolio_summary(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    await get_portfolio(db, portfolio_id, user_id)
    cache_key = _cache_key(portfolio_id, "summary")
    cached = await cache_get(cache_key)
    if cached:
        try:
            return _validate_summary_contract(cached)
        except ValidationError:
            logger.warning(
                "[summary_contract] portfolio=%s cache incompatível; recalculando",
                portfolio_id,
            )

    snapshot = await _get_latest_snapshot(db, portfolio_id)
    summary = (
        await _build_summary_from_latest_snapshot(db, portfolio_id, snapshot)
        if snapshot is not None
        else await _build_summary_from_valuation_fallback(db, portfolio_id)
    )
    validated_summary = _validate_summary_contract(summary)
    await cache_set(cache_key, validated_summary, ttl=_CACHE_TTL)
    return validated_summary
