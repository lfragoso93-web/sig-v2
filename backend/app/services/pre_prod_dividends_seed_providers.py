"""Adaptadores estritos de provedores para o seed isolado de proventos."""
from __future__ import annotations

import asyncio
import warnings
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from pandas.errors import Pandas4Warning
from yfinance.exceptions import YFTickerMissingError

from app.integrations.b3_listed_companies import (
    B3ListedCompaniesClient,
    B3ListedCompaniesError,
    parse_b3_date,
)
from app.integrations.brapi import BRAPI_BASE, _auth_headers
from app.services.dividend_brapi_payload import (
    FII_ASSET_TYPES,
    extract_brapi_events,
    iter_brapi_result_entries,
)
from app.services.dividend_history_seed_service import _yf_symbol
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendCollectionError,
    StrictDividendProviderResult,
)

YahooHistoryRow = tuple[date, float] | tuple[date, float, dict[str, Any]]
YahooHistoryFetcher = Callable[[str], Awaitable[list[YahooHistoryRow]]]


class StrictB3DividendProvider:
    """Coleta proventos estruturados do portal oficial da B3."""

    def __init__(self, *, client: B3ListedCompaniesClient) -> None:
        self._client = client

    async def __call__(
        self, ticker: str, asset_type: str
    ) -> StrictDividendProviderResult:
        try:
            supplement, rows, empty_reason = await self._client.cash_dividends(
                ticker=ticker, asset_type=asset_type
            )
        except B3ListedCompaniesError as exc:
            if "sem cÃƒÂ³digo de emissor resolvÃƒÂ­vel" in str(exc).lower():
                return StrictDividendProviderResult(
                    source="b3", rows=(), empty_reason="provider_no_coverage_issuer"
                )
            raise StrictDividendCollectionError(f"{ticker}/b3: {exc}") from exc
        if empty_reason:
            return StrictDividendProviderResult(
                source="b3", rows=(), empty_reason=empty_reason
            )
        normalized: list[dict[str, Any]] = []
        is_bdr = asset_type.strip().upper() == "BDR"
        suffix = ticker.strip()[-1:]
        expected_share_class = {
            "3": "ON", "4": "PN", "5": "PNA", "6": "PNB",
            "7": "PNC", "8": "PND",
        }.get(suffix) if asset_type.strip().upper() == "ACAO" else None
        supplement_cash = (supplement or {}).get("cashDividends", [])
        for row in rows:
            item = dict(row)
            if not is_bdr:
                row_class = str(item.get("typeStock") or "").strip().upper()
                if expected_share_class and row_class and row_class != expected_share_class:
                    continue
                item["label"] = item.get("corporateAction") or item.get("label")
                item["rate"] = item.get("valueCash") or item.get("rate")
                item["lastDatePrior"] = (
                    item.get("lastDatePriorEx") or item.get("lastDatePrior")
                )
                item["approvedOn"] = item.get("dateApproval") or item.get("approvedOn")
                # Supplement records include payment date and ISIN for a
                # shorter window. Join only on exact official identity fields.
                for detail in (supplement_cash if isinstance(supplement_cash, list) else ()):
                    if not isinstance(detail, dict):
                        continue
                    try:
                        rate_matches = Decimal(str(detail.get("rate"))) == Decimal(str(item.get("rate")))
                    except (InvalidOperation, TypeError, ValueError):
                        rate_matches = False
                    if (
                        str(detail.get("lastDatePrior") or "") == str(item.get("lastDatePrior") or "")
                        and rate_matches
                        and str(detail.get("label") or "").upper() == str(item.get("label") or "").upper()
                    ):
                        item["paymentDate"] = detail.get("paymentDate")
                        item["isinCode"] = detail.get("isinCode")
                        item["assetIssued"] = detail.get("assetIssued")
                        item["relatedTo"] = detail.get("relatedTo")
                        item["remarks"] = detail.get("remarks")
                        break
            for field in ("lastDatePrior", "paymentDate", "approvedOn", "exDate"):
                if item.get(field):
                    item[field] = parse_b3_date(item[field]).isoformat()
            item["eventCategory"] = "cash"
            normalized.append(item)
        if not normalized:
            return StrictDividendProviderResult(
                source="b3", rows=(), empty_reason="provider_returned_no_events"
            )
        return StrictDividendProviderResult(source="b3", rows=tuple(normalized))


def make_strict_b3_dividend_provider(client: httpx.AsyncClient):
    """Build the collector-compatible B3 provider from a shared HTTP client."""
    from app.integrations.b3_listed_companies import B3ListedCompaniesClient

    return StrictB3DividendProvider(client=B3ListedCompaniesClient(client=client))


def _decimal_scale(value: float) -> int:
    """Retorna a escala decimal efetivamente exposta pelo provedor."""

    exponent = Decimal(str(value)).as_tuple().exponent
    return max(0, -exponent)


class StrictBrapiDividendProvider:
    """Consulta uma fonte BRAPI sem ocultar falhas como ausÃªncia de eventos."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str = BRAPI_BASE,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._headers = dict(headers) if headers is not None else _auth_headers()

    async def __call__(
        self,
        ticker: str,
        asset_type: str,
    ) -> StrictDividendProviderResult:
        is_fii = asset_type.upper() in FII_ASSET_TYPES
        endpoint = "fii/dividends" if is_fii else "stocks/dividends"

        try:
            response = await self._client.get(
                f"{self._base_url}/v2/{endpoint}",
                headers=self._headers,
                params={"symbols": ticker.upper()},
            )
        except httpx.HTTPError as exc:
            raise StrictDividendCollectionError(
                f"{ticker}/brapi: falha de transporte"
            ) from exc

        if response.status_code in {401, 403}:
            raise StrictDividendCollectionError(
                f"{ticker}/brapi: autorizaÃ§Ã£o recusada ({response.status_code})"
            )
        if response.status_code in {400, 404}:
            return StrictDividendProviderResult(
                source="brapi",
                rows=(),
                empty_reason=f"provider_no_coverage_http_{response.status_code}",
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise StrictDividendCollectionError(
                f"{ticker}/brapi: HTTP {response.status_code}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise StrictDividendCollectionError(
                f"{ticker}/brapi: JSON invÃ¡lido"
            ) from exc
        if not isinstance(payload, dict):
            raise StrictDividendCollectionError(
                f"{ticker}/brapi: payload deve ser objeto"
            )

        rows: list[dict[str, Any]] = []
        for entry in iter_brapi_result_entries(payload, ticker):
            rows.extend(
                extract_brapi_events(
                    entry,
                    default_category="fii" if is_fii else None,
                )
            )

        if not rows:
            return StrictDividendProviderResult(
                source="brapi",
                rows=(),
                empty_reason="provider_returned_no_events",
            )
        return StrictDividendProviderResult(source="brapi", rows=tuple(rows))


class StrictYahooDividendProvider:
    """Complementa histÃ³rico sem cooldown nem fallback silencioso.

    O Ã­ndice de ``Dividends`` do Yahoo representa a data ex do evento, nÃ£o a
    data efetiva de pagamento. O adaptador normaliza essa semÃ¢ntica na fronteira
    e registra a escala numÃ©rica observada para reconciliaÃ§Ã£o auditÃ¡vel com a
    fonte primÃ¡ria. O histÃ³rico real mostra valores quantizados ora por
    truncamento, ora por arredondamento; por isso o adapter declara somente a
    escala observada, sem inventar um Ãºnico modo de reduÃ§Ã£o do provedor.
    """

    def __init__(self, *, history_fetcher: YahooHistoryFetcher) -> None:
        self._history_fetcher = history_fetcher

    async def __call__(
        self,
        ticker: str,
        asset_type: str,
    ) -> StrictDividendProviderResult:
        if asset_type.upper() == "BDR":
            return StrictDividendProviderResult(
                source="yfinance_history",
                rows=(),
                empty_reason="b3_authoritative_source_required",
            )

        symbol = _yf_symbol(ticker, asset_type)
        try:
            history = await self._history_fetcher(symbol)
        except YFTickerMissingError:
            return StrictDividendProviderResult(
                source="yfinance_history",
                rows=(),
                empty_reason="provider_no_coverage_ticker_missing",
            )
        except StrictDividendCollectionError:
            raise
        except Exception as exc:
            raise StrictDividendCollectionError(
                f"{ticker}/yfinance_history: provedor indisponÃ­vel"
            ) from exc

        rows = []
        for history_row in history:
            event_date, amount = history_row[:2]
            adjustment = history_row[2] if len(history_row) == 3 else None
            row = {
                "exDate": event_date.isoformat(),
                "rate": amount,
                "type": "DIVIDENDO",
                "eventCategory": "cash",
                "eventSemantics": "aggregate_cash_by_ex_date",
                "canonicalComparison": {
                    "value_per_unit": {
                        "mode": "provider_quantized",
                        "scale": _decimal_scale(amount),
                    }
                },
            }
            if adjustment is not None:
                row["corporateActionAdjustment"] = adjustment
            rows.append(row)
        normalized_rows = tuple(rows)
        if not normalized_rows:
            return StrictDividendProviderResult(
                source="yfinance_history",
                rows=(),
                empty_reason="provider_returned_no_historical_events",
            )
        return StrictDividendProviderResult(
            source="yfinance_history",
            rows=normalized_rows,
        )


async def fetch_yahoo_dividend_history(symbol: str) -> list[YahooHistoryRow]:
    """Consulta padrÃ£o do Yahoo; exceÃ§Ãµes sÃ£o preservadas para o adaptador."""

    def _sync() -> list[YahooHistoryRow]:
        import yfinance as yf

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*Timestamp\.utcnow is deprecated.*",
                category=Pandas4Warning,
            )
            actions = yf.Ticker(symbol).actions.copy(deep=True)
            history = yf.Ticker(symbol).history(
                start="1970-01-01",
                end=(datetime.now(UTC).date() + timedelta(days=1)).isoformat(),
                actions=True,
                auto_adjust=False,
                raise_errors=True,
            )
        if history.empty or "Dividends" not in history.columns:
            return []

        split_events: list[tuple[date, Decimal]] = []
        if not actions.empty and "Stock Splits" in actions.columns:
            for timestamp, value in actions["Stock Splits"].items():
                factor = Decimal(str(float(value or 0)))
                if factor <= 0:
                    continue
                split_date = (
                    timestamp.date()
                    if hasattr(timestamp, "date")
                    else date.fromisoformat(str(timestamp)[:10])
                )
                split_events.append((split_date, factor))

        rows: list[YahooHistoryRow] = []
        for timestamp, value in history["Dividends"].items():
            amount = float(value or 0)
            if amount <= 0:
                continue
            event_date = (
                timestamp.date()
                if hasattr(timestamp, "date")
                else date.fromisoformat(str(timestamp)[:10])
            )
            cumulative_factor = Decimal(1)
            for split_date, factor in split_events:
                if split_date > event_date:
                    cumulative_factor *= factor

            if cumulative_factor == 1:
                rows.append((event_date, amount))
                continue

            normalized_amount = Decimal(str(amount)) * cumulative_factor
            rows.append((
                event_date,
                float(normalized_amount),
                {
                    "mode": "undo_subsequent_splits",
                    "providerValue": str(amount),
                    "cumulativeFactor": str(cumulative_factor),
                },
            ))
        return rows

    return await asyncio.to_thread(_sync)
