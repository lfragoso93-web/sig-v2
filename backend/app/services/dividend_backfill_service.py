import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi import BRAPI_BASE, _auth_headers
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.services.dividend_type_service import normalize_dividend_type

logger = logging.getLogger(__name__)

SKIP_TYPES = {"CRIPTO", "TESOURO_DIRETO", "RENDA_FIXA"}
INTL_TYPES = {"STOCK", "ETF_INTERNACIONAL"}
FII_TYPES = {"FII"}


@dataclass
class ParsedDividendEvent:
    record_date: date | None
    ex_date: date
    payment_date: date | None
    approved_on: date | None
    value_per_unit: float
    dividend_type: str
    gross_value_per_unit: float | None = None
    factor: float | None = None
    complete_factor: float | None = None
    isin_code: str | None = None
    asset_issued: str | None = None
    related_to: str | None = None
    remarks: str | None = None
    raw_payload: dict[str, Any] | None = None

    def __iter__(self):
        yield self.record_date
        yield self.ex_date
        yield self.payment_date
        yield self.value_per_unit
        yield self.dividend_type


def _map_dividend_type(raw: str | None, category: str | None = None) -> str:
    """Compatibilidade interna para o parser que ainda trabalha com strings."""
    return normalize_dividend_type(raw, category).value


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _next_business_day(d: date) -> date:
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


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
                    "[Backfill] BRAPI sem autorizacao para %s (%s)", ticker, endpoint
                )
                return []
            if resp.status_code in (400, 404):
                logger.info(
                    "[Backfill] BRAPI sem dividendos/eventos para %s em %s (%s)",
                    ticker,
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
            ticker,
        )
        return rows
    except Exception as e:
        logger.warning(f"[Backfill] BRAPI erro para {ticker}: {e}")
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
        logger.warning(f"[Backfill] yfinance erro para {ticker}: {e}")
        return []


def _parse_raw_dividend(raw: dict) -> ParsedDividendEvent | None:
    try:
        category = raw.get("eventCategory")
        record_date = _parse_date(
            raw.get("lastDatePrior")
            or raw.get("recordDate")
            or raw.get("dateCom")
            or raw.get("date_with")
        )
        explicit_ex_date = _parse_date(
            raw.get("exDate")
            or raw.get("ex_date")
            or raw.get("dateEx")
            or raw.get("date_ex")
        )
        pay_date = _parse_date(
            raw.get("paymentDate") or raw.get("paidAt") or raw.get("payment_date")
        )
        approved_on = _parse_date(
            raw.get("approvedOn") or raw.get("approved_on") or raw.get("declaredDate")
        )

        if explicit_ex_date:
            ex_date = explicit_ex_date
        elif record_date:
            ex_date = _next_business_day(record_date)
        elif pay_date:
            ex_date = pay_date
        elif approved_on:
            ex_date = approved_on
        else:
            return None

        div_type = _map_dividend_type(
            raw.get("label") or raw.get("type") or raw.get("dividendType"), category
        )
        value = _to_float(
            raw.get("rate")
            or raw.get("value")
            or raw.get("amount")
            or raw.get("income"),
            default=0.0,
        )
        factor = _to_optional_float(raw.get("factor"))
        complete_factor = _to_optional_float(
            raw.get("completeFactor") or raw.get("complete_factor")
        )

        cash_types = {
            DividendType.DIVIDENDO.value,
            DividendType.JCP.value,
            DividendType.RENDIMENTO.value,
            DividendType.AMORTIZACAO.value,
            DividendType.OUTROS.value,
        }
        if div_type in cash_types and value <= 0:
            return None

        return ParsedDividendEvent(
            record_date=record_date,
            ex_date=ex_date,
            payment_date=pay_date,
            approved_on=approved_on,
            value_per_unit=value,
            gross_value_per_unit=_to_optional_float(
                raw.get("grossRate") or raw.get("grossValue")
            ),
            factor=factor,
            complete_factor=complete_factor,
            dividend_type=div_type,
            isin_code=raw.get("isinCode") or raw.get("isin_code"),
            asset_issued=raw.get("assetIssued") or raw.get("asset_issued"),
            related_to=raw.get("relatedTo") or raw.get("related_to"),
            remarks=raw.get("remarks") or raw.get("observation"),
            raw_payload=raw,
        )
    except Exception:
        return None


async def backfill_dividends(
    db: AsyncSession,
    ticker: str,
    asset_type: str,
) -> None:
    """Collect and persist global asset dividend events."""
    if asset_type.upper() in SKIP_TYPES:
        logger.debug(f"[Backfill] {ticker} ({asset_type}) ignorado (SKIP_TYPES)")
        return

    logger.info("[Backfill] iniciando sync global de eventos para %s", ticker)
    ticker = ticker.upper()
    asset_type_norm = asset_type.upper()

    use_yf = asset_type_norm in INTL_TYPES
    raw_dividends = (
        await _fetch_dividends_yf(ticker)
        if use_yf
        else await _fetch_dividends_brapi(ticker, asset_type_norm)
    )
    if not raw_dividends:
        logger.info(f"[Backfill] nenhum provento encontrado para {ticker}")
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
        parsed = _parse_raw_dividend(raw)
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
                f"[Backfill] erro ao processar provento de {ticker} ex={parsed.ex_date}: {e}"
            )
            await db.rollback()
            raise

    await db.commit()
    logger.info("[Backfill] concluido sync global de eventos para %s", ticker)


async def run_backfill(db: AsyncSession, ticker: str, asset_type) -> None:
    """Sincroniza eventos globais do ativo."""
    asset_type_str = (
        asset_type.value if hasattr(asset_type, "value") else str(asset_type)
    )
    await backfill_dividends(db, ticker=ticker, asset_type=asset_type_str)
