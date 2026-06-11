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
        brapi_name=data["brapi_name"],
        invested_value=Decimal(str(data["invested_value"])),
        purchase_date=data["purchase_date"],
        maturity_date=data.get("maturity_date"),
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

    if "brapi_name" in data:
        obj.brapi_name = data["brapi_name"]
    if "invested_value" in data:
        obj.invested_value = Decimal(str(data["invested_value"]))
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
) -> None:
    obj = await get_treasury_by_id(db, investment_id, portfolio_id)
    await db.delete(obj)
    await db.commit()


# ---------- ENRIQUECIMENTO COM COTAÇÃO ATUAL (BRAPI) -------------------------

async def enrich_with_current_prices(
    investments: list[TreasuryInvestment],
) -> list[dict]:
    """
    Busca os preços atuais da BRAPI uma vez e monta a resposta com PL calculado.
    current_price = preco unitario atual do titulo.
    valor_atual   = current_price (o preco da BRAPI ja representa o valor de face atual).
    Para Tesouro Direto o valor do titulo varia por unidade;
    como o usuario cadastra valor investido (nao quantidade), usamos:
      valor_atual      = current_price  (referencia de preco atual)
      lucro_prejuizo   = None  (nao e calculavel sem quantidade)
    Se quiser P&L real, o usuario devera informar quantidade futuramente.
    """
    try:
        brapi_items = await fetch_treasury_list() or []
    except Exception:
        brapi_items = []

    # Monta mapa slug/name -> preco
    price_map: dict[str, float] = {}
    for item in brapi_items:
        slug = (item.get("slug") or item.get("symbol") or "").strip()
        name = (item.get("bondType") or item.get("name") or "").strip()
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

        result.append({
            "id": inv.id,
            "portfolio_id": inv.portfolio_id,
            "brapi_name": inv.brapi_name,
            "invested_value": float(inv.invested_value),
            "purchase_date": inv.purchase_date.isoformat() if isinstance(inv.purchase_date, date) else inv.purchase_date,
            "maturity_date": inv.maturity_date.isoformat() if isinstance(inv.maturity_date, date) else inv.maturity_date,
            "is_active": inv.is_active,
            "current_price": current_price,
            "valor_atual": None,   # necessita quantidade para calcular
            "lucro_prejuizo": None,
            "rentabilidade_pct": None,
            "created_at": inv.created_at.isoformat() if hasattr(inv, "created_at") and inv.created_at else None,
        })

    return result
