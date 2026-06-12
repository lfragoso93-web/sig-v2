"""
dividend_backfill_service.py
----------------------------
Busca histórico completo de proventos ao cadastrar uma transação e persiste
no banco com upsert idempotente por (portfolio_id, asset_id, ex_date).

Fontes por tipo:
  ACAO / FII / ETF_NACIONAL  → BRAPI  /quote/{ticker}?dividends=true
  STOCK / ETF_INTERNACIONAL  → yfinance ticker.dividends
  CRIPTO / TESOURO / RENDA_FIXA → ignorado (sem proventos em caixa)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import httpx
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.asset import Asset, AssetType
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.transaction import Transaction

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

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


# ── Helpers internos ──────────────────────────────────────────────────────────

def _net(total: float, div_type: DividendType) -> float:
    """Aplica IR: 15% em JCP, 0% nos demais (simplificado)."""
    return total * (0.85 if div_type == DividendType.JCP else 1.0)


def _status(payment_date: date | None) -> DividendStatus:
    return (
        DividendStatus.RECEBIDO
        if payment_date and payment_date <= date.today()
        else DividendStatus.A_RECEBER
    )


async def _resolve_asset_id(db: AsyncSession, ticker: str, asset_type: AssetType) -> int | None:
    """Retorna o asset_id pelo ticker+type, ou None se não encontrado."""
    result = await db.execute(
        select(Asset.id).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    return result.scalar_one_or_none()


async def _net_qty(
    db: AsyncSession,
    portfolio_id: int,
    asset_id: int,
    ex_date: date,
) -> float:
    """Quantidade líquida (compras − vendas) antes ou na data-ex."""
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
    return max(qty, 0.0)


async def _upsert(
    db: AsyncSession,
    *,
    portfolio_id: int,
    asset_id: int,
    div_type: DividendType,
    ex_date: date,
    payment_date: date | None,
    value_per_unit: float,
    quantity: float,
) -> None:
    """Insere ou atualiza um provento. Chave: (portfolio_id, asset_id, ex_date)."""
    if quantity <= 0 or value_per_unit <= 0:
        return

    total = quantity * value_per_unit
    net   = _net(total, div_type)
    st    = _status(payment_date)

    result = await db.execute(
        select(Dividend).where(
            Dividend.portfolio_id == portfolio_id,
            Dividend.asset_id     == asset_id,
            Dividend.ex_date      == ex_date,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value_per_unit = value_per_unit
        existing.total_value    = total
        existing.net_value      = net
        existing.status         = st
        existing.quantity       = quantity
        existing.payment_date   = payment_date
    else:
        db.add(Dividend(
            portfolio_id   = portfolio_id,
            asset_id       = asset_id,
            dividend_type  = div_type,
            status         = st,
            ex_date        = ex_date,
            payment_date   = payment_date,
            quantity       = quantity,
            value_per_unit = value_per_unit,
            total_value    = total,
            net_value      = net,
        ))


# ── Backfill BRAPI (nacionais) ────────────────────────────────────────────────

async def _backfill_brapi(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_id: int,
) -> int:
    """Retorna quantidade de registros sincronizados."""
    synced = 0
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{settings.BRAPI_BASE_URL}/quote/{ticker}",
                params={"token": settings.BRAPI_TOKEN, "dividends": "true"},
            )
            resp.raise_for_status()
            data = resp.json()

        cash_divs = (
            data.get("results", [{}])[0]
            .get("dividendsData", {})
            .get("cashDividends", [])
        )

        for raw in cash_divs:
            ex_str  = raw.get("lastDatePrior") or raw.get("exDate")
            pay_str = raw.get("paymentDate")
            value   = float(raw.get("rate", 0) or 0)

            if not ex_str or value <= 0:
                continue

            ex_date      = date.fromisoformat(ex_str[:10])
            payment_date = date.fromisoformat(pay_str[:10]) if pay_str else None
            div_type_raw = raw.get("type", "DIVIDENDO").upper()
            div_type     = BRAPI_TYPE_MAP.get(div_type_raw, DividendType.OUTROS)

            qty = await _net_qty(db, portfolio_id, asset_id, ex_date)

            await _upsert(
                db,
                portfolio_id   = portfolio_id,
                asset_id       = asset_id,
                div_type       = div_type,
                ex_date        = ex_date,
                payment_date   = payment_date,
                value_per_unit = value,
                quantity       = qty,
            )
            synced += 1

        await db.commit()

    except Exception as exc:
        logger.error("backfill BRAPI %s: %s", ticker, exc)
        await db.rollback()

    return synced


# ── Backfill yfinance (internacionais) ────────────────────────────────────────

async def _backfill_yfinance(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_id: int,
) -> int:
    """Retorna quantidade de registros sincronizados."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def _fetch() -> list[tuple[date, float]]:
        try:
            info = yf.Ticker(ticker)
            divs = info.dividends  # pandas Series, index=DatetimeIndex
            if divs is None or divs.empty:
                return []
            return [(d.date(), float(v)) for d, v in divs.items()]
        except Exception as e:
            logger.warning("yfinance dividends %s: %s", ticker, e)
            return []

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        rows = await loop.run_in_executor(pool, _fetch)

    synced = 0
    try:
        for ex_date, value in rows:
            if value <= 0:
                continue

            qty = await _net_qty(db, portfolio_id, asset_id, ex_date)

            await _upsert(
                db,
                portfolio_id   = portfolio_id,
                asset_id       = asset_id,
                div_type       = DividendType.DIVIDENDO,
                ex_date        = ex_date,
                payment_date   = ex_date,   # yfinance não separa ex/pay; usa mesma data
                value_per_unit = value,
                quantity       = qty,
            )
            synced += 1

        await db.commit()

    except Exception as exc:
        logger.error("backfill yfinance %s: %s", ticker, exc)
        await db.rollback()

    return synced


# ── Entry point público ───────────────────────────────────────────────────────

async def backfill_dividends(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str | AssetType,
) -> None:
    """
    Chamado como BackgroundTask após criar/deletar uma transação.
    Busca histórico completo e faz upsert idempotente no banco.
    Silencioso em caso de erro — nunca deve quebrar a request principal.
    """
    try:
        atype = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
    except ValueError:
        logger.warning("backfill_dividends: asset_type desconhecido '%s'", asset_type)
        return

    if atype in SKIP_TYPES:
        return  # cripto, tesouro e renda fixa não têm proventos em caixa

    asset_id = await _resolve_asset_id(db, ticker, atype)
    if asset_id is None:
        logger.warning("backfill_dividends: asset não encontrado ticker=%s type=%s", ticker, atype)
        return

    if atype in BRAPI_TYPES:
        count = await _backfill_brapi(db, portfolio_id, ticker, asset_id)
    else:
        count = await _backfill_yfinance(db, portfolio_id, ticker, asset_id)

    logger.info(
        "backfill_dividends concluído: portfolio=%s ticker=%s type=%s registros=%s",
        portfolio_id, ticker, atype.value, count,
    )
