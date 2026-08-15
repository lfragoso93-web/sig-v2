import logging
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
from app.integrations.brapi import BRAPI_BASE, _auth_headers
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.services.dividend_event_normalizer import parse_dividend_event

logger = logging.getLogger(__name__)

SKIP_TYPES = {"CRIPTO", "TESOURO_DIRETO", "RENDA_FIXA"}
INTL_TYPES = {"STOCK", "ETF_INTERNACIONAL"}
FII_TYPES = {"FII"}


def _dividend_type_from_value(value) -> DividendType:
    if isinstance(value, DividendType):
        return value
    raw = value.value if hasattr(value, "value") else str(value or "")
    raw = raw.replace("DividendType.", "")
    try:
        return DividendType(raw)
    except ValueError:
        return DividendType.OUTROS


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _extract_brapi_events(
    entry: dict, default_category: str | None = None
) -> list[dict]:
    data = entry.get("data") if isinstance(entry.get("data"), dict) else entry
    events: list[dict] = []

    for category, keys in (
        (
            default_category or "cash",
            (
                "cashDividends",
                "dividends",
                "provents",
                "income",
                "incomes",
                "earnings",
                "results",
            ),
        ),
        ("stock", ("stockDividends", "stock_dividends")),
        ("subscription", ("subscriptions",)),
    ):
        raw_items: list[Any] = []
        for key in keys:
            raw_items.extend(_as_list(data.get(key)))
        for item in raw_items:
            if isinstance(item, dict):
                enriched = dict(item)
                enriched.setdefault("eventCategory", category)
                events.append(enriched)

    # Alguns retornos de FII vêm como lista direta dentro de data/results, sem
    # wrapper por ticker nem chave dividends/cashDividends.
    if not events and any(
        k in data for k in ("paymentDate", "lastDatePrior", "rate", "value", "amount")
    ):
        enriched = dict(data)
        enriched.setdefault("eventCategory", default_category or "cash")
        events.append(enriched)

    return events


def _iter_brapi_result_entries(data: dict, ticker: str) -> list[dict]:
    ticker_upper = ticker.upper()
    entries: list[dict] = []

    for key in ("results", "stocks", "fiis", "dividends", "data"):
        value = data.get(key)
        if isinstance(value, list):
            entries.extend([item for item in value if isinstance(item, dict)])
        elif isinstance(value, dict):
            entries.append(value)

    if not entries and isinstance(data, dict):
        entries.append(data)

    filtered: list[dict] = []
    for entry in entries:
        symbol = (
            entry.get("symbol")
            or entry.get("ticker")
            or entry.get("stock")
            or entry.get("fii")
            or entry.get("code")
            or entry.get("asset")
            or ""
        ).upper()
        if symbol and symbol != ticker_upper:
            continue
        filtered.append(entry)
    return filtered


async def _fetch_dividends_brapi(ticker: str, asset_type: str = "ACAO") -> list[dict]:
    is_fii = asset_type.upper() in FII_TYPES
    endpoint = "fii/dividends" if is_fii else "stocks/dividends"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/{endpoint}",
                headers=_auth_headers(),
                params={"symbols": ticker.upper()},
            )
            if resp.status_code in (401, 403):
                logger.warning(
                    "[Backfill] BRAPI sem autorizacao para %s (%s)",
                    sanitize_log_value(ticker),
                    endpoint,
                )
                return []
            if resp.status_code in (400, 404):
                logger.info(
                    "[Backfill] BRAPI sem dividendos/eventos para %s em %s (%s)",
                    sanitize_log_value(ticker),
                    endpoint,
                    resp.status_code,
                )
                return []
            resp.raise_for_status()
            data = resp.json()

        rows: list[dict] = []
        for entry in _iter_brapi_result_entries(data, ticker):
            rows.extend(
                _extract_brapi_events(entry, default_category="fii" if is_fii else None)
            )
        logger.info(
            "[Backfill] BRAPI %s: %s evento(s) bruto(s) para %s",
            endpoint,
            len(rows),
            sanitize_log_value(ticker),
        )
        return rows
    except Exception as e:
        logger.warning(
            "[Backfill] BRAPI erro para %s: %s",
            sanitize_log_value(ticker),
            sanitize_log_value(e),
        )
        return []


async def _fetch_dividends_yf(ticker: str) -> list[dict]:
    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        def _sync():
            import yfinance as yf

            t = yf.Ticker(ticker)
            divs = t.dividends
            if divs.empty:
                return []
            return [
                {
                    "paymentDate": str(dt.date()),
                    "rate": float(val),
                    "type": "DIVIDENDO",
                    "eventCategory": "cash",
                }
                for dt, val in divs.items()
            ]

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            return await loop.run_in_executor(pool, _sync)
    except Exception as e:
        logger.warning(
            "[Backfill] yfinance erro para %s: %s",
            sanitize_log_value(ticker),
            sanitize_log_value(e),
        )
        return []


async def backfill_dividends(
    db: AsyncSession,
    ticker: str,
    asset_type: str,
) -> None:
    """Collect and persist global asset dividend events."""
    if asset_type.upper() in SKIP_TYPES:
        logger.debug(
            "[Backfill] %s (%s) ignorado (SKIP_TYPES)",
            sanitize_log_value(ticker),
            sanitize_log_value(asset_type),
        )
        return

    logger.info(
        "[Backfill] iniciando sync global de eventos para %s",
        sanitize_log_value(ticker),
    )
    ticker = ticker.upper()
    asset_type_norm = asset_type.upper()

    use_yf = asset_type_norm in INTL_TYPES
    raw_dividends = (
        await _fetch_dividends_yf(ticker)
        if use_yf
        else await _fetch_dividends_brapi(ticker, asset_type_norm)
    )
    if not raw_dividends:
        logger.info(
            "[Backfill] nenhum provento encontrado para %s",
            sanitize_log_value(ticker),
        )
        return

    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type_norm)
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        asset = Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type_norm,
            currency="USD" if asset_type_norm in INTL_TYPES else "BRL",
        )
        db.add(asset)
        await db.flush()

    ad_result = await db.execute(
        select(AssetDividend).where(AssetDividend.asset_id == asset.id)
    )
    existing_ads: dict[tuple[date, str, date], AssetDividend] = {
        (
            ad.ex_date,
            _dividend_type_from_value(ad.dividend_type).value,
            ad.payment_date or ad.ex_date,
        ): ad
        for ad in ad_result.scalars().all()
    }

    source = "yfinance" if use_yf else "brapi"

    for raw in raw_dividends:
        parsed = parse_dividend_event(raw)
        if parsed is None:
            continue

        try:
            dividend_type = _dividend_type_from_value(parsed.dividend_type)
            asset_key = (
                parsed.ex_date,
                dividend_type.value,
                parsed.payment_date or parsed.ex_date,
            )
            asset_div = existing_ads.get(asset_key)
            if asset_div is None:
                asset_div = AssetDividend(
                    asset_id=asset.id,
                    record_date=parsed.record_date,
                    ex_date=parsed.ex_date,
                    payment_date=parsed.payment_date,
                    approved_on=parsed.approved_on,
                    value_per_unit=Decimal(str(parsed.value_per_unit)),
                    gross_value_per_unit=Decimal(str(parsed.gross_value_per_unit))
                    if parsed.gross_value_per_unit is not None
                    else None,
                    factor=Decimal(str(parsed.factor))
                    if parsed.factor is not None
                    else None,
                    complete_factor=Decimal(str(parsed.complete_factor))
                    if parsed.complete_factor is not None
                    else None,
                    isin_code=parsed.isin_code,
                    asset_issued=parsed.asset_issued,
                    related_to=parsed.related_to,
                    remarks=parsed.remarks,
                    raw_payload=parsed.raw_payload,
                    dividend_type=dividend_type,
                    source=source,
                )
                db.add(asset_div)
                await db.flush()
                existing_ads[asset_key] = asset_div
            else:
                asset_div.record_date = parsed.record_date or asset_div.record_date
                asset_div.payment_date = parsed.payment_date
                asset_div.approved_on = parsed.approved_on or asset_div.approved_on
                asset_div.value_per_unit = Decimal(str(parsed.value_per_unit))
                asset_div.gross_value_per_unit = (
                    Decimal(str(parsed.gross_value_per_unit))
                    if parsed.gross_value_per_unit is not None
                    else asset_div.gross_value_per_unit
                )
                asset_div.factor = (
                    Decimal(str(parsed.factor))
                    if parsed.factor is not None
                    else asset_div.factor
                )
                asset_div.complete_factor = (
                    Decimal(str(parsed.complete_factor))
                    if parsed.complete_factor is not None
                    else asset_div.complete_factor
                )
                asset_div.isin_code = parsed.isin_code or asset_div.isin_code
                asset_div.asset_issued = parsed.asset_issued or asset_div.asset_issued
                asset_div.related_to = parsed.related_to or asset_div.related_to
                asset_div.remarks = parsed.remarks or asset_div.remarks
                asset_div.raw_payload = parsed.raw_payload or asset_div.raw_payload
                asset_div.source = source

        except Exception as e:
            logger.warning(
                "[Backfill] erro ao processar provento de %s ex=%s: %s",
                sanitize_log_value(ticker),
                parsed.ex_date,
                sanitize_log_value(e),
            )
            await db.rollback()
            raise

    await db.commit()
    logger.info(
        "[Backfill] concluido sync global de eventos para %s",
        sanitize_log_value(ticker),
    )
