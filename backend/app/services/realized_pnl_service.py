"""Compatibilidade pública para leitura de ganho ou prejuízo realizado.

As funções puras históricas permanecem temporariamente para consumidores e testes
que fornecem apenas transações em memória. O runtime assíncrono da aplicação usa
o projetor canônico, que incorpora eventos corporativos globais sem reconstruir
custo médio em uma trilha paralela.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.services.fixed_income_valuation_service import RENDA_FIXA_TYPE
from app.services.portfolio_service import normalize_type
from app.services.realized_pnl_projection_reader import load_realized_pnl_by_ticker

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


def calculate_realized_pnl_by_ticker(transactions: list[Transaction]) -> dict[str, float]:
    """Caracterização legada para listas isoladas, sem acesso ao catálogo global."""
    state: dict[str, dict[str, float]] = {}
    realized: dict[str, float] = {}
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
        realized.setdefault(ticker, 0.0)
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
        realized[ticker] += net_proceeds - sold_cost
        position["quantity"] = max(0.0, position["quantity"] - sold_quantity)
        position["cost"] = max(0.0, position["cost"] - sold_cost)

    return {ticker: round(value, 2) for ticker, value in realized.items()}


def calculate_realized_pnl(transactions: list[Transaction]) -> float:
    return round(sum(calculate_realized_pnl_by_ticker(transactions).values()), 2)


async def get_realized_pnl_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, float]:
    """Lê o resultado realizado pela projeção canônica compartilhada."""

    return await load_realized_pnl_by_ticker(db, portfolio_id)


async def get_realized_pnl(db: AsyncSession, portfolio_id: int) -> float:
    realized = await get_realized_pnl_by_ticker(db, portfolio_id)
    return round(sum(realized.values()), 2)
