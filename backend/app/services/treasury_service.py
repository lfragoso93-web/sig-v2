from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from decimal import Decimal
from datetime import date
from typing import Any

from app.models.treasury import TreasuryInvestment
from app.integrations.brapi import fetch_treasury_prices


# ---------- helpers ----------------------------------------------------------

async def _assert_portfolio_owner(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> None:
    """Valida que o portfolio pertence ao user. Lanca 403 se nao."""
    from app.models.portfolio import Portfolio
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Acesso negado ao portfolio.")


# ---------- CREATE -----------------------------------------------------------

async def create_treasury(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    data: Any,
) -> TreasuryInvestment:
    await _assert_portfolio_owner(db, portfolio_id, user_id)
    payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
    investment = TreasuryInvestment(
        portfolio_id=portfolio_id,
        brapi_name=payload["brapi_name"],
        invested_value=Decimal(str(payload["invested_value"])),
        purchase_price=Decimal(str(payload["purchase_price"])) if payload.get("purchase_price") else None,
        purchase_date=payload["purchase_date"],
        maturity_date=payload.get("maturity_date"),
        is_active=payload.get("is_active", True),
    )
    db.add(investment)
    await db.commit()
    await db.refresh(investment)
    return investment


# ---------- READ -------------------------------------------------------------

async def list_treasury(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    only_active: bool = False,
) -> list[dict]:
    """Lista os investimentos de Tesouro Direto de uma carteira, enriquecidos com cotacao atual."""
    await _assert_portfolio_owner(db, portfolio_id, user_id)
    investments = await get_treasury_by_portfolio(db, portfolio_id, only_active)
    return await enrich_with_current_prices(investments)


async def get_treasury_by_portfolio(
    db: AsyncSession,
    portfolio_id: int,
    only_active: bool = False,
) -> list[TreasuryInvestment]:
    stmt = select(TreasuryInvestment).where(
        TreasuryInvestment.portfolio_id == portfolio_id
    )
    if only_active:
        stmt = stmt.where(TreasuryInvestment.is_active.is_(True))
    result = await db.execute(stmt.order_by(TreasuryInvestment.maturity_date))
    return list(result.scalars().all())


async def get_treasury_by_id(
    db: AsyncSession,
    investment_id: int,
    portfolio_id: int,
) -> TreasuryInvestment:
    stmt = select(TreasuryInvestment).where(
        TreasuryInvestment.id == investment_id,
        TreasuryInvestment.portfolio_id == portfolio_id,
    )
    result = await db.execute(stmt)
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Investimento de Tesouro n\u00e3o encontrado.")
    return obj


# ---------- UPDATE -----------------------------------------------------------

async def update_treasury(
    db: AsyncSession,
    investment_id: int,
    portfolio_id: int,
    data: dict,
) -> TreasuryInvestment:
    obj = await get_treasury_by_id(db, investment_id, portfolio_id)

    if "brapi_name" in data:
        obj.brapi_name = data["brapi_name"]
    if "invested_value" in data:
        obj.invested_value = Decimal(str(data["invested_value"]))
    if "purchase_price" in data and data["purchase_price"] is not None:
        obj.purchase_price = Decimal(str(data["purchase_price"]))
    if "purchase_date" in data:
        obj.purchase_date = data["purchase_date"]
    if "maturity_date" in data:
        obj.maturity_date = data["maturity_date"]
    if "is_active" in data:
        obj.is_active = data["is_active"]

    await db.commit()
    await db.refresh(obj)
    return obj


# ---------- DELETE -----------------------------------------------------------

async def delete_treasury(
    db: AsyncSession,
    investment_id: int,
    portfolio_id: int,
    user_id: int | None = None,
) -> None:
    if user_id is not None:
        await _assert_portfolio_owner(db, portfolio_id, user_id)
    obj = await get_treasury_by_id(db, investment_id, portfolio_id)
    await db.delete(obj)
    await db.commit()


# ---------- ENRIQUECIMENTO COM COTACAO ATUAL ---------------------------------

async def enrich_with_current_prices(
    investments: list[TreasuryInvestment],
) -> list[dict]:
    """
    Enriquece a lista de investimentos com preco atual usando fetch_treasury_prices.

    Logica de calculo com purchase_price:
      quantidade_cotas  = invested_value / purchase_price
      valor_atual       = quantidade_cotas * current_price
      lucro_prejuizo    = valor_atual - invested_value
      rentabilidade_pct = (lucro_prejuizo / invested_value) * 100

    Fallback (sem purchase_price):
      valor_atual = current_price  (preco unitario de mercado como referencia)
      lucro_prejuizo e rentabilidade_pct ficam None
    """
    if not investments:
        return []

    tickers = list({inv.brapi_name for inv in investments if inv.brapi_name})
    price_map: dict[str, float] = {}
    if tickers:
        try:
            price_map = await fetch_treasury_prices(tickers)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "[treasury_service] enrich_with_current_prices erro: %s", e
            )

    result = []
    for inv in investments:
        current_price = price_map.get(inv.brapi_name)
        invested = float(inv.invested_value)
        purchase_price = float(inv.purchase_price) if inv.purchase_price else None

        valor_atual = None
        lucro_prejuizo = None
        rentabilidade_pct = None
        quantidade_cotas = None

        if current_price is not None and current_price > 0 and invested > 0:
            if purchase_price and purchase_price > 0:
                # Calculo preciso via quantidade de cotas
                quantidade_cotas = invested / purchase_price
                valor_atual = quantidade_cotas * current_price
                lucro_prejuizo = valor_atual - invested
                rentabilidade_pct = (lucro_prejuizo / invested) * 100
            else:
                # Fallback: exibe apenas o preco unitario atual como referencia
                valor_atual = current_price

        result.append({
            "id": inv.id,
            "portfolio_id": inv.portfolio_id,
            "brapi_name": inv.brapi_name,
            "invested_value": invested,
            "purchase_price": purchase_price,
            "purchase_date": inv.purchase_date.isoformat() if isinstance(inv.purchase_date, date) else inv.purchase_date,
            "maturity_date": inv.maturity_date.isoformat() if isinstance(inv.maturity_date, date) else inv.maturity_date,
            "is_active": inv.is_active,
            "current_price": current_price,
            "valor_atual": round(valor_atual, 2) if valor_atual is not None else None,
            "lucro_prejuizo": round(lucro_prejuizo, 2) if lucro_prejuizo is not None else None,
            "rentabilidade_pct": round(rentabilidade_pct, 4) if rentabilidade_pct is not None else None,
            "quantidade_cotas": round(quantidade_cotas, 6) if quantidade_cotas is not None else None,
            "created_at": inv.created_at.isoformat() if hasattr(inv, "created_at") and inv.created_at else None,
        })

    return result
