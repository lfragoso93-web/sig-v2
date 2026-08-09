import logging
from datetime import date as DateType
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_delete, cache_get, cache_set
from app.models.asset import Asset, AssetType
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.audit_log_service import AuditLogService
from app.services.canonical_dividend_aggregation_service import (
    aggregate_received_entitlements,
    load_received_entitlements_by_ticker,
)
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)
from app.services.class_target_service import get_targets_map
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
)
from app.services.fixed_income_valuation_service import (
    RENDA_FIXA_TYPE,
    get_fixed_income_totals,
    get_fixed_income_valuations,
    valuation_to_position_payload,
)
from app.services.fx_rate_reader import (
    load_latest_usd_brl_rate,
    load_usd_brl_rates_for_dates,
)
from app.services.position_timeline_projection import (
    PositionMovement,
    PositionMovementKind,
    project_position_timeline,
)
from app.services.price_history_service import get_prices_at_date_batch
from app.services.quotes_service import get_prices

logger = logging.getLogger(__name__)

_CACHE_TTL = 120
_CACHE_PREFIX = "portfolio"


def _cache_key(portfolio_id: int, suffix: str) -> str:
    return f"{_CACHE_PREFIX}:{portfolio_id}:{suffix}"


async def invalidate_portfolio_cache(portfolio_id: int) -> None:
    try:
        await cache_delete(_cache_key(portfolio_id, "summary"))
        await cache_delete(_cache_key(portfolio_id, "positions"))
    except Exception:
        pass


_TYPE_LABEL: dict[str, str] = {
    "ACAO": "Ações",
    "FII": "FIIs",
    "ETF_NACIONAL": "ETFs Nacionais",
    "ETF_INTERNACIONAL": "ETFs Internacionais",
    "STOCK": "Stocks",
    "BDR": "BDRs",
    "CRIPTO": "Criptomoedas",
    "RENDA_FIXA": "Renda Fixa",
    "TESOURO_DIRETO": "Tesouro Direto",
    "OUTRO": "Outros",
}

_TYPE_COLOR: dict[str, str] = {
    "ACAO": "#6366f1",
    "FII": "#10b981",
    "ETF_NACIONAL": "#f59e0b",
    "ETF_INTERNACIONAL": "#3b82f6",
    "STOCK": "#ec4899",
    "BDR": "#8b5cf6",
    "CRIPTO": "#14b8a6",
    "RENDA_FIXA": "#f97316",
    "TESOURO_DIRETO": "#06b6d4",
    "OUTRO": "#6b7280",
}

_MARKET_PRICE_TYPES = {
    "ACAO", "FII", "ETF_NACIONAL", "ETF_INTERNACIONAL",
    "STOCK", "BDR", "CRIPTO", "TESOURO_DIRETO",
}

_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}

_TYPE_ALIASES: dict[str, str] = {
    "ACAO_NACIONAL": "ACAO",
    "ACOES": "ACAO",
    "ETF_INT": "ETF_INTERNACIONAL",
    "ETF": "ETF_NACIONAL",
    "TESOURO": "TESOURO_DIRETO",
    "STOCKS": "STOCK",
    "CRIPTOMOEDA": "CRIPTO",
}


def normalize_type(asset_type) -> str:
    if asset_type is None:
        return ""
    key = str(asset_type).upper().strip()
    return _TYPE_ALIASES.get(key, key)


def _asset_type_str(value) -> str:
    raw = value.value if hasattr(value, "value") else str(value or "").upper()
    return normalize_type(raw)


def _is_buy(op) -> bool:
    if isinstance(op, OperationType):
        return op == OperationType.buy
    return str(op).lower() in ("buy", "compra")


def _is_sell(op) -> bool:
    if isinstance(op, OperationType):
        return op == OperationType.sell
    return str(op).lower() in ("sell", "venda")


def _is_fixed_income_type(asset_type) -> bool:
    return normalize_type(asset_type) == RENDA_FIXA_TYPE


async def calc_raw_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date, Transaction.id)
    )
    transactions = list(result.scalars().all())
    if not transactions:
        return []

    usd_dates_needed: list[DateType] = []
    for tx in transactions:
        asset_type = _asset_type_str(tx.asset_type)
        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or asset_type in _USD_ASSET_TYPES
        )
        has_saved_rate = (
            getattr(tx, "fx_rate", None) is not None
            and float(getattr(tx, "fx_rate", 0) or 0) > 0
        )
        if is_usd and not has_saved_rate and tx.date:
            usd_dates_needed.append(tx.date)

    fx_rows = await load_usd_brl_rates_for_dates(db, usd_dates_needed) if usd_dates_needed else {}

    tickers = sorted({str(tx.ticker).strip().upper() for tx in transactions})
    actions_by_ticker = await load_global_corporate_actions_by_ticker(db, tickers)

    movements_by_ticker: dict[str, list[PositionMovement]] = {}
    metadata_by_ticker: dict[str, dict] = {}
    for tx in transactions:
        ticker = str(tx.ticker).strip().upper()
        asset_type = _asset_type_str(tx.asset_type)
        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or asset_type in _USD_ASSET_TYPES
        )

        fx_rate = Decimal(1)
        saved_rate = getattr(tx, "fx_rate", None)
        if is_usd:
            if saved_rate is not None and Decimal(str(saved_rate or 0)) > 0:
                fx_rate = Decimal(str(saved_rate))
            elif tx.date:
                persisted = fx_rows.get(tx.date)
                if persisted is None:
                    raise RuntimeError(
                        f"cobertura USD-BRL persistida indisponível em ou antes de {tx.date.isoformat()}"
                    )
                fx_rate = persisted.rate

        quantity = Decimal(str(tx.quantity or 0))
        price = Decimal(str(tx.price or 0))
        fees = Decimal(str(tx.fees or 0))
        movement_kind = (
            PositionMovementKind.BUY if _is_buy(tx.operation) else PositionMovementKind.SELL
        )
        movements_by_ticker.setdefault(ticker, []).append(
            PositionMovement(
                movement_date=tx.date,
                kind=movement_kind,
                quantity=quantity,
                unit_price=price * fx_rate,
                fees=fees * fx_rate,
                total_cost_original_currency=(
                    quantity * price + fees
                    if is_usd and movement_kind == PositionMovementKind.BUY
                    else Decimal(0)
                ),
            )
        )
        metadata_by_ticker.setdefault(
            ticker,
            {"asset_type": asset_type, "is_usd": is_usd},
        )

    positions: list[dict] = []
    for ticker in sorted(movements_by_ticker):
        projection = project_position_timeline(
            movements=movements_by_ticker[ticker],
            actions=actions_by_ticker.get(ticker, ()),
        )
        if projection.quantity <= Decimal("0.000000001"):
            continue

        metadata = metadata_by_ticker[ticker]
        asset_type = metadata["asset_type"]
        avg_usd = projection.average_price_original_currency
        positions.append({
            "ticker": ticker,
            "asset_type": asset_type,
            "asset_label": _TYPE_LABEL.get(
                asset_type,
                asset_type.replace("_", " ").title(),
            ),
            "quantity": float(projection.quantity),
            "avg_price": round(float(projection.average_price), 8),
            "avg_price_usd": round(float(avg_usd), 8) if avg_usd is not None else None,
            "total_invested": round(float(projection.total_cost), 8),
            "is_usd": metadata["is_usd"],
        })

    return positions


def enrich_with_prices(
    positions: list[dict],
    prices: dict[str, float],
    fx_today: float = 1.0,
) -> list[dict]:
    enriched = []
    for p in positions:
        ticker = p["ticker"]
        asset_type = normalize_type(p.get("asset_type", ""))
        is_usd = p.get("is_usd", False)
        price_raw = prices.get(ticker)
        item = dict(p)

        if price_raw is not None:
            price_brl = price_raw * fx_today if is_usd else price_raw
            qty = p["quantity"]
            invested = p["total_invested"]
            cur_val = qty * price_brl
            result_abs = cur_val - invested
            result_pct = (result_abs / invested * 100) if invested else 0.0
            item["current_price"] = round(price_brl, 4)
            item["current_price_usd"] = round(price_raw, 4) if is_usd else None
            item["current_value"] = round(cur_val, 2)
            item["result_abs"] = round(result_abs, 2)
            item["result_pct"] = round(result_pct, 4)
        else:
            item["current_price"] = None
            item["current_price_usd"] = None
            item["current_value"] = None
            item["result_abs"] = None
            item["result_pct"] = None
        enriched.append(item)

    return enriched


async def get_portfolio_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    positions = await calc_raw_positions(db, portfolio_id)
    if not positions:
        return []

    market_positions = [
        p for p in positions if normalize_type(p.get("asset_type", "")) in _MARKET_PRICE_TYPES
    ]
    tickers = [p["ticker"] for p in market_positions]
    prices = await get_prices(db, tickers)

    fx_today = 1.0
    if any(p.get("is_usd", False) for p in positions):
        persisted_fx = await load_latest_usd_brl_rate(db)
        if persisted_fx is None:
            raise RuntimeError("cotação USD-BRL persistida indisponível")
        fx_today = float(persisted_fx.rate)

    enriched = enrich_with_prices(positions, prices, fx_today=fx_today)
    fixed_income_valuations = await get_fixed_income_valuations(db, portfolio_id)
    fixed_income_by_ticker = {
        item.ticker: valuation_to_position_payload(item)
        for item in fixed_income_valuations
    }
    merged: list[dict] = []
    for item in enriched:
        if _is_fixed_income_type(item.get("asset_type")):
            merged.append(fixed_income_by_ticker.get(item["ticker"], item))
        else:
            merged.append(item)
    return merged


async def get_portfolio(db: AsyncSession, portfolio_id: int) -> Portfolio:
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio não encontrado")
    return portfolio


async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio)
        .where(Portfolio.user_id == user_id)
        .order_by(Portfolio.created_at.desc())
    )
    return list(result.scalars().all())


async def create_portfolio(
    db: AsyncSession,
    user_id: int,
    payload: PortfolioCreate,
) -> Portfolio:
    portfolio = Portfolio(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(portfolio)
    try:
        await db.commit()
        await db.refresh(portfolio)
    except SQLAlchemyError:
        await db.rollback()
        raise
    await AuditLogService.log_action(
        db,
        user_id=user_id,
        action="CREATE",
        entity_type="portfolio",
        entity_id=portfolio.id,
        details={"name": portfolio.name},
    )
    return portfolio


async def update_portfolio(
    db: AsyncSession,
    portfolio: Portfolio,
    payload: PortfolioUpdate,
    user_id: int,
) -> Portfolio:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(portfolio, field, value)
    try:
        await db.commit()
        await db.refresh(portfolio)
    except SQLAlchemyError:
        await db.rollback()
        raise
    await invalidate_portfolio_cache(portfolio.id)
    await AuditLogService.log_action(
        db,
        user_id=user_id,
        action="UPDATE",
        entity_type="portfolio",
        entity_id=portfolio.id,
        details=payload.model_dump(exclude_unset=True),
    )
    return portfolio


async def delete_portfolio(db: AsyncSession, portfolio: Portfolio, user_id: int) -> None:
    portfolio_id = portfolio.id
    await db.delete(portfolio)
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise
    await invalidate_portfolio_cache(portfolio_id)
    await AuditLogService.log_action(
        db,
        user_id=user_id,
        action="DELETE",
        entity_type="portfolio",
        entity_id=portfolio_id,
    )


async def get_portfolio_summary(db: AsyncSession, portfolio_id: int) -> dict:
    cached = await cache_get(_cache_key(portfolio_id, "summary"))
    if cached:
        return cached

    positions = await get_portfolio_positions(db, portfolio_id)
    market_value = sum(
        Decimal(str(item.get("current_value") or 0))
        for item in positions
    )
    invested = sum(
        Decimal(str(item.get("total_invested") or 0))
        for item in positions
    )
    fixed_income = await get_fixed_income_totals(db, portfolio_id)
    dividends = await aggregate_received_entitlements(db, portfolio_id)
    payload = {
        "portfolio_id": portfolio_id,
        "market_value": float(market_value),
        "invested": float(invested),
        "result": float(market_value - invested),
        "fixed_income_current": float(fixed_income.current_value),
        "fixed_income_income": float(fixed_income.income_amount),
        "dividends_received": float(dividends.total_received),
    }
    await cache_set(_cache_key(portfolio_id, "summary"), payload, ttl=_CACHE_TTL)
    return payload


async def get_portfolio_dividends(db: AsyncSession, portfolio_id: int) -> list[dict]:
    rows = await load_received_entitlements_by_ticker(db, portfolio_id)
    return [row.to_dict() for row in rows]


async def get_portfolio_dividend_entitlements(db: AsyncSession, portfolio_id: int) -> list[dict]:
    rows = await load_portfolio_dividend_entitlements(db, portfolio_id)
    return [row.to_dict() for row in rows]


async def get_portfolio_targets(db: AsyncSession, portfolio_id: int) -> dict[str, Decimal]:
    return await get_targets_map(db, portfolio_id)
