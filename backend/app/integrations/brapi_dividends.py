"""Sincroniza proventos de ativos nacionais via BRAPI."""
import httpx
from datetime import date
from sqlalchemy.orm import Session
from app.models.asset import Asset, AssetType
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.transaction import Transaction
from app.core.config import settings
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

NATIONAL_TYPES = {
    AssetType.ACAO_NACIONAL,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
}

DIVIDEND_TYPE_MAP = {
    "DIVIDENDO": DividendType.DIVIDENDO,
    "JCP": DividendType.JCP,
    "RENDIMENTO": DividendType.RENDIMENTO,
    "AMORTIZACAO": DividendType.AMORTIZACAO,
    "BONIFICACAO": DividendType.BONIFICACAO,
}


async def sync_dividends_for_portfolio(db: Session, portfolio_id: int) -> dict:
    """Busca todos os tickers nacionais da carteira e sincroniza proventos via BRAPI."""
    # Tickers nacionais distintos na carteira
    tickers = (
        db.query(Asset.ticker, Asset.id, Asset.asset_type)
        .join(Transaction, Transaction.asset_id == Asset.id)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Asset.asset_type.in_([t.value for t in NATIONAL_TYPES]),
        )
        .distinct()
        .all()
    )

    synced = 0
    errors = []

    async with httpx.AsyncClient(timeout=20) as client:
        for ticker, asset_id, asset_type in tickers:
            try:
                resp = await client.get(
                    f"{settings.BRAPI_BASE_URL}/quote/{ticker}",
                    params={"token": settings.BRAPI_TOKEN, "dividends": "true"},
                )
                resp.raise_for_status()
                data = resp.json()

                dividends_data = (
                    data.get("results", [{}])[0]
                    .get("dividendsData", {})
                    .get("cashDividends", [])
                )

                for div in dividends_data:
                    ex_date_str = div.get("lastDatePrior") or div.get("exDate")
                    pay_date_str = div.get("paymentDate")
                    value = float(div.get("rate", 0))

                    if not ex_date_str or value <= 0:
                        continue

                    ex_date = date.fromisoformat(ex_date_str[:10])
                    pay_date = date.fromisoformat(pay_date_str[:10]) if pay_date_str else None

                    # Quantidade na data-com (usa posição atual como aproximação)
                    qty = (
                        db.query(func.sum(Transaction.quantity))
                        .filter(
                            Transaction.portfolio_id == portfolio_id,
                            Transaction.asset_id == asset_id,
                            Transaction.transaction_date <= ex_date,
                        )
                        .scalar() or 0
                    )
                    if qty <= 0:
                        continue

                    total = float(qty) * value
                    # Imposto de renda: JCP retém 15%, demais tipos isentos para PF
                    div_type_raw = div.get("type", "DIVIDENDO").upper()
                    div_type = DIVIDEND_TYPE_MAP.get(div_type_raw, DividendType.OUTROS)
                    ir_rate = 0.15 if div_type == DividendType.JCP else 0.0
                    net = total * (1 - ir_rate)

                    status = (
                        DividendStatus.RECEBIDO
                        if pay_date and pay_date <= date.today()
                        else DividendStatus.A_RECEBER
                    )

                    # Upsert: evita duplicatas por asset_id + portfolio_id + ex_date
                    existing = db.query(Dividend).filter(
                        Dividend.portfolio_id == portfolio_id,
                        Dividend.asset_id == asset_id,
                        Dividend.ex_date == ex_date,
                    ).first()

                    if existing:
                        existing.value_per_unit = value
                        existing.total_value = total
                        existing.net_value = net
                        existing.status = status
                    else:
                        db.add(Dividend(
                            portfolio_id=portfolio_id,
                            asset_id=asset_id,
                            dividend_type=div_type,
                            status=status,
                            ex_date=ex_date,
                            payment_date=pay_date,
                            quantity=qty,
                            value_per_unit=value,
                            total_value=total,
                            net_value=net,
                        ))
                    synced += 1

                db.commit()

            except Exception as e:
                logger.error(f"Erro ao sincronizar proventos de {ticker}: {e}")
                errors.append({"ticker": ticker, "error": str(e)})

    return {"synced": synced, "errors": errors}
