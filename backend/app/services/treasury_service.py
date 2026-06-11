from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from decimal import Decimal
from datetime import date

from app.models.treasury import TreasuryInvestment
from app.integrations.brapi import fetch_treasury_list


# ---------- CREATE -----------------------------------------------------------

async def create_treasury(
    db: AsyncSession,
    portfolio_id: int,
    data: dict,
) -> TreasuryInvestment:
    investment = TreasuryInvestment(
        portfolio_id=portfolio_id,
        treasury_type=data["treasury_type"],
        brapi_name=data["brapi_name"],
        date_purchase=data["date_purchase"],
        date_maturity=data["date_maturity"],
        quantity=Decimal(str(data["quantity"])),
        purchase_price=Decimal(str(data["purchase_price"])),
        invested_amount=Decimal(str(data["invested_amount"])),
        rate_at_purchase=Decimal(str(data["rate_at_purchase"])),
        spread_rate=Decimal(str(data["spread_rate"])) if data.get("spread_rate") is not None else None,
        is_active=data.get("is_active", True),
    )
    db.add(investment)
    await db.commit()
    await db.refresh(investment)
    return investment


# ---------- READ -------------------------------------------------------------

async def get_treasury_by_portfolio(
    db: AsyncSession,
    portfolio_id: int,
    only_active: bool = False,
) -> list[TreasuryInvestment]:
    stmt = select(TreasuryInvestment).where(
        TreasuryInvestment.portfolio_id == portfolio_id
    )
    if only_active:
        stmt = stmt.where(TreasuryInvestment.is_active == True)
    result = await db.execute(stmt.order_by(TreasuryInvestment.date_maturity))
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
        raise HTTPException(status_code=404, detail="Investimento de Tesouro não encontrado.")
    return obj


# ---------- UPDATE -----------------------------------------------------------

async def update_treasury(
    db: AsyncSession,
    investment_id: int,
    portfolio_id: int,
    data: dict,
) -> TreasuryInvestment:
    obj = await get_treasury_by_id(db, investment_id, portfolio_id)

    updatable = [
        "treasury_type", "brapi_name", "date_purchase", "date_maturity",
        "quantity", "purchase_price", "invested_amount", "rate_at_purchase",
        "spread_rate", "is_active",
    ]
    decimal_fields = {"quantity", "purchase_price", "invested_amount", "rate_at_purchase", "spread_rate"}

    for field in updatable:
        if field in data:
            value = data[field]
            if value is not None and field in decimal_fields:
                value = Decimal(str(value))
            setattr(obj, field, value)

    await db.commit()
    await db.refresh(obj)
    return obj


# ---------- DELETE -----------------------------------------------------------

async def delete_treasury(
    db: AsyncSession,
    investment_id: int,
    portfolio_id: int,
) -> None:
    obj = await get_treasury_by_id(db, investment_id, portfolio_id)
    await db.delete(obj)
    await db.commit()


# ---------- COTAÇÃO ATUAL (via BRAPI) ----------------------------------------

async def get_current_price(brapi_name: str) -> float | None:
    """
    Busca o preço atual de um título na BRAPI pelo brapi_name (slug ou nome exato).
    Retorna None se não encontrar.
    """
    try:
        items = await fetch_treasury_list()
        for item in items:
            slug = item.get("slug") or item.get("symbol") or ""
            name = item.get("bondType") or item.get("name") or ""
            if slug == brapi_name or name == brapi_name:
                price = item.get("buyPrice") or item.get("basePrice") or item.get("sellPrice")
                return float(price) if price is not None else None
    except Exception:
        pass
    return None


# ---------- ENRIQUECIMENTO DA LISTA COM COTAÇÃO ATUAL ------------------------

async def enrich_with_current_prices(
    investments: list[TreasuryInvestment],
) -> list[dict]:
    """
    Retorna uma lista de dicts com os dados do investimento + valor_atual e lucro_prejuizo.
    """
    # Busca todos os títulos da BRAPI uma vez
    try:
        brapi_items = await fetch_treasury_list() or []
    except Exception:
        brapi_items = []

    price_map: dict[str, float] = {}
    for item in brapi_items:
        slug = item.get("slug") or item.get("symbol") or ""
        name = item.get("bondType") or item.get("name") or ""
        price = item.get("buyPrice") or item.get("basePrice") or item.get("sellPrice")
        if price is not None:
            p = float(price)
            if slug:
                price_map[slug] = p
            if name:
                price_map[name] = p

    result = []
    for inv in investments:
        current_price = price_map.get(inv.brapi_name)
        quantity = float(inv.quantity)
        invested = float(inv.invested_amount)

        if current_price is not None:
            valor_atual = current_price * quantity
            lucro_prejuizo = valor_atual - invested
            rentabilidade_pct = ((valor_atual / invested) - 1) * 100 if invested else 0.0
        else:
            valor_atual = None
            lucro_prejuizo = None
            rentabilidade_pct = None

        result.append({
            "id": inv.id,
            "portfolio_id": inv.portfolio_id,
            "treasury_type": inv.treasury_type,
            "brapi_name": inv.brapi_name,
            "date_purchase": inv.date_purchase.isoformat() if isinstance(inv.date_purchase, date) else inv.date_purchase,
            "date_maturity": inv.date_maturity.isoformat() if isinstance(inv.date_maturity, date) else inv.date_maturity,
            "quantity": quantity,
            "purchase_price": float(inv.purchase_price),
            "invested_amount": invested,
            "rate_at_purchase": float(inv.rate_at_purchase),
            "spread_rate": float(inv.spread_rate) if inv.spread_rate is not None else None,
            "is_active": inv.is_active,
            "current_price": current_price,
            "valor_atual": round(valor_atual, 2) if valor_atual is not None else None,
            "lucro_prejuizo": round(lucro_prejuizo, 2) if lucro_prejuizo is not None else None,
            "rentabilidade_pct": round(rentabilidade_pct, 4) if rentabilidade_pct is not None else None,
            "created_at": inv.created_at.isoformat() if hasattr(inv, "created_at") and inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if hasattr(inv, "updated_at") and inv.updated_at else None,
        })

    return result
