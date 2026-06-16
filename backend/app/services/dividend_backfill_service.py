import logging
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.transaction import Transaction
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus

logger = logging.getLogger(__name__)

# Tipos que nao possuem proventos via API
SKIP_TYPES = {"CRIPTO", "TESOURO_DIRETO", "RENDA_FIXA"}

# Tipos internacionais (yfinance)
INTL_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


async def _net_qty_on_date(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    ref_date: date,
) -> float:
    """Calcula posicao liquida (compras - vendas) do ticker na data-ex."""
    result = await db.execute(
        select(Transaction.operation, Transaction.quantity).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
            Transaction.date <= ref_date,
        )
    )
    qty = 0.0
    for op, q in result.all():
        op_str = op.value if hasattr(op, "value") else str(op)
        if op_str == "buy":
            qty += float(q)
        elif op_str == "sell":
            qty -= float(q)
    return max(qty, 0.0)


async def _portfolios_with_ticker(db: AsyncSession, ticker: str) -> list[int]:
    """Retorna lista de portfolio_ids que possuem o ticker."""
    result = await db.execute(
        select(Transaction.portfolio_id)
        .where(Transaction.ticker == ticker)
        .distinct()
    )
    return [row[0] for row in result.all()]


async def _fetch_dividends_brapi(ticker: str) -> list[dict]:
    """Busca proventos do ticker via BRAPI."""
    try:
        from app.integrations.brapi import fetch_asset_info
        info = await fetch_asset_info(ticker)
        if not info:
            return []
        dividends_raw = info.get("dividendsData", {}) or {}
        cash_dividends = dividends_raw.get("cashDividends") or []
        return cash_dividends
    except Exception as e:
        logger.warning(f"[Backfill] BRAPI erro para {ticker}: {e}")
        return []


async def _fetch_dividends_yf(ticker: str) -> list[dict]:
    """Busca proventos do ticker via yfinance."""
    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def _sync():
            import yfinance as yf
            t = yf.Ticker(ticker)
            divs = t.dividends
            if divs.empty:
                return []
            result = []
            for dt, val in divs.items():
                result.append({
                    "paymentDate": str(dt.date()),
                    "rate": float(val),
                    "type": "DIVIDENDO",
                })
            return result

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return await loop.run_in_executor(pool, _sync)
    except Exception as e:
        logger.warning(f"[Backfill] yfinance erro para {ticker}: {e}")
        return []


async def _upsert_asset_dividend(
    db: AsyncSession,
    ticker: str,
    ex_date: date,
    payment_date: Optional[date],
    value_per_unit: float,
    div_type: str,
    source: str,
) -> Optional[AssetDividend]:
    """Insere ou atualiza AssetDividend; retorna o objeto."""
    result = await db.execute(
        select(AssetDividend).where(
            AssetDividend.ticker == ticker,
            AssetDividend.ex_date == ex_date,
        )
    )
    asset_div = result.scalar_one_or_none()
    if asset_div is None:
        asset_div = AssetDividend(
            ticker=ticker,
            ex_date=ex_date,
            payment_date=payment_date,
            value_per_unit=value_per_unit,
            dividend_type=div_type,
            source=source,
        )
        db.add(asset_div)
        await db.flush()
    return asset_div


async def _upsert_portfolio_dividend(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_dividend: AssetDividend,
) -> None:
    """Insere ou atualiza Dividend para o portfolio."""
    qty = await _net_qty_on_date(db, portfolio_id, ticker, asset_dividend.ex_date)
    if qty <= 0:
        return

    result = await db.execute(
        select(Dividend).where(
            Dividend.portfolio_id == portfolio_id,
            Dividend.asset_dividend_id == asset_dividend.id,
        )
    )
    div = result.scalar_one_or_none()

    total = qty * float(asset_dividend.value_per_unit)
    div_type_str = str(asset_dividend.dividend_type or "").upper()
    net = total * 0.85 if "JCP" in div_type_str else total
    status = (
        DividendStatus.RECEBIDO
        if asset_dividend.payment_date and asset_dividend.payment_date <= date.today()
        else DividendStatus.A_RECEBER
    )

    if div is None:
        div = Dividend(
            portfolio_id=portfolio_id,
            asset_dividend_id=asset_dividend.id,
            quantity=qty,
            total_value=total,
            net_value=net,
            status=status,
        )
        db.add(div)
    else:
        div.quantity = qty
        div.total_value = total
        div.net_value = net
        div.status = status


async def backfill_dividends(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str,
) -> None:
    """
    Ponto de entrada principal do backfill.
    Chamado pelo transactions.py apos cada insercao/edicao/exclusao de transacao.
    """
    if asset_type.upper() in SKIP_TYPES:
        logger.debug(f"[Backfill] {ticker} ({asset_type}) ignorado (SKIP_TYPES)")
        return

    logger.info(f"[Backfill] iniciando para {ticker} / portfolio {portfolio_id}")

    use_yf = asset_type.upper() in INTL_TYPES
    raw_dividends = (
        await _fetch_dividends_yf(ticker)
        if use_yf
        else await _fetch_dividends_brapi(ticker)
    )

    if not raw_dividends:
        logger.info(f"[Backfill] nenhum provento encontrado para {ticker}")
        return

    for raw in raw_dividends:
        try:
            pay_str = raw.get("paymentDate") or raw.get("approvedOn") or ""
            ex_str = raw.get("lastDatePrior") or pay_str

            if not ex_str:
                continue

            ex_date = date.fromisoformat(str(ex_str)[:10])
            pay_date = date.fromisoformat(str(pay_str)[:10]) if pay_str else None
            value = float(raw.get("rate") or raw.get("value") or 0)

            if value <= 0:
                continue

            div_type = str(raw.get("type") or raw.get("dividendType") or "DIVIDENDO").upper()
            source = "yfinance" if use_yf else "brapi"

            asset_div = await _upsert_asset_dividend(
                db, ticker, ex_date, pay_date, value, div_type, source
            )

            portfolio_ids = await _portfolios_with_ticker(db, ticker)
            for pid in portfolio_ids:
                await _upsert_portfolio_dividend(db, pid, ticker, asset_div)

        except Exception as e:
            logger.warning(f"[Backfill] erro ao processar provento de {ticker}: {e}")
            continue

    await db.commit()
    logger.info(f"[Backfill] concluido para {ticker} / portfolio {portfolio_id}")


async def backfill_all_tickers(
    db: AsyncSession,
    portfolio_id: int,
    tickers: list[tuple[str, str]],
) -> list[str]:
    """
    Dispara backfill para uma lista de (ticker, asset_type).
    Usado pelo endpoint POST /dividends/sync.
    """
    queued = []
    for ticker, asset_type in tickers:
        if asset_type.upper() in SKIP_TYPES:
            continue
        await backfill_dividends(db, portfolio_id, ticker, asset_type)
        queued.append(ticker)
    return queued
