"""Contratos internos para os endpoints BRAPI v2.

O modulo legado continua ativo durante a migracao incremental. Este cliente
converte respostas do provedor em tipos estaveis e nunca entrega payload bruto
para routers ou para o frontend.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import httpx

from app.core.config import settings

_MAX_TICKERS_PER_REQUEST = 20
_MAX_CATALOG_PAGE_SIZE = 2000
_DEFAULT_TIMEOUT_SECONDS = 15.0


class BrapiV2Error(RuntimeError):
    """Erro normalizado da integracao v2."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class BrapiV2AuthenticationError(BrapiV2Error):
    """Token ausente, invalido ou expirado."""


class BrapiV2PermissionError(BrapiV2Error):
    """O plano contratado nao permite acessar o recurso."""


class BrapiV2NotFoundError(BrapiV2Error):
    """Recurso nao encontrado no provedor."""


class BrapiV2RateLimitError(BrapiV2Error):
    """Limite de requisicoes do provedor atingido."""


class BrapiV2TransportError(BrapiV2Error):
    """Falha de rede, DNS ou timeout ao acessar o provedor."""


class BrapiV2ContractError(BrapiV2Error):
    """Resposta nao atende ao contrato documentado do endpoint."""


@dataclass(frozen=True)
class TickerResolution:
    requested_symbol: str
    symbol: str
    changed: bool
    status: str
    effective_date: date | None = None


@dataclass(frozen=True)
class TickerCoverage:
    requested_symbol: str
    symbol: str
    changed: bool
    status: str
    asset_type: str | None
    sub_type: str | None
    available_data: Mapping[str, bool] = field(default_factory=dict)
    recommended_endpoints: Mapping[str, str] = field(default_factory=dict)

    def supports(self, capability: str) -> bool:
        """Informa se uma capacidade foi declarada pelo provedor."""
        return self.available_data.get(capability) is True


@dataclass(frozen=True)
class TickerRename:
    old_symbol: str
    new_symbol: str
    canonical_symbol: str
    effective_date: date


@dataclass(frozen=True)
class TickerCatalogItem:
    symbol: str
    name: str
    long_name: str | None
    asset_type: str
    sub_type: str | None
    exchange: str | None
    currency: str | None
    sector: str | None
    subsector: str | None
    is_active: bool
    logo_url: str | None


@dataclass(frozen=True)
class TickerCatalogPage:
    results: tuple[TickerCatalogItem, ...]
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next_page: bool


class BrapiV2Client:
    """Cliente v2 com autenticacao, erros e DTOs consistentes."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = (base_url or settings.BRAPI_BASE_URL).rstrip("/")
        self._token = token if token is not None else settings.BRAPI_TOKEN
        self._timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    async def resolve_tickers(
        self,
        symbols: Sequence[str],
        *,
        client: httpx.AsyncClient | None = None,
    ) -> list[TickerResolution]:
        normalized = self._normalize_symbols(symbols)
        if not normalized:
            return []

        async def run(active_client: httpx.AsyncClient) -> list[TickerResolution]:
            resolutions: list[TickerResolution] = []
            for chunk in self._chunks(normalized):
                payload = await self._get_json(
                    active_client,
                    "/v2/tickers/resolve",
                    params={"symbols": ",".join(chunk)},
                    operation="resolver tickers",
                )
                for item in self._results(payload, operation="resolver tickers"):
                    parsed = self._parse_resolution(item)
                    if parsed is not None:
                        resolutions.append(parsed)
            return resolutions

        return await self._with_client(client, run)

    async def get_ticker_coverage(
        self,
        symbols: Sequence[str],
        *,
        client: httpx.AsyncClient | None = None,
    ) -> list[TickerCoverage]:
        """Consulta as capacidades antes de rotear requisicoes de mercado."""
        normalized = self._normalize_symbols(symbols)
        if not normalized:
            return []

        async def run(active_client: httpx.AsyncClient) -> list[TickerCoverage]:
            coverage: list[TickerCoverage] = []
            for chunk in self._chunks(normalized):
                payload = await self._get_json(
                    active_client,
                    "/v2/tickers/coverage",
                    params={"symbols": ",".join(chunk)},
                    operation="consultar cobertura de tickers",
                )
                for item in self._results(
                    payload, operation="consultar cobertura de tickers"
                ):
                    coverage.append(self._parse_coverage(item))
            return coverage

        return await self._with_client(client, run)

    async def list_ticker_renames(
        self,
        *,
        symbols: Sequence[str] = (),
        search: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[TickerRename]:
        params: dict[str, Any] = {}
        normalized = self._normalize_symbols(symbols)
        if normalized:
            params["symbols"] = ",".join(normalized)
        if search and search.strip():
            params["search"] = search.strip().upper()
        if start_date:
            params["startDate"] = start_date.isoformat()
        if end_date:
            params["endDate"] = end_date.isoformat()

        async def run(active_client: httpx.AsyncClient) -> list[TickerRename]:
            payload = await self._get_json(
                active_client,
                "/v2/tickers/renames",
                params=params,
                operation="consultar renomes de tickers",
            )
            return [
                self._parse_rename(item)
                for item in self._results(
                    payload, operation="consultar renomes de tickers"
                )
            ]

        return await self._with_client(client, run)

    async def list_tickers(
        self,
        *,
        search: str | None = None,
        asset_type: str | None = None,
        sub_type: str | None = None,
        page: int = 1,
        limit: int = 20,
        client: httpx.AsyncClient | None = None,
    ) -> TickerCatalogPage:
        if page < 1:
            raise ValueError("page deve ser maior ou igual a 1")
        if limit < 1 or limit > _MAX_CATALOG_PAGE_SIZE:
            raise ValueError(f"limit deve estar entre 1 e {_MAX_CATALOG_PAGE_SIZE}")

        params: dict[str, Any] = {"page": page, "limit": limit}
        if search and search.strip():
            params["search"] = search.strip()
        if asset_type:
            params["type"] = asset_type
        if sub_type:
            params["subType"] = sub_type

        async def run(active_client: httpx.AsyncClient) -> TickerCatalogPage:
            payload = await self._get_json(
                active_client,
                "/v2/tickers",
                params=params,
                operation="listar tickers",
            )
            pagination = payload.get("pagination")
            if not isinstance(pagination, dict):
                raise BrapiV2ContractError("Resposta invalida ao listar tickers")
            return TickerCatalogPage(
                results=tuple(
                    self._parse_catalog_item(item)
                    for item in self._results(payload, operation="listar tickers")
                ),
                page=self._required_int(pagination, "page", "listar tickers"),
                limit=self._required_int(pagination, "limit", "listar tickers"),
                total_items=self._required_int(
                    pagination, "totalItems", "listar tickers"
                ),
                total_pages=self._required_int(
                    pagination, "totalPages", "listar tickers"
                ),
                has_next_page=bool(pagination.get("hasNextPage", False)),
            )

        return await self._with_client(client, run)

    async def _with_client(self, client: httpx.AsyncClient | None, operation):
        if client is not None:
            return await operation(client)
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as owned_client:
            return await operation(owned_client)

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: Mapping[str, Any],
        operation: str,
    ) -> dict[str, Any]:
        try:
            response = await client.get(
                f"{self._base_url}{path}", headers=self._headers(), params=params
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._raise_http_error(exc.response.status_code, operation)
        except httpx.RequestError as exc:
            raise BrapiV2TransportError(f"Falha de comunicacao ao {operation}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BrapiV2ContractError(f"Resposta invalida ao {operation}") from exc
        if not isinstance(payload, dict):
            raise BrapiV2ContractError(f"Resposta invalida ao {operation}")
        return payload

    @staticmethod
    def _raise_http_error(status_code: int, operation: str) -> None:
        message = f"Falha ao {operation}: HTTP {status_code}"
        error_type: type[BrapiV2Error]
        if status_code == 401:
            error_type = BrapiV2AuthenticationError
        elif status_code == 403:
            error_type = BrapiV2PermissionError
        elif status_code == 404:
            error_type = BrapiV2NotFoundError
        elif status_code == 429:
            error_type = BrapiV2RateLimitError
        else:
            error_type = BrapiV2Error
        raise error_type(message, status_code=status_code)

    @staticmethod
    def _results(payload: Mapping[str, Any], *, operation: str) -> list[Any]:
        results = payload.get("results")
        if not isinstance(results, list):
            raise BrapiV2ContractError(f"Resposta invalida ao {operation}")
        return results

    @staticmethod
    def _chunks(symbols: list[str]) -> list[list[str]]:
        return [
            symbols[index : index + _MAX_TICKERS_PER_REQUEST]
            for index in range(0, len(symbols), _MAX_TICKERS_PER_REQUEST)
        ]

    @staticmethod
    def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for symbol in symbols:
            value = symbol.strip().upper()
            if value and value not in seen:
                seen.add(value)
                normalized.append(value)
        return normalized

    @staticmethod
    def _parse_resolution(raw: object) -> TickerResolution | None:
        if not isinstance(raw, dict):
            return None
        requested_symbol = str(raw.get("requestedSymbol") or "").strip().upper()
        symbol = str(raw.get("symbol") or "").strip().upper()
        status = str(raw.get("status") or "").strip().lower()
        if not requested_symbol or not symbol or not status:
            return None
        return TickerResolution(
            requested_symbol=requested_symbol,
            symbol=symbol,
            changed=bool(raw.get("changed", requested_symbol != symbol)),
            status=status,
            effective_date=BrapiV2Client._optional_date(raw.get("effectiveDate")),
        )

    @staticmethod
    def _parse_coverage(raw: object) -> TickerCoverage:
        if not isinstance(raw, dict):
            raise BrapiV2ContractError(
                "Resposta invalida ao consultar cobertura de tickers"
            )
        requested = BrapiV2Client._required_text(
            raw, "requestedSymbol", "consultar cobertura de tickers"
        )
        symbol = str(raw.get("symbol") or requested).strip().upper()
        status = BrapiV2Client._required_text(
            raw, "status", "consultar cobertura de tickers"
        ).lower()
        available = raw.get("availableData", {})
        recommended = raw.get("recommendedEndpoints", {})
        if available is None:
            available = {}
        if recommended is None:
            recommended = {}
        if not isinstance(available, dict) or not isinstance(recommended, dict):
            raise BrapiV2ContractError(
                "Resposta invalida ao consultar cobertura de tickers"
            )
        return TickerCoverage(
            requested_symbol=requested.upper(),
            symbol=symbol,
            changed=bool(raw.get("changed", requested.upper() != symbol)),
            status=status,
            asset_type=BrapiV2Client._optional_text(raw.get("assetType")),
            sub_type=BrapiV2Client._optional_text(raw.get("subType")),
            available_data={
                str(key): value is True for key, value in available.items()
            },
            recommended_endpoints={
                str(key): str(value) for key, value in recommended.items() if value
            },
        )

    @staticmethod
    def _parse_rename(raw: object) -> TickerRename:
        if not isinstance(raw, dict):
            raise BrapiV2ContractError(
                "Resposta invalida ao consultar renomes de tickers"
            )
        effective_date = BrapiV2Client._optional_date(raw.get("effectiveDate"))
        if effective_date is None:
            raise BrapiV2ContractError(
                "Resposta invalida ao consultar renomes de tickers"
            )
        return TickerRename(
            old_symbol=BrapiV2Client._required_text(
                raw, "oldSymbol", "consultar renomes de tickers"
            ).upper(),
            new_symbol=BrapiV2Client._required_text(
                raw, "newSymbol", "consultar renomes de tickers"
            ).upper(),
            canonical_symbol=BrapiV2Client._required_text(
                raw, "canonicalSymbol", "consultar renomes de tickers"
            ).upper(),
            effective_date=effective_date,
        )

    @staticmethod
    def _parse_catalog_item(raw: object) -> TickerCatalogItem:
        if not isinstance(raw, dict):
            raise BrapiV2ContractError("Resposta invalida ao listar tickers")
        return TickerCatalogItem(
            symbol=BrapiV2Client._required_text(
                raw, "symbol", "listar tickers"
            ).upper(),
            name=BrapiV2Client._required_text(raw, "name", "listar tickers"),
            long_name=BrapiV2Client._optional_text(raw.get("longName")),
            asset_type=BrapiV2Client._required_text(raw, "assetType", "listar tickers"),
            sub_type=BrapiV2Client._optional_text(raw.get("subType")),
            exchange=BrapiV2Client._optional_text(raw.get("exchange")),
            currency=BrapiV2Client._optional_text(raw.get("currency")),
            sector=BrapiV2Client._optional_text(raw.get("sector")),
            subsector=BrapiV2Client._optional_text(raw.get("subsector")),
            is_active=bool(raw.get("isActive", True)),
            logo_url=BrapiV2Client._optional_text(raw.get("logoUrl")),
        )

    @staticmethod
    def _required_text(raw: Mapping[str, Any], key: str, operation: str) -> str:
        value = str(raw.get(key) or "").strip()
        if not value:
            raise BrapiV2ContractError(f"Resposta invalida ao {operation}")
        return value

    @staticmethod
    def _required_int(raw: Mapping[str, Any], key: str, operation: str) -> int:
        value = raw.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise BrapiV2ContractError(f"Resposta invalida ao {operation}")
        return value

    @staticmethod
    def _optional_text(raw: object) -> str | None:
        value = str(raw or "").strip()
        return value or None

    @staticmethod
    def _optional_date(raw: object) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None
