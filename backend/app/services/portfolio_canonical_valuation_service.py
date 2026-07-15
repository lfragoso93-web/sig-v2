"""Composição canônica do valuation diário da carteira.

Ativos de mercado usam o histórico genérico. Renda Fixa e Tesouro não são enviados
para o lookup legado: entram pelo custo apenas como base intermediária e são
substituídos pelos respectivos motores dedicados antes do retorno.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import DEDICATED_PRICE_TYPES, NO_QUOTE_TYPES
from app.models.asset import Asset, AssetType
from app.models.transaction import OperationType, Transaction
from app.services.fixed_income_valuation_service import (
    RENDA_FIXA_TYPE,
    _aggregate_applications,
    _apply_redemption,
    _application_from_buy,
    _is_buy,
    _is_sell,
)
from app.services.portfolio_snapshot_service import _build_positions_at
from app.services.price_history_service import get_price_at_date, get_prices_at_date_batch
from app.services.treasury_catalog_service import resolve_treasury_symbol

_ZERO = Decimal("0")
_MONEY = Decimal("0.01")
_PCT = Decimal("0.0001")
_TREASURY_TYPE = AssetType.TESOURO_DIRETO.value
_NON_MARKET_TYPES = NO_QUOTE_TYPES | DEDICATED_PRICE_TYPES


def _asset_type(value: object) -> AssetType:
    raw = getattr(value, "value", value)
    try:
        return AssetType(str(raw))
    except (TypeError, ValueError):
        return AssetType.ACAO


async def _base_totals_without_dedicated_lookup(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, Decimal]:
    """Replica a base patrimonial sem consultar preços para classes dedicadas."""
    positions = await _build_positions_at(db, portfolio_id, target_date)
    if not positions:
        return {
            "market_value": _ZERO,
            "cost_basis": _ZERO,
            "invested_total": _ZERO,
            "realized_pnl": _ZERO,
            "unrealized_pnl": _ZERO,
            "total_pnl": _ZERO,
            "return_pct": _ZERO,
        }

    tickers = list(positions)
    rows = await db.execute(
        select(Asset.ticker, Asset.asset_type).where(Asset.ticker.in_(tickers))
    )
    persisted_types = {str(row.ticker): _asset_type(row.asset_type) for row in rows.all()}

    requirements: list[tuple[str, AssetType]] = []
    effective_types: dict[str, AssetType] = {}
    for ticker, state in positions.items():
        current_type = persisted_types.get(ticker) or _asset_type(state.asset_type)
        effective_types[ticker] = current_type
        if current_type not in _NON_MARKET_TYPES:
            requirements.append((ticker, current_type))

    prices = await get_prices_at_date_batch(db, requirements, target_date.isoformat()) if requirements else {}

    market_value = _ZERO
    cost_basis = _ZERO
    realized_pnl = _ZERO
    for ticker, state in positions.items():
        current_type = effective_types[ticker]
        if current_type in _NON_MARKET_TYPES:
            close = state.avg_price
        else:
            close = Decimal(str(prices.get(ticker, float(state.avg_price))))
        market_value += state.qty * close
        cost_basis += state.cost
        realized_pnl += state.realized_pnl

    invested_result = await db.execute(
        select(
            func.sum(
                case(
                    (
                        Transaction.operation == OperationType.buy,
                        Transaction.price
                        * func.coalesce(Transaction.fx_rate, 1.0)
                        * Transaction.quantity
                        + func.coalesce(Transaction.fees, 0)
                        * func.coalesce(Transaction.fx_rate, 1.0),
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
    return_base = cost_basis + max(realized_pnl, _ZERO)
    if return_base > 0:
        return_pct = total_pnl / return_base * Decimal("100")
    elif invested_total > 0:
        return_pct = total_pnl / invested_total * Decimal("100")
    else:
        return_pct = _ZERO

    return {
        "market_value": market_value.quantize(_MONEY),
        "cost_basis": cost_basis.quantize(_MONEY),
        "invested_total": invested_total.quantize(_MONEY),
        "realized_pnl": realized_pnl.quantize(_MONEY),
        "unrealized_pnl": unrealized_pnl.quantize(_MONEY),
        "total_pnl": total_pnl.quantize(_MONEY),
        "return_pct": return_pct.quantize(_PCT),
    }


async def _fixed_income_totals_at_date(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, Decimal]:
    """Calcula Renda Fixa usando somente lançamentos existentes até a data-alvo."""
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_type == RENDA_FIXA_TYPE,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )

    applications = []
    for tx in result.scalars().all():
        if _is_buy(tx.operation):
            application = _application_from_buy(tx)
            if application.invested_amount > 0:
                applications.append(application)
        elif _is_sell(tx.operation):
            _apply_redemption(applications, tx)

    valuations = await _aggregate_applications(db, applications, target_date)
    invested = sum((item.invested_amount for item in valuations), _ZERO).quantize(_MONEY)
    current = sum((item.current_value for item in valuations), _ZERO).quantize(_MONEY)
    return {
        "invested_amount": invested,
        "current_value": current,
        "income_amount": (current - invested).quantize(_MONEY),
    }


async def _treasury_correction_at_date(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict[str, Decimal | int]:
    """Substitui o proxy por custo médio pelo preço do ativo oficial do Tesouro."""
    positions = await _build_positions_at(db, portfolio_id, target_date)
    correction = _ZERO
    matched = 0
    unresolved = 0

    for ticker, state in positions.items():
        raw_type = state.asset_type.value if hasattr(state.asset_type, "value") else str(state.asset_type or "")
        if raw_type.upper() != _TREASURY_TYPE:
            continue

        canonical = await resolve_treasury_symbol(db, ticker)
        if not canonical:
            unresolved += 1
            continue

        price = await get_price_at_date(
            db,
            canonical,
            AssetType.TESOURO_DIRETO,
            target_date.isoformat(),
        )
        if price is None:
            unresolved += 1
            continue

        canonical_value = state.qty * Decimal(str(price))
        proxy_value = state.qty * state.avg_price
        correction += canonical_value - proxy_value
        matched += 1

    return {
        "correction": correction.quantize(_MONEY),
        "matched": matched,
        "unresolved": unresolved,
    }


async def calculate_canonical_portfolio_totals(
    db: AsyncSession,
    portfolio_id: int,
    target_date: date,
) -> dict:
    """Retorna totais de mercado corrigidos por Renda Fixa e Tesouro."""
    totals = await _base_totals_without_dedicated_lookup(db, portfolio_id, target_date)
    fixed_income = await _fixed_income_totals_at_date(db, portfolio_id, target_date)
    treasury = await _treasury_correction_at_date(db, portfolio_id, target_date)

    fixed_income_correction = fixed_income["current_value"] - fixed_income["invested_amount"]
    total_correction = fixed_income_correction + Decimal(str(treasury["correction"]))
    market_value = Decimal(str(totals["market_value"])) + total_correction
    unrealized_pnl = Decimal(str(totals["unrealized_pnl"])) + total_correction
    realized_pnl = Decimal(str(totals["realized_pnl"]))
    total_pnl = realized_pnl + unrealized_pnl
    cost_basis = Decimal(str(totals["cost_basis"]))
    invested_total = Decimal(str(totals["invested_total"]))

    return_base = cost_basis + max(realized_pnl, _ZERO)
    if return_base > 0:
        return_pct = total_pnl / return_base * Decimal("100")
    elif invested_total > 0:
        return_pct = total_pnl / invested_total * Decimal("100")
    else:
        return_pct = _ZERO

    return {
        **totals,
        "market_value": market_value.quantize(_MONEY),
        "unrealized_pnl": unrealized_pnl.quantize(_MONEY),
        "total_pnl": total_pnl.quantize(_MONEY),
        "return_pct": return_pct.quantize(_PCT),
        "fixed_income_invested": fixed_income["invested_amount"],
        "fixed_income_current": fixed_income["current_value"],
        "fixed_income_income": fixed_income["income_amount"],
        "treasury_correction": treasury["correction"],
        "treasury_matched": treasury["matched"],
        "treasury_unresolved": treasury["unresolved"],
    }
