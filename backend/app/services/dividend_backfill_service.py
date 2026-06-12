"""
dividend_backfill_service.py
----------------------------
Fluxo:
  1. Busca proventos da fonte (BRAPI / yfinance) para um ticker.
  2. Faz upsert idempotente em asset_dividends (global por ativo).
  3. Para cada carteira que possui o ativo na data-ex,
     cria/atualiza um Dividend com a quantidade correta.

Fontes:
  ACAO / FII / ETF_NACIONAL  -> BRAPI  /quote/{ticker}?dividends=true
  STOCK / ETF_INTERNACIONAL  -> yfinance ticker.dividends
  CRIPTO / TESOURO / RENDA_FIXA -> ignorado
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.asset import Asset, AssetType
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Tipos suportados
BRAPI_TYPES = {AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL}
YF_TYPES    = {AssetType.STOCK, AssetType.ETF_INTERNACIONAL}
SKIP_TYPES  = {AssetType.CRIPTO, AssetType.TESOURO_DIRETO, AssetType.RENDA_FIXA}

BRAPI_TYPE_MAP: dict[str, DividendType] = {
    "DIVIDENDO":   DividendType.DIVIDENDO,
    "JCP":         DividendType.JCP,
    "RENDIMENTO":  DividendType.RENDIMENTO,
    "AMORTIZACAO": DividendType.AMORTIZACAO,
    "BONIFICACAO": DividendType.BONIFICACAO,
}


# -- helpers internos ----------------------------------------------------------

def _net(total: Decimal, div_type: DividendType) -> Decimal:
    """Aplica IR: 15% em JCP, 0% nos demais (simplificado)."""
    factor = Decimal("0.85") if div_type == DividendType.JCP else Decimal("1.0")
    return (total * factor).quantize(Decimal("0.01"))


def _status(payment_date: date | None) -> DividendStatus:
    return (
        DividendStatus.RECEBIDO
        if payment_date and payment_date <= date.today()
        else DividendStatus.A_RECEBER
    )


async def _get_or_create_asset(
    db: AsyncSession, ticker: str, asset_type: AssetType
) -> Asset:
    result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = Asset(ticker=ticker, name=ticker, asset_type=asset_type)
        db.add(asset)
        await db.flush()
    return asset


async def _upsert_asset_dividend(
    db: AsyncSession,
    asset_id: int,
    ex_date: date,
    payment_date: date | None,
    dividend_type: DividendType,
    value_per_unit: float,
    source: str,
) -> AssetDividend:
    """
    INSERT asset_dividend ON CONFLICT UPDATE value_per_unit / payment_date.
    Retorna o objeto persistido.
    """
    stmt = (
        pg_insert(AssetDividend)
        .values(
            asset_id=asset_id,
            ex_date=ex_date,
            payment_date=payment_date,
            dividend_type=dividend_type.value,
            value_per_unit=Decimal(str(round(value_per_unit, 8))),
            source=source,
        )
        .on_conflict_do_update(
            constraint="uq_asset_dividend_asset_exdate_type",
            set_={
                "value_per_unit": Decimal(str(round(value_per_unit, 8))),
                "payment_date": payment_date,
                "source": source,
            },
        )
        .returning(AssetDividend.id)
    )
    result = await db.execute(stmt)
    asset_div_id = result.scalar_one()
    await db.flush()
    # Recarrega objeto
    ad = await db.get(AssetDividend, asset_div_id)
    return ad


async def _net_qty_on_date(
    db: AsyncSession,
    portfolio_id: int,
    asset_id: int,
    ex_date: date,
) -> float:
    """Quantidade liquida (compras - vendas) antes ou na data-ex."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_id == asset_id,
            Transaction.date <= ex_date,
        )
    )
    txs = result.scalars().all()
    qty = sum(
        t.quantity if t.operation in ("compra", "buy") else -t.quantity
        for t in txs
    )
    return max(float(qty), 0.0)


async def _portfolios_with_asset(
    db: AsyncSession, asset_id: int
) -> list[int]:
    """Retorna portfolio_ids que possuem o ativo (qualquer transacao)."""
    result = await db.execute(
        select(Transaction.portfolio_id)
        .where(Transaction.asset_id == asset_id)
        .distinct()
    )
    return [r for r in result.scalars().all()]


async def _upsert_portfolio_dividend(
    db: AsyncSession,
    portfolio_id: int,
    asset_dividend: AssetDividend,
    quantity: float,
) -> None:
    """Cria ou atualiza Dividend de carteira a partir do AssetDividend."""
    if quantity <= 0:
        return

    total = (Decimal(str(quantity)) * asset_dividend.value_per_unit).quantize(Decimal("0.01"))
    net   = _net(total, asset_dividend.dividend_type)
    st    = _status(asset_dividend.payment_date)

    stmt = (
        pg_insert(Dividend)
        .values(
            portfolio_id=portfolio_id,
            asset_dividend_id=asset_dividend.id,
            quantity=quantity,
            total_value=total,
            net_value=net,
            status=st.value,
        )
        .on_conflict_do_update(
            constraint="uq_dividend_portfolio_asset_dividend",
            set_={
                "quantity": quantity,
                "total_value": total,
                "net_value": net,
                "status": st.value,
            },
        )
    )
    await db.execute(stmt)


# -- processamento de proventos brutas ----------------------------------------

async def _process_raw_dividends(
    db: AsyncSession,
    asset: Asset,
    raw_dividends: list[dict],  # [{ex_date, payment_date, value_per_unit, dividend_type, source}]
) -> int:
    """
    Para cada provento bruto:
    1. Upsert em asset_dividends
    2. Para cada carteira com o ativo, upsert em dividends
    Retorna total de registros em asset_dividends processados.
    """
    portfolio_ids = await _portfolios_with_asset(db, asset.id)
    synced = 0

    for raw in raw_dividends:
        ex_date      = raw["ex_date"]
        payment_date = raw.get("payment_date")
        value        = float(raw["value_per_unit"])
        div_type     = raw["dividend_type"]
        source       = raw.get("source", "brapi")

        if value <= 0:
            continue

        ad = await _upsert_asset_dividend(
            db, asset.id, ex_date, payment_date, div_type, value, source
        )

        for pid in portfolio_ids:
            qty = await _net_qty_on_date(db, pid, asset.id, ex_date)
            await _upsert_portfolio_dividend(db, pid, ad, qty)

        synced += 1

    await db.commit()
    return synced


# -- fontes: BRAPI -------------------------------------------------------------

async def _fetch_brapi(
    db: AsyncSession, asset: Asset
) -> int:
    ticker = asset.brapi_ticker or asset.ticker
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{settings.BRAPI_BASE_URL}/quote/{ticker}",
                params={"token": settings.BRAPI_TOKEN, "dividends": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("BRAPI fetch dividends %s: %s", ticker, exc)
        return 0

    cash_divs = (
        data.get("results", [{}])[0]
        .get("dividendsData", {})
        .get("cashDividends", [])
    )

    raw: list[dict] = []
    for item in cash_divs:
        ex_str  = item.get("lastDatePrior") or item.get("exDate")
        pay_str = item.get("paymentDate")
        value   = float(item.get("rate", 0) or 0)
        if not ex_str or value <= 0:
            continue

        div_type_raw = item.get("type", "DIVIDENDO").upper()
        div_type     = BRAPI_TYPE_MAP.get(div_type_raw, DividendType.OUTROS)

        raw.append({
            "ex_date":      date.fromisoformat(ex_str[:10]),
            "payment_date": date.fromisoformat(pay_str[:10]) if pay_str else None,
            "value_per_unit": value,
            "dividend_type": div_type,
            "source": "brapi",
        })

    return await _process_raw_dividends(db, asset, raw)


# -- fontes: yfinance ----------------------------------------------------------

async def _fetch_yfinance(
    db: AsyncSession, asset: Asset
) -> int:
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    ticker = asset.ticker

    def _sync() -> list[tuple[date, float]]:
        try:
            info = yf.Ticker(ticker)
            divs = info.dividends
            if divs is None or divs.empty:
                return []
            return [(d.date(), float(v)) for d, v in divs.items()]
        except Exception as e:
            logger.warning("yfinance dividends %s: %s", ticker, e)
            return []

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        rows = await loop.run_in_executor(pool, _sync)

    raw = [
        {
            "ex_date":       ex_date,
            "payment_date":  ex_date,
            "value_per_unit": value,
            "dividend_type": DividendType.DIVIDENDO,
            "source": "yfinance",
        }
        for ex_date, value in rows
        if value > 0
    ]

    return await _process_raw_dividends(db, asset, raw)


# -- entry point publico -------------------------------------------------------

async def backfill_dividends(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str | AssetType,
) -> None:
    """
    Chamado como BackgroundTask apos criar/deletar uma transacao.
    Busca historico completo, faz upsert em asset_dividends e gera
    Dividends para todas as carteiras com o ativo.
    Silencioso em caso de erro.
    """
    try:
        atype = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
    except ValueError:
        logger.warning("backfill_dividends: asset_type desconhecido '%s'", asset_type)
        return

    if atype in SKIP_TYPES:
        return

    try:
        asset = await _get_or_create_asset(db, ticker, atype)

        if atype in BRAPI_TYPES:
            count = await _fetch_brapi(db, asset)
        elif atype in YF_TYPES:
            count = await _fetch_yfinance(db, asset)
        else:
            count = 0

        logger.info(
            "backfill_dividends: portfolio=%s ticker=%s type=%s asset_divs=%s",
            portfolio_id, ticker, atype.value, count,
        )
    except Exception as exc:
        logger.error("backfill_dividends inesperado %s: %s", ticker, exc)
        await db.rollback()
