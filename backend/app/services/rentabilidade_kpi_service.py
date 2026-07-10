"""Composicao dos KPIs exibidos na pagina Rentabilidade.

Os valores atuais da carteira vêm da mesma fonte canônica usada por Resumo e
Patrimônio. Ganho realizado e retornos por período são calculados aqui a partir
das transações e da evolução patrimonial automática.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services.portfolio_snapshot_service import get_daily_evolution
from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.portfolio_service import normalize_type
from app.services.fixed_income_valuation_service import RENDA_FIXA_TYPE

_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _operation_name(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    return str(raw or "").strip().lower()


def _is_buy(value: object) -> bool:
    return _operation_name(value) in {"buy", "compra"}


def _is_sell(value: object) -> bool:
    return _operation_name(value) in {"sell", "venda"}


def _asset_type_name(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    return normalize_type(str(raw or ""))


def _transaction_fx_rate(tx: Transaction) -> float:
    asset_type = _asset_type_name(tx.asset_type)
    currency = str(getattr(tx, "currency", "BRL") or "BRL").upper()
    is_usd = currency == "USD" or asset_type in _USD_ASSET_TYPES
    if not is_usd:
        return 1.0

    saved = getattr(tx, "fx_rate", None)
    if saved is not None and float(saved or 0) > 0:
        return float(saved)
    return 1.0


def calculate_realized_pnl(transactions: list[Transaction]) -> float:
    """Calcula PnL realizado por custo médio móvel.

    A venda reduz o custo contábil proporcional da posição e reconhece como
    resultado o valor líquido vendido menos esse custo. Taxas da venda reduzem
    o ganho realizado.
    """
    state: dict[str, dict[str, float]] = {}
    total_realized = 0.0

    ordered = sorted(
        transactions,
        key=lambda tx: (getattr(tx, "date", date.min), getattr(tx, "id", 0) or 0),
    )

    for tx in ordered:
        if _asset_type_name(tx.asset_type) == RENDA_FIXA_TYPE:
            continue

        ticker = str(tx.ticker or "").upper().strip()
        if not ticker:
            continue

        quantity = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)
        fx_rate = _transaction_fx_rate(tx)
        price_brl = price * fx_rate
        fees_brl = fees * fx_rate

        position = state.setdefault(ticker, {"quantity": 0.0, "cost": 0.0})

        if _is_buy(tx.operation):
            position["quantity"] += quantity
            position["cost"] += quantity * price_brl + fees_brl
            continue

        if not _is_sell(tx.operation) or position["quantity"] <= 0:
            continue

        sold_quantity = min(quantity, position["quantity"])
        average_cost = position["cost"] / position["quantity"]
        sold_cost = sold_quantity * average_cost
        net_proceeds = sold_quantity * price_brl - fees_brl

        total_realized += net_proceeds - sold_cost
        position["quantity"] = max(0.0, position["quantity"] - sold_quantity)
        position["cost"] = max(0.0, position["cost"] - sold_cost)

    return round(total_realized, 2)


async def _load_transactions(db: AsyncSession, portfolio_id: int) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    return list(result.scalars().all())


def _period_return(
    points: list[dict],
    target_date: date,
    current_market_value: float,
    current_total_pnl: float,
) -> float:
    """Calcula retorno no período usando o último ponto anterior à referência."""
    if not points:
        return 0.0

    parsed: list[tuple[date, dict]] = []
    for point in points:
        try:
            parsed.append((date.fromisoformat(str(point["date"])[:10]), point))
        except (KeyError, TypeError, ValueError):
            continue

    if not parsed:
        return 0.0

    parsed.sort(key=lambda item: item[0])
    candidates = [item for item in parsed if item[0] <= target_date]
    baseline = candidates[-1][1] if candidates else parsed[0][1]

    baseline_market = float(
        baseline.get("market_value")
        or baseline.get("invested_total")
        or baseline.get("cost_basis")
        or 0
    )
    if baseline_market <= 0:
        return 0.0

    baseline_pnl = float(baseline.get("total_pnl") or 0)
    return round((current_total_pnl - baseline_pnl) / baseline_market * 100, 4)


async def get_rentabilidade_kpis(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna KPIs atuais canônicos combinados com métricas históricas."""
    summary = await get_canonical_portfolio_summary(db, portfolio_id, user_id)
    transactions = await _load_transactions(db, portfolio_id)
    realized_pnl = calculate_realized_pnl(transactions)

    today = date.today()
    month_reference = today.replace(day=1) - timedelta(days=1)
    twelve_month_reference = today - timedelta(days=365)

    # Quando snapshots recentes não existem, get_daily_evolution usa o fallback
    # automático baseado em transações e histórico de preços.
    month_points = await get_daily_evolution(db, portfolio_id, days=45)
    year_points = await get_daily_evolution(db, portfolio_id, days=370)

    current_market_value = float(summary["total_patrimonio"])
    current_total_pnl = float(summary["ganho_capital"]) + realized_pnl

    return {
        # Valores atuais: mesma fonte de Resumo e Patrimônio.
        "patrimonio_atual": summary["total_patrimonio"],
        "custo_total": summary["total_investido"],
        "total_aportado": summary["total_investido"],
        "ganho_nao_realizado": summary["ganho_capital"],
        "total_pnl": summary["lucro_total"],
        "retorno_total_pct": summary["rentabilidade_total"],
        "retorno_desde_inicio_pct": summary["rentabilidade_total"],
        "proventos_total": summary["total_proventos"],
        "proventos_12m": summary["dividendos_recebidos_12m"],
        # Métricas específicas de rentabilidade.
        "ganho_realizado": realized_pnl,
        "retorno_dia_pct": 0.0,
        "retorno_mes_pct": _period_return(
            month_points,
            month_reference,
            current_market_value,
            current_total_pnl,
        ),
        "retorno_12m_pct": _period_return(
            year_points,
            twelve_month_reference,
            current_market_value,
            current_total_pnl,
        ),
        "snapshot_date": today.isoformat(),
    }
