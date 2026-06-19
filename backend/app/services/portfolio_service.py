import logging
from datetime import date as DateType, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.dividend import Dividend
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.quotes_service import get_prices

logger = logging.getLogger(__name__)

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


def _asset_type_str(value) -> str:
    if hasattr(value, 'value'):
        return str(value.value)
    return str(value or "").upper()


def _is_buy(op) -> bool:
    if isinstance(op, OperationType):
        return op == OperationType.buy
    return str(op).lower() in ("buy", "compra")


def _is_sell(op) -> bool:
    if isinstance(op, OperationType):
        return op == OperationType.sell
    return str(op).lower() in ("sell", "venda")


# ---------------------------------------------------------------------------
# calc_raw_positions
# ---------------------------------------------------------------------------

async def calc_raw_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date)
    )
    transactions = result.scalars().all()

    state: dict[str, dict] = {}

    for tx in transactions:
        ticker = str(tx.ticker)
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        op = tx.operation
        asset_type = _asset_type_str(tx.asset_type)

        if ticker not in state:
            state[ticker] = {"quantity": 0.0, "total_cost": 0.0, "asset_type": asset_type}

        s = state[ticker]

        if _is_buy(op):
            s["total_cost"] += qty * price + fees
            s["quantity"] += qty
        elif _is_sell(op):
            if s["quantity"] > 0:
                ratio = min(qty, s["quantity"]) / s["quantity"]
                s["total_cost"] -= s["total_cost"] * ratio
                s["quantity"] = max(0.0, s["quantity"] - qty)

    positions = []
    for ticker, s in state.items():
        qty = s["quantity"]
        if qty <= 1e-9:
            continue
        avg = s["total_cost"] / qty if qty else 0.0
        at = s["asset_type"]
        positions.append({
            "ticker": ticker,
            "asset_type": at,
            "asset_label": _TYPE_LABEL.get(at, at.replace("_", " ").title()),
            "quantity": qty,
            "avg_price": round(avg, 8),
            "total_invested": round(s["total_cost"], 8),
        })

    return positions


# ---------------------------------------------------------------------------
# enrich_with_prices
# ---------------------------------------------------------------------------

def enrich_with_prices(positions: list[dict], prices: dict[str, float]) -> list[dict]:
    """
    Enriquece posicoes com preco atual.
    Quando o preco nao esta disponivel, current_price=None e current_value=None
    para que o frontend diferencie "sem cotacao" de "vale R$ 0".
    """
    enriched = []
    for p in positions:
        ticker = p["ticker"]
        price = prices.get(ticker)
        item = dict(p)
        if price is not None:
            qty = p["quantity"]
            invested = p["total_invested"]
            cur_val = qty * price
            result_abs = cur_val - invested
            result_pct = (result_abs / invested * 100) if invested else 0.0
            item["current_price"] = price
            item["current_value"] = round(cur_val, 2)
            item["result_abs"] = round(result_abs, 2)
            item["result_pct"] = round(result_pct, 4)
        else:
            # Sem cotacao: deixa explicito como None para o schema/frontend
            item["current_price"] = None
            item["current_value"] = None
            item["result_abs"] = 0.0
            item["result_pct"] = 0.0
        enriched.append(item)
    return enriched


async def _fetch_prices_batch(db: AsyncSession, positions_raw: list[dict]) -> dict[str, float]:
    if not positions_raw:
        return {}
    price_input = [
        {"ticker": p["ticker"], "asset_type": p["asset_type"]}
        for p in positions_raw
    ]
    try:
        return await get_prices(price_input, db)
    except Exception as e:
        logger.error(f"[portfolio_service] erro ao buscar precos: {e}")
        return {}


# ---------------------------------------------------------------------------
# sum_dividends
# ---------------------------------------------------------------------------

async def sum_dividends(db: AsyncSession, portfolio_id: int, cutoff: DateType | None = None) -> float:
    from app.models.asset_dividend import AssetDividend
    q = select(func.sum(Dividend.total_value)).where(Dividend.portfolio_id == portfolio_id)
    if cutoff is not None:
        q = q.join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id).where(
            AssetDividend.ex_date >= cutoff
        )
    result = await db.execute(q)
    total = result.scalar_one_or_none()
    return float(total) if total is not None else 0.0


# ---------------------------------------------------------------------------
# CRUD de carteiras
# ---------------------------------------------------------------------------

async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at)
    )
    return list(result.scalars().all())


async def create_portfolio(db: AsyncSession, user_id: int, data: PortfolioCreate) -> Portfolio:
    portfolio = Portfolio(user_id=user_id, name=data.name, description=getattr(data, "description", None))
    db.add(portfolio)
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
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(portfolio, field, value)
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


async def delete_portfolio(db: AsyncSession, portfolio_id: int, user_id: int) -> None:
    portfolio = await get_portfolio(db, portfolio_id, user_id)
    await db.delete(portfolio)
    await db.commit()


async def get_portfolio_summary(db: AsyncSession, portfolio_id: int, user_id: int) -> dict:
    await get_portfolio(db, portfolio_id, user_id)
    positions_raw = await calc_raw_positions(db, portfolio_id)
    total_invested = sum(p["total_invested"] for p in positions_raw)

    prices = await _fetch_prices_batch(db, positions_raw)

    current_value = 0.0
    for p in positions_raw:
        price_now = prices.get(p["ticker"])
        # Fallback para total_invested quando sem preco (soma patrimonial)
        current_value += (p["quantity"] * price_now) if price_now else p["total_invested"]

    cutoff_12m = (datetime.now(timezone.utc) - timedelta(days=365)).date()
    dividendos_12m = await sum_dividends(db, portfolio_id, cutoff=cutoff_12m)
    total_proventos = await sum_dividends(db, portfolio_id)

    total_gain = current_value - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0.0
    lucro_total = total_gain + total_proventos

    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_gain": round(total_gain, 2),
        "total_gain_pct": round(total_gain_pct, 4),
        "total_patrimonio": round(current_value, 2),
        "total_investido": round(total_invested, 2),
        "lucro_total": round(lucro_total, 2),
        "variacao_valor": round(total_gain, 2),
        "variacao_percentual": round(total_gain_pct, 4),
        "rentabilidade_total": round(total_gain_pct, 4),
        "dividendos_recebidos_12m": round(dividendos_12m, 2),
        "total_proventos": round(total_proventos, 2),
        "ganho_capital": round(total_gain, 2),
    }


async def get_portfolio_positions(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    await get_portfolio(db, portfolio_id, user_id)
    positions_raw = await calc_raw_positions(db, portfolio_id)

    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices)

    # Para o calculo de alocacao, usa current_value quando disponivel, senao total_invested
    total_current = sum(
        (e["current_value"] if e["current_value"] is not None else e["total_invested"])
        for e in enriched
    )

    groups: dict[str, dict] = {}
    for idx, e in enumerate(enriched):
        at = e["asset_type"] or "OUTRO"
        label = _TYPE_LABEL.get(at, at.replace("_", " ").title())
        val_for_alloc = e["current_value"] if e["current_value"] is not None else e["total_invested"]
        alloc = (val_for_alloc / total_current * 100) if total_current else 0

        if at not in groups:
            groups[at] = {"label": label, "count": 0, "total_value": 0.0, "positions": []}

        groups[at]["count"] += 1
        groups[at]["total_value"] += val_for_alloc
        groups[at]["positions"].append({
            "id": idx + 1,  # id sintetico para chave React
            "ticker": e["ticker"],
            "asset_type": at,
            "asset_label": label,
            "quantity": round(e["quantity"], 8),
            "average_price": round(e["avg_price"], 4),
            "current_price": e["current_price"],   # None quando sem cotacao
            "current_value": e["current_value"],    # None quando sem cotacao
            "invested_value": round(e["total_invested"], 2),
            "variation_value": round(e["result_abs"] or 0, 2),
            "variation_percent": round(e["result_pct"] or 0, 4),
            "allocation_pct": round(alloc, 4),
        })

    sorted_groups = sorted(groups.values(), key=lambda g: g["total_value"], reverse=True)
    for g in sorted_groups:
        g["total_value"] = round(g["total_value"], 2)
    return sorted_groups


async def get_asset_distribution(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    positions_raw = await calc_raw_positions(db, portfolio_id)
    if not positions_raw:
        return []
    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices)

    by_type: dict[str, float] = {}
    for e in enriched:
        at = e.get("asset_type") or "OUTRO"
        val = e["current_value"] if e["current_value"] is not None else e["total_invested"]
        by_type[at] = by_type.get(at, 0) + val

    total = sum(by_type.values())
    return [
        {
            "asset_type": at,
            "label": _TYPE_LABEL.get(at, at.replace("_", " ").title()),
            "value": round(v, 2),
            "percentage": round(v / total * 100, 4) if total else 0,
        }
        for at, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)
    ]
