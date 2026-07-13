"""Calculo canonico de ganho ou prejuizo realizado da carteira."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.services.fixed_income_valuation_service import RENDA_FIXA_TYPE
from app.services.portfolio_service import normalize_type

_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _operation_name(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    return str(raw or "").strip().lower()


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
    """Calcula PnL realizado por custo medio movel.

    Compras incorporam taxas ao custo. Vendas reconhecem o valor liquido recebido,
    descontando taxas, e removem o custo medio proporcional. Posicoes totalmente
    encerradas continuam contribuindo para o total realizado da carteira.

    Renda fixa permanece fora deste calculo porque seus resgates exigem separar
    principal e rendimento no servico especifico de valuation.
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
        operation = _operation_name(tx.operation)

        if operation in {OperationType.buy.value, "compra"}:
            position["quantity"] += quantity
            position["cost"] += quantity * price_brl + fees_brl
            continue

        if operation not in {OperationType.sell.value, "venda"} or position["quantity"] <= 0:
            continue

        sold_quantity = min(quantity, position["quantity"])
        average_cost = position["cost"] / position["quantity"]
        sold_cost = sold_quantity * average_cost
        net_proceeds = sold_quantity * price_brl - fees_brl

        total_realized += net_proceeds - sold_cost
        position["quantity"] = max(0.0, position["quantity"] - sold_quantity)
        position["cost"] = max(0.0, position["cost"] - sold_cost)

    return round(total_realized, 2)


async def get_realized_pnl(db: AsyncSession, portfolio_id: int) -> float:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    return calculate_realized_pnl(list(result.scalars().all()))
