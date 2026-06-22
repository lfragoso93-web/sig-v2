"""
Servico de listagem de transacoes com paginacao e filtros.

Tambem exporta helpers sincronos de calculo de preco medio e
quantidade atual, usados por portfolio_service e pelos testes unitarios.
"""
from datetime import date as DateType
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, OperationType


# ---------------------------------------------------------------------------
# Helpers sincronos (Session normal — usados por servicos legados e testes)
# ---------------------------------------------------------------------------

def _calc_average_price(
    db: Session,
    portfolio_id: int,
    ticker: str,
) -> float:
    """
    Calcula o preco medio ponderado atual de um ativo na carteira.

    Regra:
      - Compras aumentam custo total e quantidade.
      - Vendas reduzem quantidade (pro-rata do PM vigente), sem alterar PM.
      - Se quantidade chegar a zero ou negativo, retorna 0.0.
    """
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
        )
        .order_by(Transaction.date)
        .all()
    )

    total_qty: float  = 0.0
    total_cost: float = 0.0

    for row in rows:
        if row.operation == OperationType.buy:
            total_qty  += float(row.quantity)
            total_cost += float(row.quantity) * float(row.price)
        elif row.operation == OperationType.sell:
            sold = min(float(row.quantity), total_qty)  # nunca abaixo de zero
            pm = total_cost / total_qty if total_qty > 0 else 0.0
            total_qty  -= sold
            total_cost -= sold * pm

    if total_qty <= 0:
        return 0.0
    return total_cost / total_qty


def _calc_current_quantity(
    db: Session,
    portfolio_id: int,
    ticker: str,
) -> float:
    """
    Retorna a quantidade atual do ativo na carteira (nunca negativa).
    """
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
        )
        .all()
    )

    qty: float = 0.0
    for row in rows:
        if row.operation == OperationType.buy:
            qty += float(row.quantity)
        elif row.operation == OperationType.sell:
            qty -= float(row.quantity)

    return max(0.0, qty)


# ---------------------------------------------------------------------------
# Listagem paginada async (usada pelos routers)
# ---------------------------------------------------------------------------

async def list_transactions_paginated(
    db: AsyncSession,
    portfolio_id: int,
    page: int = 1,
    page_size: int = 50,
    ticker: Optional[str] = None,
    operation: Optional[str] = None,
    date_from: Optional[DateType] = None,
    date_to: Optional[DateType] = None,
) -> dict:
    """
    Lista transacoes de uma carteira com paginacao e filtros opcionais.

    Retorna:
        {
            items: list[Transaction],
            total: int,
            page: int,
            page_size: int,
            pages: int,
        }
    """
    base = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
    )
    count_base = (
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
    )

    if ticker:
        t = ticker.strip().upper()
        base = base.where(Transaction.ticker == t)
        count_base = count_base.where(Transaction.ticker == t)

    if operation:
        try:
            op_enum = OperationType(operation.lower())
            base = base.where(Transaction.operation == op_enum)
            count_base = count_base.where(Transaction.operation == op_enum)
        except ValueError:
            pass  # filtro ignorado silenciosamente; validacao fica no router

    if date_from:
        base = base.where(Transaction.date >= date_from)
        count_base = count_base.where(Transaction.date >= date_from)

    if date_to:
        base = base.where(Transaction.date <= date_to)
        count_base = count_base.where(Transaction.date <= date_to)

    total_result = await db.execute(count_base)
    total = total_result.scalar_one()

    base = base.order_by(Transaction.date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(base)
    items = list(result.scalars().all())

    pages = max(1, -(-total // page_size))  # ceil division

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }
