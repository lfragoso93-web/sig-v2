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

# Paleta de cores fixa por classe — alinhada com o frontend (PALETTE no AssetDonutChart)
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

# Mapa de normalização para o valor canônico do enum AssetType.
# Apenas aliases legítimos de entrada externa (ex: dados históricos antigos).
# NUNCA mapear para valores fora do enum AssetType (ex: ACAO_NACIONAL não existe no enum).
_TYPE_ALIASES: dict[str, str] = {
    "ACAO_NACIONAL": "ACAO",   # alias legado → valor correto do enum
    "ACOES": "ACAO",
    "ETF_INT": "ETF_INTERNACIONAL",
    "ETF": "ETF_NACIONAL",
    "TESOURO": "TESOURO_DIRETO",
    "STOCKS": "STOCK",
    "CRIPTOMOEDA": "CRIPTO",
}


def normalize_type(asset_type) -> str:
    """
    Normaliza aliases de asset_type para o valor canônico do enum AssetType.

    Garante que o valor retornado seja sempre reconhecido por AssetType(value),
    evitando ValueError silencioso no quotes_service que causa L1 ser ignorado.

    Exemplos:
        "ACAO_NACIONAL" -> "ACAO"
        "ETF_INT"       -> "ETF_INTERNACIONAL"
        "TESOURO"       -> "TESOURO_DIRETO"
        "STOCKS"        -> "STOCK"
        "FII"           -> "FII"  (sem alias, retorna como está)
        None            -> ""
    """
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
    enriched = []
    for p in positions:
        ticker = p["ticker"]
        asset_type = p.get("asset_type", "")
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
            item["current_price"] = None
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
    """
    Soma os dividendos de um portfolio.

    Quando `cutoff` é informado, filtra apenas dividendos cujo AssetDividend.ex_date >= cutoff.
    Usa LEFT JOIN para preservar dividendos manuais (asset_dividend_id IS NULL):
      - Dividendos vinculados a um AssetDividend com ex_date >= cutoff → incluídos
      - Dividendos vinculados a um AssetDividend com ex_date < cutoff  → excluídos
      - Dividendos sem AssetDividend (manuais, asset_dividend_id IS NULL) → sempre incluídos no período
    """
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
    """
    Soma os proventos recebidos apenas para os tickers ainda em carteira.

    Usado em get_portfolio_summary para evitar superestimativa de
    rentabilidade_total_pct causada por proventos históricos de ativos
    já vendidos (cujo custo foi removido de total_invested).

    Se `tickers` for vazio, retorna 0.0 sem executar query.
    """
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
    """
    Retorna mapa {ticker: total_proventos} para os tickers fornecidos.

    Executa uma única query GROUP BY ticker, evitando N roundtrips ao banco.
    Usado em get_portfolio_positions para calcular rentabilidade_pct por grupo
    de classe de ativo (P3).

    Tickers sem proventos não aparecem no dict retornado (usar .get(ticker, 0.0)).
    Se `tickers` for vazio, retorna {} sem executar query.
    """
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

    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices)

    # P1: identifica ativos sem cotação para expor flag ao frontend
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

    # P2: rentabilidade_total usa apenas proventos dos tickers ainda em carteira,
    # evitando superestimativa por proventos históricos de ativos já vendidos.
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
        # P1: flags para o frontend exibir aviso de precificação parcial
        "has_partial_prices": has_partial_prices,
        "assets_without_price": tickers_without_price,
    }


async def get_portfolio_positions(db: AsyncSession, portfolio_id: int, user_id: int) -> list[dict]:
    await get_portfolio(db, portfolio_id, user_id)
    positions_raw = await calc_raw_positions(db, portfolio_id)

    prices = await _fetch_prices_batch(db, positions_raw)
    enriched = enrich_with_prices(positions_raw, prices)

    tickers = [e["ticker"] for e in enriched]
    logos = await _fetch_logos_batch(db, tickers)
    targets_map = await get_targets_map(db, portfolio_id)

    # P3: uma query GROUP BY ticker para todos os tickers da carteira
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
            "average_price": round(e["avg_price"], 4),
            "current_price": e["current_price"],
            "current_value": e["current_value"],
            "invested_value": round(e["total_invested"], 2),
            "variation_value": e["result_abs"],
            "variation_percent": e["result_pct"],
            "allocation_pct": round(alloc, 4),
            "logo_url": logos.get(e["ticker"]),
        })

    sorted_groups = sorted(groups.values(), key=lambda g: g["total_value"], reverse=True)
    for g in sorted_groups:
        g["total_value"] = round(g["total_value"], 2)
        g["total_invested"] = round(g["total_invested"], 2)

        # P4: variation_pct calculado apenas sobre posições com cotação real.
        quoted_positions = [p for p in g["positions"] if p["current_price"] is not None]
        if quoted_positions:
            quoted_cur = sum(p["current_value"] for p in quoted_positions)
            quoted_inv = sum(p["invested_value"] for p in quoted_positions)
            g["variation_pct"] = round((quoted_cur - quoted_inv) / quoted_inv * 100, 4) if quoted_inv > 0 else None
        else:
            g["variation_pct"] = None

        # P3: rentabilidade_pct = (ganho_capital_cotados + proventos_grupo) / custo_cotados * 100
        # Usa quoted_inv como denominador (coerente com P4 — mesmo subgrupo cotado).
        # Proventos são somados para todos os tickers do grupo (cotados + não-cotados),
        # pois proventos existem independentemente de ter cotação de mercado.
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
            "color": _TYPE_COLOR.get(at, "#6b7280"),
        }
        for at, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)
    ]
