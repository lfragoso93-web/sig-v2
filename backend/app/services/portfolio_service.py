import logging
from datetime import date as DateType, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from fastapi import HTTPException

from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.dividend import Dividend
from app.models.asset import Asset, AssetType
from app.models.audit_log import AuditLog
from app.models.corporate_event import CorporateEvent
from app.models.fixed_income import FixedIncomeInvestment
from app.models.goal import Goal
from app.models.irpf import IRPFReport
from app.models.portfolio_class_target import PortfolioClassTarget
from app.models.portfolio_position import PortfolioPosition
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.quotes_service import get_prices
from app.services.class_target_service import get_targets_map
from app.services.fx_service import get_usd_brl_batch, get_usd_brl_today
from app.core.cache import cache_get, cache_set, cache_delete
from app.services.audit_log_service import AuditLogService
from app.services.fixed_income_valuation_service import (
    RENDA_FIXA_TYPE,
    get_fixed_income_totals,
    get_fixed_income_valuations,
    valuation_to_position_payload,
)
from app.services.price_history_service import get_prices_at_date_batch

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
        .order_by(Transaction.date)
    )
    transactions = list(result.scalars().all())

    usd_dates_needed: list[str] = []
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
            usd_dates_needed.append(tx.date.isoformat())

    fx_map: dict[str, float] = {}
    if usd_dates_needed:
        fx_map = await get_usd_brl_batch(db, usd_dates_needed)

    state: dict[str, dict] = {}

    for tx in transactions:
        ticker = str(tx.ticker).upper()
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        op = tx.operation
        asset_type = _asset_type_str(tx.asset_type)

        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or asset_type in _USD_ASSET_TYPES
        )

        fx_rate = 1.0
        if is_usd:
            saved_rate = getattr(tx, "fx_rate", None)
            if saved_rate is not None and float(saved_rate or 0) > 0:
                fx_rate = float(saved_rate)
            elif tx.date:
                fx_rate = fx_map.get(tx.date.isoformat(), 1.0)

        price_brl = price * fx_rate
        fees_brl = fees * fx_rate

        if ticker not in state:
            state[ticker] = {
                "quantity": 0.0,
                "total_cost": 0.0,
                "total_cost_usd": 0.0,
                "asset_type": asset_type,
                "is_usd": is_usd,
            }

        s = state[ticker]

        if _is_buy(op):
            s["total_cost"] += qty * price_brl + fees_brl
            s["quantity"] += qty
            if is_usd:
                s["total_cost_usd"] += qty * price + fees
        elif _is_sell(op):
            if s["quantity"] > 0:
                ratio = min(qty, s["quantity"]) / s["quantity"]
                s["total_cost"] -= s["total_cost"] * ratio
                s["total_cost_usd"] -= s["total_cost_usd"] * ratio
                s["quantity"] = max(0.0, s["quantity"] - qty)

    positions = []
    for ticker, s in state.items():
        qty = s["quantity"]
        if qty <= 1e-9:
            continue
        avg_brl = s["total_cost"] / qty if qty else 0.0
        avg_usd = s["total_cost_usd"] / qty if qty and s["is_usd"] else None
        at = s["asset_type"]
        positions.append({
            "ticker": ticker,
            "asset_type": at,
            "asset_label": _TYPE_LABEL.get(at, at.replace("_", " ").title()),
            "quantity": qty,
            "avg_price": round(avg_brl, 8),
            "avg_price_usd": round(avg_usd, 8) if avg_usd is not None else None,
            "total_invested": round(s["total_cost"], 8),
            "is_usd": s["is_usd"],
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
            item["current_value"] = round(p["total_invested"], 2) if asset_type not in _MARKET_PRICE_TYPES else None
            item["result_abs"] = None
            item["result_pct"] = None
        enriched.append(item)
    return enriched


async def _fetch_prices_batch(db: AsyncSession, positions_raw: list[dict]) -> dict[str, float]:
    if not positions_raw:
        return {}
    price_input = [
        {"ticker": p["ticker"], "asset_type": p["asset_type"]}
        for p in positions_raw
        if not _is_fixed_income_type(p.get("asset_type"))
    ]
    if not price_input:
        return {}
    try:
        return await get_prices(price_input, db)
    except Exception as e:
        logger.error(f"[portfolio_service] erro ao buscar precos: {e}")
        return {}


async def _fetch_logos_batch(db: AsyncSession, tickers: list[str]) -> dict[str, str | None]:
    if not tickers:
        return {}
    result = await db.execute(
        select(Asset.ticker, Asset.logo_url).where(Asset.ticker.in_(tickers))
    )
    return {row.ticker: row.logo_url for row in result.all()}


def build_group_performance_metrics(
    current_value: float,
    total_invested: float,
    previous_value: float | None,
    proventos_grupo: float = 0.0,
) -> dict:
    capital_result = current_value - total_invested
    daily_variation_value = None
    daily_variation_pct = None
    if previous_value is not None and previous_value > 0:
        daily_variation_value = current_value - previous_value
        daily_variation_pct = daily_variation_value / previous_value * 100

    rentabilidade_pct = None
    if total_invested > 0:
        rentabilidade_pct = (capital_result + proventos_grupo) / total_invested * 100

    return {
        "daily_variation_value": (
            round(daily_variation_value, 2)
            if daily_variation_value is not None
            else None
        ),
        "daily_variation_pct": (
            round(daily_variation_pct, 4)
            if daily_variation_pct is not None
            else None
        ),
        "rentabilidade_pct": (
            round(rentabilidade_pct, 4)
            if rentabilidade_pct is not None
            else None
        ),
    }


def _asset_type_enum(asset_type: str | None) -> AssetType:
    try:
        return AssetType(normalize_type(asset_type))
    except (ValueError, KeyError):
        return AssetType.ACAO


async def _fetch_previous_prices_batch(
    db: AsyncSession,
    positions: list[dict],
) -> tuple[dict[str, float], str]:
    previous_date = (DateType.today() - timedelta(days=1)).isoformat()
    tickers_with_types = [
        (p["ticker"], _asset_type_enum(p.get("asset_type")))
        for p in positions
        if p.get("current_price") is not None
        and normalize_type(p.get("asset_type")) in _MARKET_PRICE_TYPES
    ]
    if not tickers_with_types:
        return {}, previous_date
    return await get_prices_at_date_batch(db, tickers_with_types, previous_date), previous_date


async def sum_dividends(db: AsyncSession, portfolio_id: int, cutoff: DateType | None = None) -> float:
    from app.models.asset_dividend import AssetDividend

    q = select(func.sum(Dividend.total_value)).where(Dividend.portfolio_id == portfolio_id)
    if cutoff is not None:
        q = (
            q.outerjoin(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
            .where(
                (AssetDividend.ex_date >= cutoff) | (Dividend.asset_dividend_id.is_(None))
            )
        )
    try:
        result = await db.execute(q)
        total = result.scalar_one_or_none()
        return float(total) if total is not None else 0.0
    except Exception as e:
        logger.warning(f"[portfolio_service] sum_dividends falhou: {e} — retornando 0.0")
        try:
            await db.rollback()
        except Exception:
            pass
        return 0.0


async def sum_dividends_for_tickers(
    db: AsyncSession,
    portfolio_id: int,
    tickers: list[str],
) -> float:
    if not tickers:
        return 0.0
    q = (
        select(func.sum(Dividend.total_value))
        .where(
            Dividend.portfolio_id == portfolio_id,
            Dividend.ticker.in_(tickers),
        )
    )
    try:
        result = await db.execute(q)
        total = result.scalar_one_or_none()
        return float(total) if total is not None else 0.0
    except Exception as e:
        logger.warning(f"[portfolio_service] sum_dividends_for_tickers falhou: {e} — retornando 0.0")
        try:
            await db.rollback()
        except Exception:
            pass
        return 0.0


async def sum_dividends_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
    tickers: list[str],
) -> dict[str, float]:
    if not tickers:
        return {}
    q = (
        select(Dividend.ticker, func.sum(Dividend.total_value).label("total"))
        .where(
            Dividend.portfolio_id == portfolio_id,
            Dividend.ticker.in_(tickers),
        )
        .group_by(Dividend.ticker)
    )
    try:
        result = await db.execute(q)
        return {row.ticker: float(row.total or 0.0) for row in result.all()}
    except Exception as e:
        logger.warning(f"[portfolio_service] sum_dividends_by_ticker falhou: {e} — retornando vazio")
        try:
            await db.rollback()
        except Exception:
            pass
        return {}


async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at)
    )
    return list(result.scalars().all())


async def create_portfolio(db: AsyncSession, user_id: int, data: PortfolioCreate) -> Portfolio:
    portfolio = Portfolio(user_id=user_id, name=data.name, description=getattr(data, "description", None))
    db.add(portfolio)
    await db.flush()

    await AuditLogService.log_action(
        db=db,
        user_id=user_id,
        action="CREATE",
        resource_type="Portfolio",
        resource_id=portfolio.id,
        portfolio_id=portfolio.id,
        new_values={"name": data.name, "description": getattr(data, "description", None)},
    )

    await db.commit()
    await db.refresh(portfolio)
    return portfolio


async def get_portfolio(db: AsyncSession, portfolio_id: int, user_id: int) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Carteira nao encontrada")
    return portfolio


async def update_portfolio(db: AsyncSession, portfolio_id: int, user_id: int, data: PortfolioUpdate) -> Portfolio:
    portfolio = await get_portfolio(db, portfolio_id, user_id)

    old_values = {"name": portfolio.name, "description": portfolio.description}

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(portfolio, field, value)

    new_values = {"name": portfolio.name, "description": portfolio.description}

    await AuditLogService.log_action(
        db=db,
        user_id=user_id,
        action="UPDATE",
        resource_type="Portfolio",
        resource_id=portfolio_id,
        portfolio_id=portfolio_id,
        old_values=old_values,
        new_values=new_values,
    )

    await db.commit()
    await db.refresh(portfolio)
    await invalidate_portfolio_cache(portfolio_id)
    return portfolio


async def delete_portfolio(db: AsyncSession, portfolio_id: int, user_id: int) -> None:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    old_values = {"name": portfolio.name, "description": portfolio.description}

    await AuditLogService.log_action(
        db=db,
        user_id=user_id,
        action="DELETE",
        resource_type="Portfolio",
        resource_id=portfolio_id,
        portfolio_id=portfolio_id,
        old_values=old_values,
    )
    await db.flush()

    await db.execute(
        update(AuditLog)
        .where(AuditLog.portfolio_id == portfolio_id)
        .values(portfolio_id=None)
    )

    dependent_models = (
        Dividend,
        CorporateEvent,
        FixedIncomeInvestment,
        Goal,
        IRPFReport,
        PortfolioClassTarget,
        PortfolioPosition,
        PortfolioSnapshot,
        Transaction,
    )
    for model in dependent_models:
        await db.execute(delete(model).where(model.portfolio_id == portfolio_id))

    await db.delete(portfolio)
    await db.commit()
    await invalidate_portfolio_cache(portfolio_id)


async def _non_fixed_income_enriched(db: AsyncSession, portfolio_id: int) -> list[dict]:
    positions_raw = await calc_raw_positions(db, portfolio_id)
    positions_raw = [p for p in positions_raw if not _is_fixed_income_type(p.get("asset_type"))]
    fx_today = await get_usd_brl_today(db)
    prices = await _fetch_prices_batch(db, positions_raw)
    return enrich_with_prices(positions_raw, prices, fx_today=fx_today)


async def get_portfolio_summary(db: AsyncSession, portfolio_id: int, user_id: int) -> dict:
    await get_portfolio(db, portfolio_id, user_id)
    cache_key = _cache_key(portfolio_id, "summary")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    enriched = await _non_fixed_income_enriched(db, portfolio_id)
    rf_totals = await get_fixed_income_totals(db, portfolio_id)

    non_rf_invested = sum(p["total_invested"] for p in enriched)
    non_rf_current = sum(
        (e["current_value"] if e["current_value"] is not None else e["total_invested"])
        for e in enriched
    )

    total_invested = non_rf_invested + float(rf_totals["invested_amount"])
    current_value = non_rf_current + float(rf_totals["current_value"])

    tickers_without_price = [
        e["ticker"] for e in enriched
        if e.get("current_price") is None and e["asset_type"] in _MARKET_PRICE_TYPES
    ]
    has_partial_prices = len(tickers_without_price) > 0

    cutoff_12m = (datetime.now(timezone.utc) - timedelta(days=365)).date()
    dividendos_12m = await sum_dividends(db, portfolio_id, cutoff=cutoff_12m)
    total_proventos = await sum_dividends(db, portfolio_id)

    tickers_em_carteira = [p["ticker"] for p in enriched]
    proventos_em_carteira = await sum_dividends_for_tickers(db, portfolio_id, tickers_em_carteira)

    total_gain = current_value - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0.0
    lucro_total = total_gain + proventos_em_carteira
    rentabilidade_total_pct = (lucro_total / total_invested * 100) if total_invested else 0.0

    fx_today = await get_usd_brl_today(db)
    result = {
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_gain": round(total_gain, 2),
        "total_gain_pct": round(total_gain_pct, 4),
        "total_patrimonio": round(current_value, 2),
        "total_investido": round(total_invested, 2),
        "lucro_total": round(lucro_total, 2),
        "variacao_valor": round(total_gain, 2),
        "variacao_percentual": round(total_gain_pct, 4),
        "rentabilidade_total": round(rentabilidade_total_pct, 4),
        "dividendos_recebidos_12m": round(dividendos_12m, 2),
        "total_proventos": round(total_proventos, 2),
        "proventos_em_carteira": round(proventos_em_carteira, 2),
        "ganho_capital": round(total_gain, 2),
        "has_partial_prices": has_partial_prices,
        "assets_without_price": tickers_without_price,
        "usd_brl_rate": round(fx_today, 4),
    }

    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result


async def get_portfolio_positions(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    await get_portfolio(db, portfolio_id, user_id)
    cache_key = _cache_key(portfolio_id, "positions")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    enriched = await _non_fixed_income_enriched(db, portfolio_id)
    targets_map = await get_targets_map(db, portfolio_id)
    previous_prices, previous_reference_date = await _fetch_previous_prices_batch(db, enriched)
    fx_today = await get_usd_brl_today(db)

    tickers = [e["ticker"] for e in enriched]
    logos = await _fetch_logos_batch(db, tickers)
    dividends_by_ticker = await sum_dividends_by_ticker(db, portfolio_id, tickers)

    valuations = await get_fixed_income_valuations(db, portfolio_id)
    rf_positions = [valuation_to_position_payload(v, idx + 1) for idx, v in enumerate(valuations)]

    total_current = sum(
        (e["current_value"] if e["current_value"] is not None else e["total_invested"])
        for e in enriched
    ) + sum(p["current_value"] for p in rf_positions)

    groups: dict[str, dict] = {}
    for idx, e in enumerate(enriched):
        at = e["asset_type"] or "OUTRO"
        label = _TYPE_LABEL.get(at, at.replace("_", " ").title())
        val_for_alloc = e["current_value"] if e["current_value"] is not None else e["total_invested"]
        alloc = (val_for_alloc / total_current * 100) if total_current else 0
        is_usd = e.get("is_usd", False)

        if at not in groups:
            groups[at] = {
                "label": label,
                "count": 0,
                "total_value": 0.0,
                "total_invested": 0.0,
                "positions": [],
            }

        groups[at]["count"] += 1
        groups[at]["total_value"] += val_for_alloc
        groups[at]["total_invested"] += e["total_invested"]
        groups[at]["positions"].append({
            "id": idx + 1,
            "ticker": e["ticker"],
            "asset_type": at,
            "asset_label": label,
            "quantity": round(e["quantity"], 8),
            "average_price": round(e["avg_price_usd"], 4) if (is_usd and e.get("avg_price_usd") is not None) else round(e["avg_price"], 4),
            "average_price_brl": round(e["avg_price"], 4),
            "average_price_usd": e.get("avg_price_usd"),
            "current_price": e["current_price_usd"] if (is_usd and e.get("current_price_usd") is not None) else e["current_price"],
            "current_price_brl": e["current_price"],
            "current_price_usd": e.get("current_price_usd"),
            "current_value": e["current_value"],
            "invested_value": round(e["total_invested"], 2),
            "variation_value": e["result_abs"],
            "variation_percent": e["result_pct"],
            "allocation_pct": round(alloc, 4),
            "logo_url": logos.get(e["ticker"]),
            "is_usd": is_usd,
            "currency": "USD" if is_usd else "BRL",
        })

    if rf_positions:
        rf_total_value = sum(p["current_value"] for p in rf_positions)
        rf_total_invested = sum(p["invested_value"] for p in rf_positions)
        for p in rf_positions:
            p["allocation_pct"] = round((p["current_value"] / total_current * 100) if total_current else 0, 4)
        groups[RENDA_FIXA_TYPE] = {
            "label": _TYPE_LABEL[RENDA_FIXA_TYPE],
            "count": len(rf_positions),
            "total_value": rf_total_value,
            "total_invested": rf_total_invested,
            "positions": rf_positions,
        }

    sorted_groups = sorted(groups.values(), key=lambda g: g["total_value"], reverse=True)
    for g in sorted_groups:
        g["total_value"] = round(g["total_value"], 2)
        g["total_invested"] = round(g["total_invested"], 2)

        if g["positions"] and g["positions"][0].get("asset_type") == RENDA_FIXA_TYPE:
            inv = g["total_invested"]
            cur = g["total_value"]
            metrics = build_group_performance_metrics(cur, inv, None, 0.0)
            g["daily_variation_value"] = None
            g["daily_variation_pct"] = None
            g["variation_pct"] = None
            g["variation_reference_date"] = None
            g["proventos_grupo"] = 0.0
            g["rentabilidade_pct"] = metrics["rentabilidade_pct"]
            g["target_pct"] = targets_map.get(RENDA_FIXA_TYPE)
            continue

        quoted_positions = [p for p in g["positions"] if p["current_price_brl"] is not None]
        proventos_grupo = sum(
            dividends_by_ticker.get(p["ticker"], 0.0)
            for p in g["positions"]
        )
        g["proventos_grupo"] = round(proventos_grupo, 2)
        quoted_cur = sum(p["current_value"] for p in quoted_positions)
        quoted_inv = sum(p["invested_value"] for p in quoted_positions)
        previous_values: list[float] = []
        for p in quoted_positions:
            previous_price = previous_prices.get(p["ticker"])
            if previous_price is None:
                previous_values = []
                break
            price_brl = previous_price * fx_today if p.get("is_usd") else previous_price
            previous_values.append(p["quantity"] * price_brl)

        previous_value = (
            sum(previous_values)
            if quoted_positions and len(previous_values) == len(quoted_positions)
            else None
        )
        metrics = build_group_performance_metrics(
            quoted_cur,
            quoted_inv,
            previous_value,
            proventos_grupo,
        )
        g["daily_variation_value"] = metrics["daily_variation_value"]
        g["daily_variation_pct"] = metrics["daily_variation_pct"]
        g["variation_pct"] = metrics["daily_variation_pct"]
        g["variation_reference_date"] = (
            previous_reference_date
            if metrics["daily_variation_pct"] is not None
            else None
        )
        g["rentabilidade_pct"] = metrics["rentabilidade_pct"]

        g["target_pct"] = targets_map.get(g["positions"][0]["asset_type"]) if g["positions"] else None

    await cache_set(cache_key, sorted_groups, ttl=_CACHE_TTL)
    return sorted_groups


async def get_asset_distribution(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    await get_portfolio(db, portfolio_id, user_id)
    enriched = await _non_fixed_income_enriched(db, portfolio_id)
    rf_totals = await get_fixed_income_totals(db, portfolio_id)

    by_type: dict[str, float] = {}
    for e in enriched:
        at = normalize_type(e.get("asset_type")) or "OUTRO"
        val = e["current_value"] if e["current_value"] is not None else e["total_invested"]
        if val <= 0:
            continue
        by_type[at] = by_type.get(at, 0) + val

    rf_current = float(rf_totals["current_value"])
    if rf_current > 0:
        by_type[RENDA_FIXA_TYPE] = by_type.get(RENDA_FIXA_TYPE, 0) + rf_current

    return build_asset_distribution_items(by_type)


def build_asset_distribution_items(by_type: dict[str, float]) -> list[dict]:
    positive_by_type = {
        asset_type: value
        for asset_type, value in by_type.items()
        if value > 0
    }

    if not positive_by_type:
        return []

    total = sum(positive_by_type.values())
    if total <= 0:
        return []

    return [
        {
            "asset_type": at,
            "label": _TYPE_LABEL.get(at, at.replace("_", " ").title()),
            "value": round(v, 2),
            "percentage": round(v / total * 100, 4) if total else 0,
            "color": _TYPE_COLOR.get(at, "#6b7280"),
        }
        for at, v in sorted(positive_by_type.items(), key=lambda x: x[1], reverse=True)
    ]
