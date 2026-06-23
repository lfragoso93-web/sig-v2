import logging
from datetime import date as DateType, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, OperationType
from app.models.dividend import Dividend
from app.models.asset import Asset
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.quotes_service import get_prices
from app.services.class_target_service import get_targets_map
from app.services.fx_service import get_usd_brl_batch, get_usd_brl_today

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

# Tipos de ativos cujo preco de mercado e em USD (cotado em bolsa estrangeira)
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


# ---------------------------------------------------------------------------
# calc_raw_positions
# ---------------------------------------------------------------------------

async def calc_raw_positions(db: AsyncSession, portfolio_id: int) -> list[dict]:
    """
    Calcula posicoes brutas da carteira.

    Para transacoes em USD (STOCK/ETF_INTERNACIONAL):
      - total_cost e SEMPRE em BRL (para calculos de portfolio).
      - total_cost_usd e calculado em USD (para avg_price_usd correto).
      - Usa fx_rate salvo na transacao se disponivel e > 0.
      - Caso contrario, busca via fx_service.get_usd_brl_batch().
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date)
    )
    transactions = list(result.scalars().all())

    # Coleta datas das transacoes USD que precisam de fx_rate
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
        ticker = str(tx.ticker)
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)  # em USD para STOCK/ETF_INT
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
                "total_cost": 0.0,       # sempre em BRL
                "total_cost_usd": 0.0,   # em USD (apenas para is_usd=True)
                "asset_type": asset_type,
                "is_usd": is_usd,
            }

        s = state[ticker]

        if _is_buy(op):
            s["total_cost"] += qty * price_brl + fees_brl
            s["quantity"] += qty
            if is_usd:
                s["total_cost_usd"] += qty * price + fees  # acumula em USD
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
        # avg_price em BRL (para calculos internos de resultado)
        avg_brl = s["total_cost"] / qty if qty else 0.0
        # avg_price em USD (para exibicao quando is_usd=True)
        avg_usd = s["total_cost_usd"] / qty if qty and s["is_usd"] else None
        at = s["asset_type"]
        positions.append({
            "ticker": ticker,
            "asset_type": at,
            "asset_label": _TYPE_LABEL.get(at, at.replace("_", " ").title()),
            "quantity": qty,
            "avg_price": round(avg_brl, 8),       # BRL — interno
            "avg_price_usd": round(avg_usd, 8) if avg_usd is not None else None,  # USD — exibicao
            "total_invested": round(s["total_cost"], 8),
            "is_usd": s["is_usd"],
        })

    return positions


# ---------------------------------------------------------------------------
# enrich_with_prices
# ---------------------------------------------------------------------------

def enrich_with_prices(
    positions: list[dict],
    prices: dict[str, float],
    fx_today: float = 1.0,
) -> list[dict]:
    """
    Enriquece posicoes com cotacoes atuais e calcula resultado.

    Para ativos USD (is_usd=True):
      - current_price_usd = preco em USD (bruto do quotes_service)
      - current_price     = preco em BRL (current_price_usd * fx_today)
      - current_value     = qty * current_price (BRL)
      - result_abs/pct calculados em BRL.

    invested_value e sempre em BRL.
    """
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
            item["current_price"] = round(price_brl, 4)               # BRL
            item["current_price_usd"] = round(price_raw, 4) if is_usd else None  # USD
            item["current_value"] = round(cur_val, 2)                 # BRL
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
    ]
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


# ---------------------------------------------------------------------------
# sum_dividends
# ---------------------------------------------------------------------------

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
        return {
            row.ticker: float(row.total)
            for row in result.all()
            if row.ticker is not None and row.total is not None
        }
    except Exception as e:
        logger.warning(f"[portfolio_service] sum_dividends_by_ticker falhou: {e} — retornando {{}}")
        try:
            await db.rollback()
        except Exception:
            pass
        return {}


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

    fx_today = await get_usd_brl_today(db)

    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices, fx_today=fx_today)

    tickers_without_price = [
        e["ticker"] for e in enriched
        if e.get("current_price") is None and e["asset_type"] in _MARKET_PRICE_TYPES
    ]
    has_partial_prices = len(tickers_without_price) > 0

    current_value = 0.0
    for e in enriched:
        val = e.get("current_value")
        current_value += val if val is not None else e["total_invested"]

    cutoff_12m = (datetime.now(timezone.utc) - timedelta(days=365)).date()
    dividendos_12m = await sum_dividends(db, portfolio_id, cutoff=cutoff_12m)
    total_proventos = await sum_dividends(db, portfolio_id)

    tickers_em_carteira = [p["ticker"] for p in positions_raw]
    proventos_em_carteira = await sum_dividends_for_tickers(db, portfolio_id, tickers_em_carteira)

    total_gain = current_value - total_invested
    total_gain_pct = (total_gain / total_invested * 100) if total_invested else 0.0
    lucro_total = total_gain + proventos_em_carteira
    rentabilidade_total_pct = (lucro_total / total_invested * 100) if total_invested else 0.0

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
        "rentabilidade_total": round(rentabilidade_total_pct, 4),
        "dividendos_recebidos_12m": round(dividendos_12m, 2),
        "total_proventos": round(total_proventos, 2),
        "proventos_em_carteira": round(proventos_em_carteira, 2),
        "ganho_capital": round(total_gain, 2),
        "has_partial_prices": has_partial_prices,
        "assets_without_price": tickers_without_price,
        "usd_brl_rate": round(fx_today, 4),
    }


async def get_portfolio_positions(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    await get_portfolio(db, portfolio_id, user_id)
    positions_raw = await calc_raw_positions(db, portfolio_id)

    fx_today = await get_usd_brl_today(db)

    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices, fx_today=fx_today)

    tickers = [e["ticker"] for e in enriched]
    logos = await _fetch_logos_batch(db, tickers)
    targets_map = await get_targets_map(db, portfolio_id)

    dividends_by_ticker = await sum_dividends_by_ticker(db, portfolio_id, tickers)

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
            # Preco medio: USD para STOCK/ETF_INT, BRL para os demais
            "average_price": round(e["avg_price_usd"], 4) if (is_usd and e.get("avg_price_usd") is not None) else round(e["avg_price"], 4),
            "average_price_brl": round(e["avg_price"], 4),        # BRL — para calculos internos
            "average_price_usd": e.get("avg_price_usd"),          # USD — None para ativos BRL
            # Preco atual: USD para STOCK/ETF_INT, BRL para os demais
            "current_price": e["current_price_usd"] if (is_usd and e.get("current_price_usd") is not None) else e["current_price"],
            "current_price_brl": e["current_price"],              # BRL
            "current_price_usd": e.get("current_price_usd"),     # USD
            "current_value": e["current_value"],                  # BRL — sempre
            "invested_value": round(e["total_invested"], 2),      # BRL — sempre
            "variation_value": e["result_abs"],
            "variation_percent": e["result_pct"],
            "allocation_pct": round(alloc, 4),
            "logo_url": logos.get(e["ticker"]),
            "is_usd": is_usd,
            "currency": "USD" if is_usd else "BRL",
        })

    sorted_groups = sorted(groups.values(), key=lambda g: g["total_value"], reverse=True)
    for g in sorted_groups:
        g["total_value"] = round(g["total_value"], 2)
        g["total_invested"] = round(g["total_invested"], 2)

        quoted_positions = [p for p in g["positions"] if p["current_price_brl"] is not None]
        if quoted_positions:
            quoted_cur = sum(p["current_value"] for p in quoted_positions)
            quoted_inv = sum(p["invested_value"] for p in quoted_positions)
            g["variation_pct"] = round((quoted_cur - quoted_inv) / quoted_inv * 100, 4) if quoted_inv > 0 else None
        else:
            g["variation_pct"] = None

        proventos_grupo = sum(
            dividends_by_ticker.get(p["ticker"], 0.0)
            for p in g["positions"]
        )
        g["proventos_grupo"] = round(proventos_grupo, 2)
        if quoted_positions and quoted_inv > 0:
            quoted_gain = quoted_cur - quoted_inv
            lucro_grupo = quoted_gain + proventos_grupo
            g["rentabilidade_pct"] = round(lucro_grupo / quoted_inv * 100, 4)
        else:
            g["rentabilidade_pct"] = None

        g["target_pct"] = targets_map.get(g["positions"][0]["asset_type"]) if g["positions"] else None

    return sorted_groups


async def get_asset_distribution(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    positions_raw = await calc_raw_positions(db, portfolio_id)
    if not positions_raw:
        return []
    fx_today = await get_usd_brl_today(db)
    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices, fx_today=fx_today)

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
            "color": _TYPE_COLOR.get(at, "#6b7280"),
        }
        for at, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)
    ]
