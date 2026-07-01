"""
Treasury service — lê posições diretamente da tabela transactions.

Cada linha de transação com asset_type = 'tesouro_direto' representa
um lote de compra de Tesouro Direto:
  - ticker   → brapi_name (ex: "Tesouro IPCA+ 2029")
  - price    → preço de um título cheio na data de compra
  - quantity → quantidade de cotas (pode ser fracionado, ex: 0.02)
  - quantity * price → valor investido (calculado)
  - date     → purchase_date

Cálculo de rentabilidade:
  valor_atual       = quantity * current_price
  lucro_prejuizo    = valor_atual - invested_value
  rentabilidade_pct = (lucro_prejuizo / invested_value) * 100
"""
from datetime import date
from typing import Optional
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.transaction import Transaction, OperationType
from app.models.portfolio import Portfolio
from app.integrations.brapi import fetch_treasury_prices

logger = logging.getLogger(__name__)

# Valores de asset_type reconhecidos como Tesouro Direto (case-insensitive)
TREASURY_ASSET_TYPES = {"tesouro_direto", "tesouro direto", "treasury"}


async def _assert_portfolio_owner(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> None:
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Acesso negado ao portfolio.")


def _is_treasury(asset_type: Optional[str]) -> bool:
    if not asset_type:
        return False
    return asset_type.strip().lower() in TREASURY_ASSET_TYPES


# ---------- READ -------------------------------------------------------------

async def list_treasury(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    only_active: bool = False,
) -> list[dict]:
    """
    Lista todos os lotes de Tesouro Direto de uma carteira,
    enriquecidos com cotação atual via BRAPI.

    only_active é mantido por compatibilidade de assinatura, mas
    como transações não têm is_active, retorna todas as compras (buy).
    """
    await _assert_portfolio_owner(db, portfolio_id, user_id)

    stmt = select(Transaction).where(
        Transaction.portfolio_id == portfolio_id,
        Transaction.operation == OperationType.buy,
    ).order_by(Transaction.date.desc())

    result = await db.execute(stmt)
    all_txs = result.scalars().all()

    treasury_txs = [tx for tx in all_txs if _is_treasury(tx.asset_type)]

    return await enrich_with_current_prices(treasury_txs)


async def get_treasury_by_portfolio(
    db: AsyncSession,
    portfolio_id: int,
    only_active: bool = False,
) -> list[Transaction]:
    """Retorna transações de Tesouro Direto de uma carteira (sem autenticação)."""
    stmt = select(Transaction).where(
        Transaction.portfolio_id == portfolio_id,
        Transaction.operation == OperationType.buy,
    ).order_by(Transaction.date.desc())

    result = await db.execute(stmt)
    all_txs = result.scalars().all()
    return [tx for tx in all_txs if _is_treasury(tx.asset_type)]


# ---------- ENRIQUECIMENTO COM COTAÇÃO ATUAL ---------------------------------

async def enrich_with_current_prices(
    transactions: list[Transaction],
) -> list[dict]:
    """
    Enriquece lotes de Tesouro com preço atual da BRAPI.

    Campos retornados por lote:
      id, portfolio_id, ticker (= brapi_name), purchase_price, quantity,
      invested_value, purchase_date, current_price,
      valor_atual, lucro_prejuizo, rentabilidade_pct
    """
    if not transactions:
        return []

    tickers = list({tx.ticker for tx in transactions if tx.ticker})
    price_map: dict[str, float] = {}
    if tickers:
        try:
            price_map = await fetch_treasury_prices(tickers)
        except Exception as exc:
            logger.warning("[treasury_service] erro ao buscar preços BRAPI: %s", exc)

    result = []
    for tx in transactions:
        purchase_price = float(tx.price)
        quantity = float(tx.quantity)
        invested_value = round(quantity * purchase_price, 2)

        current_price = price_map.get(tx.ticker)
        valor_atual = None
        lucro_prejuizo = None
        rentabilidade_pct = None

        if current_price is not None and current_price > 0 and invested_value > 0:
            valor_atual = round(quantity * current_price, 2)
            lucro_prejuizo = round(valor_atual - invested_value, 2)
            rentabilidade_pct = round((lucro_prejuizo / invested_value) * 100, 4)

        purchase_date = tx.date
        result.append({
            "id": tx.id,
            "portfolio_id": tx.portfolio_id,
            "brapi_name": tx.ticker,
            "ticker": tx.ticker,
            "purchase_price": purchase_price,
            "quantity": quantity,
            "invested_value": invested_value,
            "purchase_date": purchase_date.isoformat() if isinstance(purchase_date, date) else purchase_date,
            "maturity_date": None,  # não armazenado em transactions; reservado para uso futuro via notes
            "is_active": True,
            "current_price": current_price,
            "valor_atual": valor_atual,
            "lucro_prejuizo": lucro_prejuizo,
            "rentabilidade_pct": rentabilidade_pct,
            "quantidade_cotas": round(quantity, 6),
            "notes": tx.notes,
        })

    return result
