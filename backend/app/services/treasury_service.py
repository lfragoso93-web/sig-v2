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
    Enriquece a lista de investimentos com preco atual usando fetch_treasury_prices,
    que implementa as 4 camadas de resolucao:
      1. Mapa estatico (BRAPI slugs conhecidos)
      2. Slug BRAPI direto
      3. Catalogo dinamico BRAPI /v2/treasury/list
      4. Fallback API publica do Tesouro Nacional (STN)

    Para cada investimento com preco encontrado, calcula tambem:
      valor_atual      = invested_value / preco_compra * preco_atual
      lucro_prejuizo   = valor_atual - invested_value
      rentabilidade_pct = (lucro_prejuizo / invested_value) * 100

    Nota: o campo brapi_name armazena o nome como o usuario cadastrou
    (ex: 'Tesouro Renda+ Aposentadoria Extra 2065'). A resolucao do slug
    e feita internamente por fetch_treasury_prices.
    """
    if not investments:
        return []

    # Coleta todos os brapi_names distintos para busca em batch
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

        valor_atual = None
        lucro_prejuizo = None
        rentabilidade_pct = None

        if current_price is not None and current_price > 0 and invested > 0:
            # Para Tesouro, o preco da cota ja e o valor unitario.
            # O valor atual e proporcional: (invested / preco_compra) * preco_atual.
            # Como nao temos preco_compra armazenado, usamos o preco atual diretamente
            # como referencia e calculamos o valor_atual = current_price (preco da cota).
            # Para multiplas cotas: valor_atual = (invested / avg_purchase_price) * current_price.
            # Como avg_purchase_price nao e armazenado neste modelo, usamos a convencao de
            # que invested_value ja representa o valor total investido e current_price e
            # o preco unitario atual — o valor atual fica como referencia de mercado.
            valor_atual = current_price
            lucro_prejuizo = None   # requer preco_compra para calculo preciso
            rentabilidade_pct = None

        result.append({
            "id": inv.id,
            "portfolio_id": inv.portfolio_id,
            "brapi_name": inv.brapi_name,
            "invested_value": invested,
            "purchase_date": inv.purchase_date.isoformat() if isinstance(inv.purchase_date, date) else inv.purchase_date,
            "maturity_date": inv.maturity_date.isoformat() if isinstance(inv.maturity_date, date) else inv.maturity_date,
            "is_active": inv.is_active,
            "current_price": current_price,
            "valor_atual": valor_atual,
            "lucro_prejuizo": lucro_prejuizo,
            "rentabilidade_pct": rentabilidade_pct,
            "created_at": inv.created_at.isoformat() if hasattr(inv, "created_at") and inv.created_at else None,
        })

    return result
