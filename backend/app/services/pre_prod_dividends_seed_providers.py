"""Adaptadores estritos de provedores para o seed isolado de proventos."""
from __future__ import annotations

import asyncio
import warnings
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from pandas.errors import Pandas4Warning
from yfinance.exceptions import YFTickerMissingError

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


def _decimal_scale(value: float) -> int:
    """Retorna a escala decimal efetivamente exposta pelo provedor."""

    exponent = Decimal(str(value)).as_tuple().exponent
    return max(0, -exponent)


class StrictBrapiDividendProvider:
    """Consulta uma fonte BRAPI sem ocultar falhas como ausência de eventos."""

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
                f"{ticker}/brapi: autorização recusada ({response.status_code})"
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
                f"{ticker}/brapi: JSON inválido"
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
    """Complementa histórico sem cooldown nem fallback silencioso.

    O índice de ``Dividends`` do Yahoo representa a data ex do evento, não a
    data efetiva de pagamento. O adaptador normaliza essa semântica na fronteira
    e registra a escala numérica observada para reconciliação auditável com a
    fonte primária. O histórico real mostra valores quantizados ora por
    truncamento, ora por arredondamento; por isso o adapter declara somente a
    escala observada, sem inventar um único modo de redução do provedor.
    """

    def __init__(self, *, history_fetcher: YahooHistoryFetcher) -> None:
        self._history_fetcher = history_fetcher

    async def __call__(
        self,
        ticker: str,
        asset_type: str,
    ) -> StrictDividendProviderResult:
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
                f"{ticker}/yfinance_history: provedor indisponível"
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
    """Consulta padrão do Yahoo; exceções são preservadas para o adaptador."""

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