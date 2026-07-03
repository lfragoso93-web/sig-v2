"""
Treasury service — lê posições diretamente da tabela transactions.

Cada linha de transação com asset_type = 'tesouro_direto' representa um lote de
compra de Tesouro Direto. Para cotação atual, o ticker informado pelo usuário é
resolvido para o `symbol` canônico da BRAPI usando o catálogo persistido em
assets, populado via /api/v2/treasury/list.
"""
from datetime import date
from typing import Optional
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.transaction import Transaction, OperationType
from app.models.portfolio import Portfolio
from app.integrations.brapi_treasury import fetch_treasury_prices
from app.services.treasury_catalog_service import resolve_treasury_symbol

logger = logging.getLogger(__name__)

TREASURY_ASSET_TYPES = {"tesouro_direto", "tesouro direto", "treasury", "TESOURO_DIRETO"}


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
    raw = asset_type.value if hasattr(asset_type, "value") else str(asset_type)
    return raw.strip().lower() in {item.lower() for item in TREASURY_ASSET_TYPES}


async def list_treasury(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    only_active: bool = False,
) -> list[dict]:
    await _assert_portfolio_owner(db, portfolio_id, user_id)

    stmt = select(Transaction).where(
        Transaction.portfolio_id == portfolio_id,
        Transaction.operation == OperationType.buy,
    ).order_by(Transaction.date.desc())

    result = await db.execute(stmt)
    all_txs = result.scalars().all()
    treasury_txs = [tx for tx in all_txs if _is_treasury(tx.asset_type)]
    return await enrich_with_current_prices(db, treasury_txs)


async def get_treasury_by_portfolio(
    db: AsyncSession,
    portfolio_id: int,
    only_active: bool = False,
) -> list[Transaction]:
    stmt = select(Transaction).where(
        Transaction.portfolio_id == portfolio_id,
        Transaction.operation == OperationType.buy,
    ).order_by(Transaction.date.desc())

    result = await db.execute(stmt)
    all_txs = result.scalars().all()
    return [tx for tx in all_txs if _is_treasury(tx.asset_type)]


async def enrich_with_current_prices(
    db: AsyncSession,
    transactions: list[Transaction],
) -> list[dict]:
    """Enriquece lotes de Tesouro com preço atual via BRAPI indicators."""
    if not transactions:
        return []

    symbol_by_raw: dict[str, str | None] = {}
    for tx in transactions:
        raw = str(tx.ticker or "")
        if raw not in symbol_by_raw:
            symbol_by_raw[raw] = await resolve_treasury_symbol(db, raw)

    symbols = sorted({s for s in symbol_by_raw.values() if s})
    price_map: dict[str, float] = {}
    if symbols:
        try:
            price_map = await fetch_treasury_prices(symbols)
        except Exception as exc:
            logger.warning("[treasury_service] erro ao buscar preços BRAPI: %s", exc)

    result = []
    for tx in transactions:
        purchase_price = float(tx.price)
        quantity = float(tx.quantity)
        invested_value = round(quantity * purchase_price, 2)

        raw_ticker = str(tx.ticker or "")
        brapi_symbol = symbol_by_raw.get(raw_ticker)
        current_price = price_map.get(brapi_symbol) if brapi_symbol else None
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
            "brapi_name": brapi_symbol or raw_ticker,
            "brapi_symbol": brapi_symbol,
            "ticker": raw_ticker,
            "purchase_price": purchase_price,
            "quantity": quantity,
            "invested_value": invested_value,
            "purchase_date": purchase_date.isoformat() if isinstance(purchase_date, date) else purchase_date,
            "maturity_date": None,
            "is_active": True,
            "current_price": current_price,
            "valor_atual": valor_atual,
            "lucro_prejuizo": lucro_prejuizo,
            "rentabilidade_pct": rentabilidade_pct,
            "quantidade_cotas": round(quantity, 6),
            "notes": tx.notes,
        })

    return result
