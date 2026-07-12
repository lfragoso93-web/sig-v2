"""Cliente tipado e isolado para contratos v2 de dados de mercado.

O módulo atual de integração permanece ativo durante a migração incremental.
Este cliente não deve expor payloads brutos para routers ou frontend.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

import httpx

from app.core.config import settings


_MAX_TICKERS_PER_REQUEST = 20
_DEFAULT_TIMEOUT_SECONDS = 15.0


class BrapiV2Error(RuntimeError):
    """Erro normalizado da integração v2."""


@dataclass(frozen=True)
class TickerResolution:
    """Resultado interno de normalização de um ticker informado pelo usuário."""

    requested_symbol: str
    symbol: str
    changed: bool
    status: str
    effective_date: Optional[date] = None


class BrapiV2Client:
    """Cliente mínimo para endpoints v2, com contratos internos estáveis."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = (base_url or settings.BRAPI_BASE_URL).rstrip("/")
        self._token = token if token is not None else settings.BRAPI_TOKEN
        self._timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    async def resolve_tickers(
        self,
        symbols: Sequence[str],
        *,
        client: Optional[httpx.AsyncClient] = None,
    ) -> list[TickerResolution]:
        """Resolve tickers antigos para os códigos atuais, preservando a ordem.

        A API aceita no máximo 20 símbolos por chamada. A função divide lotes
        maiores e retorna apenas itens válidos recebidos do provedor.
        """
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
            response = await client.get(
                f"{self._base_url}/v2/tickers/resolve",
                headers=self._headers(),
                params={"symbols": ",".join(chunk)},
            )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise BrapiV2Error(
                    f"Falha ao resolver tickers: HTTP {response.status_code}"
                ) from exc

            payload = response.json()
            raw_results = payload.get("results")
            if not isinstance(raw_results, list):
                raise BrapiV2Error("Resposta inválida ao resolver tickers")

            for item in raw_results:
                parsed = self._parse_resolution(item)
                if parsed is not None:
                    resolutions.append(parsed)

        return resolutions

    @staticmethod
    def _normalize_symbols(symbols: Sequence[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for symbol in symbols:
            value = symbol.strip().upper()
            if not value or value in seen:
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
