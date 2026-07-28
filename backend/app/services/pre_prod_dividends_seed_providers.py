"""Adaptadores estritos de provedores para o seed isolado de proventos."""
from __future__ import annotations

import asyncio
import warnings
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from pandas.errors import Pandas4Warning
from yfinance.exceptions import YFTickerMissingError

from app.integrations.brapi import BRAPI_BASE, _auth_headers
from app.services.dividend_backfill_service import (
    FII_TYPES,
    _extract_brapi_events,
    _iter_brapi_result_entries,
)
from app.services.dividend_history_seed_service import _yf_symbol
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendCollectionError,
    StrictDividendProviderResult,
)

YahooHistoryFetcher = Callable[[str], Awaitable[list[tuple[date, float]]]]


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
        is_fii = asset_type.upper() in FII_TYPES
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
        for entry in _iter_brapi_result_entries(payload, ticker):
            rows.extend(
                _extract_brapi_events(
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
    """Complementa histórico sem cooldown nem fallback silencioso."""

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

        rows = tuple(
            {
                "paymentDate": event_date.isoformat(),
                "rate": amount,
                "type": "DIVIDENDO",
                "eventCategory": "cash",
            }
            for event_date, amount in history
        )
        if not rows:
            return StrictDividendProviderResult(
                source="yfinance_history",
                rows=(),
                empty_reason="provider_returned_no_historical_events",
            )
        return StrictDividendProviderResult(
            source="yfinance_history",
            rows=rows,
        )


async def fetch_yahoo_dividend_history(symbol: str) -> list[tuple[date, float]]:
    """Consulta padrão do Yahoo; exceções são preservadas para o adaptador."""

    def _sync() -> list[tuple[date, float]]:
        import yfinance as yf

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r".*Timestamp\.utcnow is deprecated.*",
                category=Pandas4Warning,
            )
            history = yf.Ticker(symbol).history(
                start="1970-01-01",
                end=(datetime.now(UTC).date() + timedelta(days=1)).isoformat(),
                actions=True,
                auto_adjust=False,
                raise_errors=True,
            )
        if history.empty or "Dividends" not in history.columns:
            return []

        rows: list[tuple[date, float]] = []
        for timestamp, value in history["Dividends"].items():
            amount = float(value or 0)
            if amount <= 0:
                continue
            event_date = (
                timestamp.date()
                if hasattr(timestamp, "date")
                else date.fromisoformat(str(timestamp)[:10])
            )
            rows.append((event_date, amount))
        return rows

    return await asyncio.to_thread(_sync)
