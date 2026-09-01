"""Reconstrução DB-first de patrimônio e TWR diário por classe.

Somente classes cuja precificação histórica é integralmente sustentada por
``asset_prices`` entram no cálculo nesta primeira versão. Classes com motores
dedicados (Tesouro e Renda Fixa) são declaradas indisponíveis, em vez de receber
uma fórmula aproximada ou retorno simples.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.models.transaction import OperationType, Transaction
from app.services.canonical_dividend_aggregation_service import (
    group_received_entitlements_by_day,
)
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
    load_portfolio_dividend_entitlements,
)
from app.services.class_snapshot_position_projection import (
    aggregate_class_positions,
    project_class_positions_at,
)
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.fx_rate_reader import load_usd_brl_rates_for_dates
from app.services.price_history_service import get_prices_at_date_batch
from app.services.twr_service import (
    DailyTwrInput,
    append_compounded_return_pct,
    build_daily_twr_chain,
    calculate_daily_twr_pct,
)

logger = logging.getLogger(__name__)
_ZERO = Decimal(0)
_MONEY = Decimal("0.01")

SUPPORTED_CLASS_TWR_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.ETF_INTERNACIONAL,
    AssetType.STOCK,
    AssetType.BDR,
    AssetType.CRIPTO,
    AssetType.TESOURO_DIRETO,
}
UNSUPPORTED_CLASS_TWR_TYPES = {
    AssetType.RENDA_FIXA,
}
MARKET_PRICE_CLASS_TWR_TYPES = SUPPORTED_CLASS_TWR_TYPES - {AssetType.TESOURO_DIRETO}
_USD_TYPES = {AssetType.STOCK, AssetType.ETF_INTERNACIONAL}


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def _asset_type(value: object) -> AssetType | None:
    raw = getattr(value, "value", value)
    try:
        return AssetType(str(raw).upper())
    except (TypeError, ValueError):
        return None


def _next_business_date(value: date) -> date:
    result = value
    while result.weekday() >= 5:
        result += timedelta(days=1)
    return result


def _business_dates(start: date, end: date) -> list[date]:
    dates: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor += timedelta(days=1)
    return dates


async def _load_required_usd_brl_rates(
    db: AsyncSession,
    start: date,
    end: date,
) -> dict[date, Decimal]:
    """Pré-carrega FX persistido e falha antes de qualquer rebuild parcial."""

    required_dates = _business_dates(start, end)
    if not required_dates:
        return {}

    persisted = await load_usd_brl_rates_for_dates(db, required_dates)
    missing = [target_date for target_date in required_dates if target_date not in persisted]
    if missing:
        raise RuntimeError(
            "cobertura USD-BRL persistida indisponível para snapshots de classe: "
            f"first_missing={missing[0].isoformat()} missing_dates={len(missing)}"
        )

    return {target_date: persisted[target_date].rate for target_date in required_dates}


@dataclass
class ClassReturnState:
    previous_value: Decimal = _ZERO
    accumulated_return_pct: Decimal = _ZERO
    dividends_accumulated: Decimal = _ZERO


def class_twr_availability(asset_types: Iterable[AssetType]) -> list[dict]:
    rows = []
    for asset_type in sorted(set(asset_types), key=lambda item: item.value):
        supported = asset_type in SUPPORTED_CLASS_TWR_TYPES
        rows.append(
            {
                "asset_type": asset_type.value,
                "available": supported,
                "status": "available" if supported else "dedicated_history_not_available",
                "reason": None if supported else (
                    "A classe exige valuation histórico dedicado; nenhuma estimativa é exibida."
                ),
            }
        )
    return rows


def _group_received_dividends(
    entitlements: Iterable[PortfolioDividendEntitlement],
) -> dict[tuple[AssetType, date], Decimal]:
    totals: dict[tuple[AssetType, date], Decimal] = {}
    items = list(entitlements)
    for asset_type in SUPPORTED_CLASS_TWR_TYPES:
        by_day, _ = group_received_entitlements_by_day(
            items,
            asset_types=(asset_type.value,),
        )
        totals.update(
            ((asset_type, payment_date), value)
            for payment_date, value in by_day.items()
        )
    return totals


def _operation_brl(transaction: Transaction) -> tuple[Decimal, Decimal, Decimal]:
    fx_rate = _decimal(getattr(transaction, "fx_rate", None) or 1)
    quantity = _decimal(transaction.quantity)
    price_brl = _decimal(transaction.price) * fx_rate
    fees_brl = _decimal(transaction.fees) * fx_rate
    return quantity, price_brl, fees_brl


async def _load_exact_treasury_prices(
    db: AsyncSession,
    tickers: Iterable[str],
    target_date: date,
) -> dict[str, Decimal]:
    normalized = sorted({str(ticker).upper() for ticker in tickers if ticker})
    if not normalized:
        return {}

    result = await db.execute(
        select(Asset.ticker, AssetPrice.close)
        .join(AssetPrice, AssetPrice.asset_id == Asset.id)
        .where(
            Asset.asset_type == AssetType.TESOURO_DIRETO.value,
            func.upper(Asset.ticker).in_(normalized),
            func.date(AssetPrice.timestamp) == target_date,
        )
        .order_by(AssetPrice.timestamp.desc())
    )
    prices: dict[str, Decimal] = {}
    for ticker, close in result.all():
        key = str(ticker).upper()
        if key not in prices:
            prices[key] = _decimal(close)
    return prices


async def _upsert_class_snapshot(
    db: AsyncSession,
    portfolio_id: int,
    asset_type: AssetType,
    snapshot_date: date,
    values: dict,
) -> None:
    statement = (
        pg_insert(PortfolioClassSnapshot)
        .values(
            portfolio_id=portfolio_id,
            asset_type=asset_type.value,
            snapshot_date=snapshot_date,
            **values,
        )
        .on_conflict_do_update(
            constraint="uq_class_snapshot_portfolio_type_date",
            set_=values,
        )
    )
    await db.execute(statement)


async def rebuild_class_snapshots(
    db: AsyncSession,
    portfolio_id: int,
    days_back: int | None = None,
) -> int:
    """Reconstrói a cadeia completa de TWR por classe usando apenas o banco.

    ``days_back`` é aceito por compatibilidade com o endpoint consolidado, mas a
    cadeia por classe é sempre reconstruída desde a primeira operação. Isso evita
    reiniciar o retorno acumulado no meio da série e prioriza fidelidade.
    """
    transaction_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(transaction_result.scalars().all())
    if not transactions:
        return 0

    portfolio_types: set[AssetType] = set()
    for transaction in transactions:
        parsed = _asset_type(transaction.asset_type)
        if parsed is None:
            continue
        portfolio_types.add(parsed)

    supported_transactions = [
        transaction
        for transaction in transactions
        if _asset_type(transaction.asset_type) in SUPPORTED_CLASS_TWR_TYPES
    ]
    market_transactions = [
        transaction
        for transaction in transactions
        if _asset_type(transaction.asset_type) in MARKET_PRICE_CLASS_TWR_TYPES
    ]
    treasury_transactions = [
        transaction
        for transaction in transactions
        if _asset_type(transaction.asset_type) == AssetType.TESOURO_DIRETO
    ]
    if not supported_transactions:
        return 0

    if days_back is not None:
        logger.info(
            "[class_twr] portfolio=%s days_back=%s ignorado para preservar cadeia completa",
            portfolio_id,
            days_back,
        )

    today = datetime.now(UTC).date()
    usd_transactions = [
        transaction
        for transaction in market_transactions
        if _asset_type(transaction.asset_type) in _USD_TYPES
    ]
    fx_rates_by_date: dict[date, Decimal] = {}
    if usd_transactions:
        first_usd_date = _next_business_date(
            min(transaction.date for transaction in usd_transactions)
        )
        fx_rates_by_date = await _load_required_usd_brl_rates(
            db,
            first_usd_date,
            today,
        )

    dividends_by_class_day = _group_received_dividends(
        await load_portfolio_dividend_entitlements(db, portfolio_id),
    )

    start = _next_business_date(supported_transactions[0].date)
    await db.execute(
        delete(PortfolioClassSnapshot).where(
            PortfolioClassSnapshot.portfolio_id == portfolio_id
        )
    )

    transactions_by_day: dict[date, list[Transaction]] = defaultdict(list)
    for transaction in market_transactions:
        transactions_by_day[_next_business_date(transaction.date)].append(transaction)
    treasury_transactions_by_day: dict[date, list[Transaction]] = defaultdict(list)
    for transaction in treasury_transactions:
        treasury_transactions_by_day[_next_business_date(transaction.date)].append(transaction)

    actions_by_ticker = await load_global_corporate_actions_by_ticker(
        db,
        [str(transaction.ticker) for transaction in market_transactions],
    )

    return_states: dict[AssetType, ClassReturnState] = defaultdict(ClassReturnState)
    treasury_inputs: list[DailyTwrInput] = []
    treasury_realized_pnl = _ZERO
    count = 0
    cursor = start
    while cursor <= today:
        if cursor.weekday() < 5:
            external_flows: dict[AssetType, Decimal] = defaultdict(lambda: _ZERO)
            for transaction in transactions_by_day.get(cursor, []):
                parsed = _asset_type(transaction.asset_type)
                if parsed not in SUPPORTED_CLASS_TWR_TYPES:
                    continue
                quantity, price_brl, fees_brl = _operation_brl(transaction)
                if transaction.operation == OperationType.buy:
                    external_flows[parsed] += quantity * price_brl + fees_brl
                elif transaction.operation == OperationType.sell:
                    external_flows[parsed] -= quantity * price_brl - fees_brl

            projected_positions = project_class_positions_at(
                market_transactions,
                actions_by_ticker,
                target_date=cursor,
            )
            open_by_class, realized_by_class = aggregate_class_positions(
                projected_positions.values()
            )

            for asset_type in sorted(
                SUPPORTED_CLASS_TWR_TYPES & portfolio_types,
                key=lambda item: item.value,
            ):
                open_positions = open_by_class.get(asset_type, [])
                requirements = [
                    (position.ticker, asset_type)
                    for position in open_positions
                ]
                prices = (
                    await get_prices_at_date_batch(db, requirements, cursor.isoformat())
                    if requirements
                    else {}
                )
                fx_rate = Decimal(1)
                if asset_type in _USD_TYPES and requirements:
                    fx_rate = fx_rates_by_date[cursor]

                market_value = _ZERO
                cost_basis = _ZERO
                has_partial_prices = False
                for position in open_positions:
                    close = prices.get(position.ticker)
                    if close is None:
                        has_partial_prices = True
                        close_decimal = (
                            position.cost / position.quantity
                            if position.quantity > 0
                            else _ZERO
                        )
                    else:
                        close_decimal = _decimal(close) * fx_rate
                    market_value += position.quantity * close_decimal
                    cost_basis += position.cost

                class_state = return_states[asset_type]
                dividends_day = dividends_by_class_day.get((asset_type, cursor), _ZERO)
                class_state.dividends_accumulated += dividends_day
                daily_return = calculate_daily_twr_pct(
                    class_state.previous_value,
                    market_value,
                    net_external_flow=external_flows[asset_type],
                    dividends_day=dividends_day,
                )
                class_state.accumulated_return_pct = append_compounded_return_pct(
                    class_state.accumulated_return_pct,
                    daily_return,
                )
                unrealized_pnl = market_value - cost_basis

                await _upsert_class_snapshot(
                    db,
                    portfolio_id,
                    asset_type,
                    cursor,
                    {
                        "market_value": market_value.quantize(_MONEY),
                        "cost_basis": cost_basis.quantize(_MONEY),
                        "realized_pnl": realized_by_class.get(asset_type, _ZERO).quantize(_MONEY),
                        "unrealized_pnl": unrealized_pnl.quantize(_MONEY),
                        "net_external_flow": external_flows[asset_type].quantize(_MONEY),
                        "dividends_day": dividends_day.quantize(_MONEY),
                        "dividends_accumulated": class_state.dividends_accumulated.quantize(_MONEY),
                        "daily_return_pct": daily_return,
                        "accumulated_return_pct": class_state.accumulated_return_pct,
                        "has_partial_prices": has_partial_prices,
                        "return_is_estimated": True,
                        "valuation_status": "partial_prices" if has_partial_prices else "complete",
                    },
                )
                class_state.previous_value = market_value
                count += 1

            if AssetType.TESOURO_DIRETO in portfolio_types:
                treasury_flow = _ZERO
                for transaction in treasury_transactions_by_day.get(cursor, []):
                    quantity, price_brl, fees_brl = _operation_brl(transaction)
                    if transaction.operation == OperationType.buy:
                        treasury_flow += quantity * price_brl + fees_brl
                    elif transaction.operation == OperationType.sell:
                        treasury_flow -= quantity * price_brl - fees_brl

                treasury_positions = project_class_positions_at(
                    treasury_transactions,
                    {},
                    target_date=cursor,
                )
                treasury_open, treasury_realized = aggregate_class_positions(
                    treasury_positions.values()
                )
                treasury_realized_pnl = treasury_realized.get(
                    AssetType.TESOURO_DIRETO,
                    treasury_realized_pnl,
                )
                open_positions = treasury_open.get(AssetType.TESOURO_DIRETO, [])
                treasury_prices = await _load_exact_treasury_prices(
                    db,
                    (position.ticker for position in open_positions),
                    cursor,
                )
                has_coverage = all(
                    str(position.ticker).upper() in treasury_prices
                    for position in open_positions
                )
                market_value = _ZERO
                cost_basis = _ZERO
                for position in open_positions:
                    close = treasury_prices.get(str(position.ticker).upper())
                    if close is not None:
                        market_value += position.quantity * close
                    cost_basis += position.cost

                treasury_inputs.append(
                    DailyTwrInput(
                        reference_date=cursor,
                        market_value=market_value,
                        net_external_flow=treasury_flow,
                        income_day=_ZERO,
                        has_coverage=has_coverage,
                    )
                )
                treasury_point = build_daily_twr_chain(treasury_inputs)[-1]
                if treasury_point.available:
                    unrealized_pnl = market_value - cost_basis
                    await _upsert_class_snapshot(
                        db,
                        portfolio_id,
                        AssetType.TESOURO_DIRETO,
                        cursor,
                        {
                            "market_value": market_value.quantize(_MONEY),
                            "cost_basis": cost_basis.quantize(_MONEY),
                            "realized_pnl": treasury_realized_pnl.quantize(_MONEY),
                            "unrealized_pnl": unrealized_pnl.quantize(_MONEY),
                            "net_external_flow": treasury_flow.quantize(_MONEY),
                            "dividends_day": _ZERO,
                            "dividends_accumulated": _ZERO.quantize(_MONEY),
                            "daily_return_pct": treasury_point.daily_return_pct,
                            "accumulated_return_pct": treasury_point.accumulated_return_pct,
                            "has_partial_prices": False,
                            "return_is_estimated": False,
                            "valuation_status": "complete",
                        },
                    )
                    count += 1

            if count and count % 100 == 0:
                await db.commit()
        cursor += timedelta(days=1)

    await db.commit()
    logger.info(
        "[class_twr] portfolio=%s snapshots=%s start=%s supported=%s unavailable=%s",
        portfolio_id,
        count,
        start,
        sorted(item.value for item in SUPPORTED_CLASS_TWR_TYPES & portfolio_types),
        sorted(item.value for item in UNSUPPORTED_CLASS_TWR_TYPES & portfolio_types),
    )
    return count
