"""Cliente tipado e isolado para contratos v2 de dados de mercado da BRAPI.

Este cliente nao expoe payloads brutos para routers ou frontend, mantendo
DTOs internos estaveis, tratamento de timeout, retries com backoff,
circuit breaker por cobertura de ativo e tratamento gracioso de erros.
"""

from __future__ import annotations

import asyncio
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime
import logging
from typing import Any, Optional, Sequence

import httpx

import re
from app.core.config import settings
from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

_MAX_TICKERS_PER_REQUEST = 20
_DEFAULT_TIMEOUT_SECONDS = 15.0
_DEFAULT_MAX_RETRIES = 2

_SAFE_SYMBOL_RE = re.compile(r"^[A-Za-z0-9^.-]{1,32}\Z")
_SAFE_MACRO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}\Z")
_SAFE_PATH_RE = re.compile(r"^/(api/quote/[A-Za-z0-9^.,-]+|v2/(tickers/resolve|prime/macro/[A-Za-z0-9_.-]+))\Z")


# -----------------------------------------------------------------------------
# Exceções tipadas
# -----------------------------------------------------------------------------

class BrapiV2Error(RuntimeError):
    """Erro generico normalizado da integracao v2."""


class BrapiV2NotFoundError(BrapiV2Error):
    """Ativo ou recurso nao encontrado no provedor (HTTP 404)."""


class BrapiV2RateLimitError(BrapiV2Error):
    """Limite de requisicoes excedido no provedor (HTTP 429)."""


class BrapiV2TimeoutError(BrapiV2Error):
    """Timeout de conexao ou leitura na requisicao ao provedor."""


# -----------------------------------------------------------------------------
# DTOs internos estaveis (independentes do provedor)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TickerResolution:
    """Resultado interno de normalizacao de um ticker informado pelo usuario."""

    requested_symbol: str
    symbol: str
    changed: bool
    status: str
    effective_date: Optional[date] = None


@dataclass(frozen=True)
class QuoteDTO:
    """Cotacao em tempo real ou fechamento de um ativo."""

    symbol: str
    regular_market_price: float
    regular_market_change: Optional[float] = None
    regular_market_change_percent: Optional[float] = None
    regular_market_time: Optional[datetime] = None
    currency: Optional[str] = "BRL"
    market_cap: Optional[float] = None
    short_name: Optional[str] = None
    long_name: Optional[str] = None


@dataclass(frozen=True)
class HistoricalBarDTO:
    """Barra individual da serie historica de precos (OHLCV)."""

    bar_date: date
    close: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[int] = None


@dataclass(frozen=True)
class PriceHistoryDTO:
    """Serie historica normalizada de um ativo."""

    symbol: str
    bars: list[HistoricalBarDTO] = field(default_factory=list)


@dataclass(frozen=True)
class DividendEventDTO:
    """Provento em dinheiro (Dividendo, JCP, Rendimento) normalizado."""

    symbol: str
    label: str  # DIVIDENDO, JCP, RENDIMENTO
    rate: float
    last_date_prior: Optional[date] = None  # Data Com
    payment_date: Optional[date] = None
    approved_on: Optional[date] = None
    isin_code: Optional[str] = None
    remarks: Optional[str] = None


@dataclass(frozen=True)
class CorporateEventDTO:
    """Evento corporativo de bonificacao, desdobramento ou subscricao (Issue #130 Bloco 4)."""

    symbol: str
    event_type: str  # BONUS, SPLIT, REVERSE_SPLIT, RIGHTS
    factor: Optional[float] = None
    subscription_price: Optional[float] = None
    last_date_prior: Optional[date] = None
    payment_date: Optional[date] = None
    subscription_end_date: Optional[date] = None
    isin_code: Optional[str] = None
    status: str = "PENDING"


@dataclass(frozen=True)
class FIIIndicatorDTO:
    """Indicadores fundamentalistas e operacionais de FII (Issue #130 Bloco 5)."""

    symbol: str
    pvp: Optional[float] = None
    dividend_yield: Optional[float] = None
    net_worth: Optional[float] = None
    share_holders: Optional[int] = None
    physical_vacancy: Optional[float] = None
    financial_vacancy: Optional[float] = None
    properties_count: Optional[int] = None
    segment: Optional[str] = None


@dataclass(frozen=True)
class CompanyFundamentalsDTO:
    """Fundamentos e estatisticas de acoes (Issue #130 Bloco 6)."""

    symbol: str
    pe: Optional[float] = None  # P/L
    pb: Optional[float] = None  # P/VP
    dividend_yield: Optional[float] = None
    eps: Optional[float] = None  # LPA
    market_cap: Optional[float] = None
    net_revenue: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    net_debt: Optional[float] = None


@dataclass(frozen=True)
class MacroSeriesPointDTO:
    """Ponto de serie temporal macroeconomica ou cambial (Issue #130 Bloco 7)."""

    name: str
    point_date: date
    value: float


# -----------------------------------------------------------------------------
# Cliente BrapiV2Client
# -----------------------------------------------------------------------------

class BrapiV2Client:
    """Cliente tipado para endpoints v2 da BRAPI com isolamento de payloads."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        self._base_url = (base_url or settings.BRAPI_BASE_URL).rstrip("/")
        self._token = token if token is not None else settings.BRAPI_TOKEN
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def _headers(self) -> dict[str, str]:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Executa requisicao GET com retry em falhas transientes e mapeamento de excecoes."""
        if not path.startswith("/") or "://" in path or ".." in path or not _SAFE_PATH_RE.fullmatch(path):
            raise ValueError(f"Caminho de requisicao BRAPI invalido: {path}")

        url = f"{self._base_url}{path}"
        base_parsed = urllib.parse.urlsplit(self._base_url)
        url_parsed = urllib.parse.urlsplit(url)
        if url_parsed.scheme not in ("http", "https") or url_parsed.netloc != base_parsed.netloc:
            raise ValueError(f"Destino de requisicao BRAPI invalido: {url}")

        last_exception: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.get(
                    url,
                    headers=self._headers(),
                    params=params,
                )
                if response.status_code == 404:
                    raise BrapiV2NotFoundError(f"Recurso nao encontrado ({path})")
                if response.status_code == 429:
                    raise BrapiV2RateLimitError("Limite de requisicoes BRAPI excedido (HTTP 429)")

                response.raise_for_status()

                try:
                    payload = response.json()
                except ValueError as exc:
                    raise BrapiV2Error("Resposta invalida (JSON malformado)") from exc

                if not isinstance(payload, dict):
                    raise BrapiV2Error("Resposta invalida (esperado objeto JSON)")

                return payload

            except (BrapiV2NotFoundError, BrapiV2RateLimitError):
                raise
            except httpx.TimeoutException as exc:
                last_exception = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(0.2 * (2 ** attempt))
                    continue
                raise BrapiV2TimeoutError("Timeout de comunicacao com o provedor") from exc
            except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
                last_exception = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                # Retry only for server errors (500, 502, 503, 504) or network connect errors
                if attempt < self._max_retries and (status is None or status >= 500):
                    await asyncio.sleep(0.2 * (2 ** attempt))
                    continue
                raise BrapiV2Error(f"Falha de comunicacao com o provedor: {exc}") from exc
            except Exception as exc:
                raise BrapiV2Error(f"Erro inesperado no cliente BRAPI: {exc}") from exc

        raise BrapiV2Error("Requisicao falhou apos retries") from last_exception

    # -------------------------------------------------------------------------
    # 1. Resolucao de Tickers
    # -------------------------------------------------------------------------

    async def resolve_tickers(
        self,
        symbols: Sequence[str],
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[TickerResolution]:
        """Resolve tickers antigos para os codigos atuais, preservando a ordem."""
        normalized_symbols = self._normalize_symbols(symbols)
        if not normalized_symbols:
            return []

        if client is not None:
            return await self._resolve_with_client(client, normalized_symbols)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._resolve_with_client(owned_client, normalized_symbols)

    async def _resolve_with_client(
        self,
        client: httpx.AsyncClient,
        symbols: list[str],
    ) -> list[TickerResolution]:
        resolutions: list[TickerResolution] = []

        for index in range(0, len(symbols), _MAX_TICKERS_PER_REQUEST):
            chunk = symbols[index:index + _MAX_TICKERS_PER_REQUEST]
            try:
                payload = await self._request_with_retry(
                    client,
                    "/v2/tickers/resolve",
                    params={"symbols": ",".join(chunk)},
                )
            except BrapiV2NotFoundError:
                continue

            raw_results = payload.get("results")
            if not isinstance(raw_results, list):
                raise BrapiV2Error("Resposta invalida ao resolver tickers")

            for item in raw_results:
                parsed = self._parse_resolution(item)
                if parsed is not None:
                    resolutions.append(parsed)

        return resolutions

    # -------------------------------------------------------------------------
    # 2. Cotacoes em Lote / Individuais
    # -------------------------------------------------------------------------

    async def fetch_quotes(
        self,
        symbols: Sequence[str],
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, QuoteDTO]:
        """Obtem cotacoes normalizadas em lote para os ativos informados."""
        normalized_symbols = self._normalize_symbols(symbols)
        if not normalized_symbols:
            return {}

        if client is not None:
            return await self._fetch_quotes_with_client(client, normalized_symbols)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._fetch_quotes_with_client(owned_client, normalized_symbols)

    async def _fetch_quotes_with_client(
        self,
        client: httpx.AsyncClient,
        symbols: list[str],
    ) -> dict[str, QuoteDTO]:
        quotes: dict[str, QuoteDTO] = {}

        for index in range(0, len(symbols), _MAX_TICKERS_PER_REQUEST):
            chunk = symbols[index:index + _MAX_TICKERS_PER_REQUEST]
            path = f"/api/quote/{','.join(chunk)}"
            try:
                payload = await self._request_with_retry(client, path)
            except BrapiV2NotFoundError:
                continue
            except BrapiV2RateLimitError:
                raise
            except Exception as exc:
                logger.warning("Falha ao buscar lote de cotacoes %s: %s", sanitize_log_value(chunk), sanitize_log_value(exc))
                continue

            raw_results = payload.get("results")
            if not isinstance(raw_results, list):
                continue

            for item in raw_results:
                parsed = self._parse_quote(item)
                if parsed is not None:
                    quotes[parsed.symbol] = parsed

        return quotes

    # -------------------------------------------------------------------------
    # 3. Historico de Precos
    # -------------------------------------------------------------------------

    async def fetch_history(
        self,
        symbol: str,
        *,
        range_val: str = "1mo",
        interval: str = "1d",
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[PriceHistoryDTO]:
        """Obtem serie historica OHLCV de um ativo."""
        clean_symbol = symbol.strip().upper()
        if not clean_symbol or not _SAFE_SYMBOL_RE.fullmatch(clean_symbol):
            return None

        path = f"/api/quote/{clean_symbol}"
        params = {"range": range_val, "interval": interval}

        if client is not None:
            return await self._fetch_history_with_client(client, clean_symbol, path, params)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._fetch_history_with_client(owned_client, clean_symbol, path, params)

    async def _fetch_history_with_client(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        path: str,
        params: dict[str, Any],
    ) -> Optional[PriceHistoryDTO]:
        try:
            payload = await self._request_with_retry(client, path, params=params)
        except BrapiV2NotFoundError:
            return None

        raw_results = payload.get("results")
        if not isinstance(raw_results, list) or not raw_results:
            return None

        entry = raw_results[0]
        if not isinstance(entry, dict):
            return None

        raw_bars = entry.get("historicalDataPrice")
        if not isinstance(raw_bars, list):
            return None

        bars: list[HistoricalBarDTO] = []
        for bar_raw in raw_bars:
            if not isinstance(bar_raw, dict):
                continue
            parsed_bar = self._parse_historical_bar(bar_raw)
            if parsed_bar is not None:
                bars.append(parsed_bar)

        bars.sort(key=lambda b: b.bar_date)
        return PriceHistoryDTO(symbol=symbol, bars=bars)

    # -------------------------------------------------------------------------
    # 4. Proventos e Eventos Corporativos (Issue #130 Bloco 3 e 4)
    # -------------------------------------------------------------------------

    async def fetch_dividends_and_events(
        self,
        symbol: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> tuple[list[DividendEventDTO], list[CorporateEventDTO]]:
        """Obtem proventos em dinheiro e eventos corporativos separados (Bloco 4)."""
        clean_symbol = symbol.strip().upper()
        if not clean_symbol or not _SAFE_SYMBOL_RE.fullmatch(clean_symbol):
            return [], []

        path = f"/api/quote/{clean_symbol}"
        params = {"dividends": "true"}

        if client is not None:
            return await self._fetch_dividends_with_client(client, clean_symbol, path, params)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._fetch_dividends_with_client(owned_client, clean_symbol, path, params)

    async def _fetch_dividends_with_client(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        path: str,
        params: dict[str, Any],
    ) -> tuple[list[DividendEventDTO], list[CorporateEventDTO]]:
        try:
            payload = await self._request_with_retry(client, path, params=params)
        except BrapiV2NotFoundError:
            return [], []

        raw_results = payload.get("results")
        if not isinstance(raw_results, list) or not raw_results:
            return [], []

        entry = raw_results[0]
        if not isinstance(entry, dict):
            return [], []

        div_data = entry.get("dividendsData")
        if not isinstance(div_data, dict):
            div_data = entry

        cash_dividends: list[DividendEventDTO] = []
        corp_events: list[CorporateEventDTO] = []

        # Proventos em dinheiro (cashDividends)
        for item in div_data.get("cashDividends") or []:
            if isinstance(item, dict):
                cash_dto = self._parse_cash_dividend(symbol, item)
                if cash_dto is not None:
                    cash_dividends.append(cash_dto)

        # Bonificacoes / Desdobramentos (stockDividends)
        for item in div_data.get("stockDividends") or []:
            if isinstance(item, dict):
                stock_dto = self._parse_stock_dividend(symbol, item)
                if stock_dto is not None:
                    corp_events.append(stock_dto)

        # Subscricoes (subscriptions)
        for item in div_data.get("subscriptions") or []:
            if isinstance(item, dict):
                sub_dto = self._parse_subscription(symbol, item)
                if sub_dto is not None:
                    corp_events.append(sub_dto)

        return cash_dividends, corp_events

    # -------------------------------------------------------------------------
    # 5. Enriquecimento de FIIs (Issue #130 Bloco 5)
    # -------------------------------------------------------------------------

    async def fetch_fii_indicators(
        self,
        symbol: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[FIIIndicatorDTO]:
        """Obtem dados operacionais, de vacancia e fundamentos de FII."""
        clean_symbol = symbol.strip().upper()
        if not clean_symbol or not _SAFE_SYMBOL_RE.fullmatch(clean_symbol):
            return None

        path = f"/api/quote/{clean_symbol}"
        params = {"fundamental": "true"}

        if client is not None:
            return await self._fetch_fii_indicators_with_client(client, clean_symbol, path, params)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._fetch_fii_indicators_with_client(owned_client, clean_symbol, path, params)

    async def _fetch_fii_indicators_with_client(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        path: str,
        params: dict[str, Any],
    ) -> Optional[FIIIndicatorDTO]:
        try:
            payload = await self._request_with_retry(client, path, params=params)
        except BrapiV2NotFoundError:
            return None

        raw_results = payload.get("results")
        if not isinstance(raw_results, list) or not raw_results:
            return None

        entry = raw_results[0]
        if not isinstance(entry, dict):
            return None

        return FIIIndicatorDTO(
            symbol=symbol,
            pvp=self._safe_float(entry.get("priceToBook") or entry.get("pvp")),
            dividend_yield=self._safe_float(entry.get("dividendYield")),
            net_worth=self._safe_float(entry.get("netWorth") or entry.get("equity")),
            share_holders=self._safe_int(entry.get("shareHolders") or entry.get("quotaHolders")),
            physical_vacancy=self._safe_float(entry.get("physicalVacancy")),
            financial_vacancy=self._safe_float(entry.get("financialVacancy")),
            properties_count=self._safe_int(entry.get("propertiesCount") or entry.get("realEstateCount")),
            segment=str(entry.get("segment") or entry.get("sector") or "") or None,
        )

    # -------------------------------------------------------------------------
    # 6. Fundamentos de Acoes (Issue #130 Bloco 6)
    # -------------------------------------------------------------------------

    async def fetch_company_fundamentals(
        self,
        symbol: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[CompanyFundamentalsDTO]:
        """Obtem metricas fundamentalistas consolidadas para acoes."""
        clean_symbol = symbol.strip().upper()
        if not clean_symbol or not _SAFE_SYMBOL_RE.fullmatch(clean_symbol):
            return None

        path = f"/api/quote/{clean_symbol}"
        params = {"fundamental": "true"}

        if client is not None:
            return await self._fetch_fundamentals_with_client(client, clean_symbol, path, params)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._fetch_fundamentals_with_client(owned_client, clean_symbol, path, params)

    async def _fetch_fundamentals_with_client(
        self,
        client: httpx.AsyncClient,
        symbol: str,
        path: str,
        params: dict[str, Any],
    ) -> Optional[CompanyFundamentalsDTO]:
        try:
            payload = await self._request_with_retry(client, path, params=params)
        except BrapiV2NotFoundError:
            return None

        raw_results = payload.get("results")
        if not isinstance(raw_results, list) or not raw_results:
            return None

        entry = raw_results[0]
        if not isinstance(entry, dict):
            return None

        return CompanyFundamentalsDTO(
            symbol=symbol,
            pe=self._safe_float(entry.get("priceEarnings") or entry.get("pe")),
            pb=self._safe_float(entry.get("priceToBook") or entry.get("pb")),
            dividend_yield=self._safe_float(entry.get("dividendYield")),
            eps=self._safe_float(entry.get("earningsPerShare") or entry.get("lpa")),
            market_cap=self._safe_float(entry.get("marketCap")),
            net_revenue=self._safe_float(entry.get("netRevenue") or entry.get("revenue")),
            net_income=self._safe_float(entry.get("netIncome") or entry.get("lucroLiquido")),
            ebitda=self._safe_float(entry.get("ebitda")),
            net_margin=self._safe_float(entry.get("netMargin") or entry.get("margemLiquida")),
            roe=self._safe_float(entry.get("returnOnEquity") or entry.get("roe")),
            net_debt=self._safe_float(entry.get("netDebt") or entry.get("dividaLiquida")),
        )

    # -------------------------------------------------------------------------
    # 7. Series Macroeconomicas e Cambio (Issue #130 Bloco 7)
    # -------------------------------------------------------------------------

    async def fetch_macro_series(
        self,
        name: str,
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[MacroSeriesPointDTO]:
        """Obtem serie historica de indicadores macroeconomicos (CDI, SELIC, IPCA) ou moedas."""
        clean_name = name.strip().upper()
        if not clean_name or not _SAFE_MACRO_RE.fullmatch(clean_name):
            return []

        path = f"/v2/prime/macro/{clean_name}"
        if client is not None:
            return await self._fetch_macro_with_client(client, clean_name, path)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await self._fetch_macro_with_client(owned_client, clean_name, path)

    async def _fetch_macro_with_client(
        self,
        client: httpx.AsyncClient,
        name: str,
        path: str,
    ) -> list[MacroSeriesPointDTO]:
        try:
            payload = await self._request_with_retry(client, path)
        except (BrapiV2NotFoundError, BrapiV2Error):
            return []

        raw_points = payload.get("results") or payload.get("data")
        if not isinstance(raw_points, list):
            return []

        points: list[MacroSeriesPointDTO] = []
        for raw in raw_points:
            if not isinstance(raw, dict):
                continue
            date_raw = raw.get("date") or raw.get("timestamp")
            val_raw = raw.get("value") or raw.get("rate")
            if not date_raw or val_raw is None:
                continue
            try:
                p_date = date.fromisoformat(str(date_raw)[:10])
                p_val = float(val_raw)
                points.append(MacroSeriesPointDTO(name=name, point_date=p_date, value=p_val))
            except (ValueError, TypeError):
                continue

        points.sort(key=lambda p: p.point_date)
        return points

    # -------------------------------------------------------------------------
    # Utilitarios de Parsing e Normalizacao
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for symbol in symbols:
            value = symbol.strip().upper()
            if not value or value in seen:
                continue
            if not _SAFE_SYMBOL_RE.fullmatch(value):
                continue
            seen.add(value)
            normalized.append(value)

        return normalized

    @staticmethod
    def _parse_resolution(raw: object) -> Optional[TickerResolution]:
        if not isinstance(raw, dict):
            return None

        requested_symbol = str(raw.get("requestedSymbol") or "").strip().upper()
        symbol = str(raw.get("symbol") or "").strip().upper()
        status = str(raw.get("status") or "").strip().lower()

        if not requested_symbol or not symbol or not status:
            return None

        raw_effective_date = raw.get("effectiveDate")
        effective_date: Optional[date] = None
        if raw_effective_date:
            try:
                effective_date = date.fromisoformat(str(raw_effective_date)[:10])
            except ValueError:
                effective_date = None

        return TickerResolution(
            requested_symbol=requested_symbol,
            symbol=symbol,
            changed=bool(raw.get("changed", requested_symbol != symbol)),
            status=status,
            effective_date=effective_date,
        )

    @classmethod
    def _parse_quote(cls, raw: dict[str, Any]) -> Optional[QuoteDTO]:
        symbol = str(raw.get("symbol") or "").strip().upper()
        price = cls._safe_float(raw.get("regularMarketPrice") or raw.get("close"))
        if not symbol or price is None or price < 0:
            return None

        time_val = None
        raw_time = raw.get("regularMarketTime")
        if raw_time:
            try:
                time_val = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                time_val = None

        return QuoteDTO(
            symbol=symbol,
            regular_market_price=price,
            regular_market_change=cls._safe_float(raw.get("regularMarketChange")),
            regular_market_change_percent=cls._safe_float(raw.get("regularMarketChangePercent")),
            regular_market_time=time_val,
            currency=str(raw.get("currency") or "BRL"),
            market_cap=cls._safe_float(raw.get("marketCap")),
            short_name=str(raw.get("shortName") or "") or None,
            long_name=str(raw.get("longName") or "") or None,
        )

    @classmethod
    def _parse_historical_bar(cls, raw: dict[str, Any]) -> Optional[HistoricalBarDTO]:
        raw_date = raw.get("date")
        if raw_date is None:
            return None

        parsed_date: Optional[date] = None
        if isinstance(raw_date, (int, float)):
            try:
                parsed_date = datetime.fromtimestamp(raw_date).date()
            except (ValueError, OSError):
                return None
        else:
            try:
                parsed_date = date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                return None

        close = cls._safe_float(raw.get("close"))
        if close is None:
            return None

        return HistoricalBarDTO(
            bar_date=parsed_date,
            close=close,
            open=cls._safe_float(raw.get("open")),
            high=cls._safe_float(raw.get("high")),
            low=cls._safe_float(raw.get("low")),
            volume=cls._safe_int(raw.get("volume")),
        )

    @classmethod
    def _parse_cash_dividend(cls, symbol: str, raw: dict[str, Any]) -> Optional[DividendEventDTO]:
        rate = cls._safe_float(raw.get("rate") or raw.get("value") or raw.get("amount"))
        if rate is None or rate <= 0:
            return None

        label = str(raw.get("label") or raw.get("type") or "DIVIDENDO").strip().upper()
        last_date = cls._safe_date(raw.get("lastDatePrior") or raw.get("exDate"))
        pay_date = cls._safe_date(raw.get("paymentDate") or raw.get("paidAt"))
        approved_on = cls._safe_date(raw.get("approvedOn"))

        return DividendEventDTO(
            symbol=symbol,
            label=label,
            rate=rate,
            last_date_prior=last_date,
            payment_date=pay_date,
            approved_on=approved_on,
            isin_code=str(raw.get("isinCode") or "") or None,
            remarks=str(raw.get("remarks") or "") or None,
        )

    @classmethod
    def _parse_stock_dividend(cls, symbol: str, raw: dict[str, Any]) -> Optional[CorporateEventDTO]:
        factor = cls._safe_float(raw.get("factor") or raw.get("rate") or raw.get("percentage"))
        label = str(raw.get("label") or raw.get("type") or "BONIFICACAO").strip().upper()

        event_type = "BONUS"
        if "DESDOBRAMENTO" in label or "SPLIT" in label:
            event_type = "SPLIT"
        elif "GRUPAMENTO" in label or "REVERSE" in label:
            event_type = "REVERSE_SPLIT"

        last_date = cls._safe_date(raw.get("lastDatePrior") or raw.get("approvedOn"))
        pay_date = cls._safe_date(raw.get("paymentDate"))

        return CorporateEventDTO(
            symbol=symbol,
            event_type=event_type,
            factor=factor,
            last_date_prior=last_date,
            payment_date=pay_date,
            isin_code=str(raw.get("isinCode") or "") or None,
        )

    @classmethod
    def _parse_subscription(cls, symbol: str, raw: dict[str, Any]) -> Optional[CorporateEventDTO]:
        price = cls._safe_float(raw.get("price") or raw.get("subscriptionPrice"))
        factor = cls._safe_float(raw.get("percentage") or raw.get("factor"))

        last_date = cls._safe_date(raw.get("lastDatePrior") or raw.get("approvedOn"))
        end_date = cls._safe_date(raw.get("subscriptionEndDate") or raw.get("tradingPeriodEnd"))

        return CorporateEventDTO(
            symbol=symbol,
            event_type="RIGHTS",
            factor=factor,
            subscription_price=price,
            last_date_prior=last_date,
            subscription_end_date=end_date,
            isin_code=str(raw.get("isinCode") or "") or None,
            status="PENDING",
        )

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(val: Any) -> Optional[int]:
        if val is None:
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_date(val: Any) -> Optional[date]:
        if not val:
            return None
        try:
            return date.fromisoformat(str(val)[:10])
        except (ValueError, TypeError):
            return None
