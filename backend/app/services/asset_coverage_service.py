"""Servico de cobertura por ativo e controle de capacidades de endpoints externos.

Mapeia quais recursos (cotacoes, historico, proventos, indicadores) estao
disponiveis para cada ticker, evitando chamadas repetidas a endpoints 404,
respeitando TTLs por tipo de status e permitindo operacao de ativos com
cobertura parcial sem marca-los como invalidos.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.cache import cache_get, cache_set, get_redis

logger = logging.getLogger(__name__)

# TTLs em segundos
TTL_SUPPORTED = 7 * 86400       # 7 dias para recursos confirmados
TTL_UNSUPPORTED = 86400         # 24 horas para 404/nao suportado
TTL_TRANSIENT_ERROR = 900       # 15 minutos para erros transitorios (5xx, timeout)

KEY_PREFIX = "coverage:"

# Capacidades suportadas
CAPABILITY_QUOTE = "quote"
CAPABILITY_HISTORY = "history"
CAPABILITY_DIVIDENDS = "dividends"
CAPABILITY_INDICATORS = "indicators"
CAPABILITY_REAL_ESTATE = "real_estate"

# Status de cobertura
STATUS_FULL = "FULL"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNSUPPORTED = "UNSUPPORTED"
STATUS_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AssetCoverageReport:
    ticker: str
    provider: str
    status: str
    capabilities: dict[str, bool]
    last_checked_at: str
    error_code: Optional[str] = None
    ttl_seconds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AssetCoverageService:
    """Gerencia cobertura de endpoints por ativo com cache Redis e fallback em memoria."""

    def __init__(self) -> None:
        self._memory_cache: dict[str, dict[str, Any]] = {}

    def _cache_key(self, ticker: str, provider: str = "brapi") -> str:
        return f"{KEY_PREFIX}{provider.lower()}:{ticker.strip().upper()}"

    async def get_coverage(
        self, ticker: str, provider: str = "brapi"
    ) -> Optional[AssetCoverageReport]:
        normalized_ticker = ticker.strip().upper()
        key = self._cache_key(normalized_ticker, provider)

        # 1. Tentar ler da memoria local L1
        cached = self._memory_cache.get(key)
        if cached is None:
            # 2. Tentar ler do Redis L2
            cached = await cache_get(key)

        if not cached or not isinstance(cached, dict):
            return None

        return AssetCoverageReport(
            ticker=normalized_ticker,
            provider=cached.get("provider", provider),
            status=cached.get("status", STATUS_UNKNOWN),
            capabilities=cached.get("capabilities", {}),
            last_checked_at=cached.get(
                "last_checked_at", datetime.now(timezone.utc).isoformat()
            ),
            error_code=cached.get("error_code"),
            ttl_seconds=cached.get("ttl_seconds", TTL_SUPPORTED),
        )

    async def is_supported(
        self, ticker: str, capability: str, provider: str = "brapi"
    ) -> bool:
        """Verifica se uma capacidade especifica esta disponivel.

        Retorna True caso a capacidade seja suportada ou caso o ticker ainda nao
        tenha sido testado (fail-open para descoberta). Retorna False somente se
        houver registro explicito de indisponibilidade dentro do TTL.
        """
        report = await self.get_coverage(ticker, provider)
        if report is None:
            return True

        # Se a capacidade estiver explicitamente marcada como False, bloqueia chamada
        return report.capabilities.get(capability, True)

    async def record_capability(
        self,
        ticker: str,
        capability: str,
        supported: bool,
        *,
        error_code: Optional[str] = None,
        provider: str = "brapi",
    ) -> AssetCoverageReport:
        """Registra o resultado da consulta de um endpoint para o ticker."""
        normalized_ticker = ticker.strip().upper()
        key = self._cache_key(normalized_ticker, provider)

        # Carregar estado existente ou inicializar
        current = await self.get_coverage(normalized_ticker, provider)
        capabilities: dict[str, bool] = {}
        if current:
            capabilities = dict(current.capabilities)

        capabilities[capability] = supported

        # Determinar status global
        if all(capabilities.values()):
            status = STATUS_FULL
        elif not any(capabilities.values()):
            status = STATUS_UNSUPPORTED
        else:
            status = STATUS_PARTIAL

        # Escolher TTL adequado
        if not supported:
            if error_code and ("5" in error_code or "TIMEOUT" in error_code):
                ttl = TTL_TRANSIENT_ERROR
            else:
                ttl = TTL_UNSUPPORTED
        else:
            ttl = TTL_SUPPORTED

        report = AssetCoverageReport(
            ticker=normalized_ticker,
            provider=provider,
            status=status,
            capabilities=capabilities,
            last_checked_at=datetime.now(timezone.utc).isoformat(),
            error_code=error_code if not supported else None,
            ttl_seconds=ttl,
        )

        data = report.to_dict()
        # Salva em memoria
        self._memory_cache[key] = data

        # Salva no Redis com TTL correspondente
        await cache_set(key, data, ttl=ttl)

        logger.info(
            "[coverage] Ticker %s capability '%s'=%s -> status=%s (ttl=%ds)",
            normalized_ticker,
            capability,
            supported,
            status,
            ttl,
        )
        return report

    async def list_all_coverages(
        self, limit: int = 100, provider: str = "brapi"
    ) -> list[AssetCoverageReport]:
        """Lista registros de cobertura para diagnostico administrativo."""
        reports: dict[str, AssetCoverageReport] = {}

        # 1. Carregar da memoria
        for key, data in self._memory_cache.items():
            if key.startswith(f"{KEY_PREFIX}{provider.lower()}:"):
                ticker = data.get("ticker", "")
                if ticker:
                    reports[ticker] = AssetCoverageReport(
                        ticker=ticker,
                        provider=data.get("provider", provider),
                        status=data.get("status", STATUS_UNKNOWN),
                        capabilities=data.get("capabilities", {}),
                        last_checked_at=data.get(
                            "last_checked_at", datetime.now(timezone.utc).isoformat()
                        ),
                        error_code=data.get("error_code"),
                        ttl_seconds=data.get("ttl_seconds", TTL_SUPPORTED),
                    )

        # 2. Consultar chaves no Redis se disponivel
        client = await get_redis()
        if client:
            try:
                pattern = f"{KEY_PREFIX}{provider.lower()}:*"
                cursor = 0
                keys: list[str] = []
                while True:
                    cursor, batch = await client.scan(cursor, match=pattern, count=100)
                    keys.extend(batch)
                    if cursor == 0 or len(keys) >= limit:
                        break

                for key in keys[:limit]:
                    data = await cache_get(key)
                    if data and isinstance(data, dict):
                        ticker = data.get("ticker", "")
                        if ticker:
                            reports[ticker] = AssetCoverageReport(
                                ticker=ticker,
                                provider=data.get("provider", provider),
                                status=data.get("status", STATUS_UNKNOWN),
                                capabilities=data.get("capabilities", {}),
                                last_checked_at=data.get(
                                    "last_checked_at",
                                    datetime.now(timezone.utc).isoformat(),
                                ),
                                error_code=data.get("error_code"),
                                ttl_seconds=data.get("ttl_seconds", TTL_SUPPORTED),
                            )
            except Exception as exc:
                logger.warning("Falha ao escanear chaves de cobertura no Redis: %s", exc)

        return sorted(reports.values(), key=lambda r: r.ticker)[:limit]

    async def clear_coverage(
        self, ticker: Optional[str] = None, provider: str = "brapi"
    ) -> int:
        """Limpa cache de cobertura de um ticker especifico ou de todos."""
        count = 0
        if ticker:
            key = self._cache_key(ticker, provider)
            self._memory_cache.pop(key, None)
            client = await get_redis()
            if client:
                try:
                    await client.delete(key)
                    count = 1
                except Exception:
                    pass
            return count

        # Limpeza geral
        self._memory_cache.clear()
        client = await get_redis()
        if client:
            try:
                pattern = f"{KEY_PREFIX}*"
                cursor = 0
                while True:
                    cursor, keys = await client.scan(cursor, match=pattern, count=100)
                    if keys:
                        await client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception as exc:
                logger.warning("Falha ao limpar chaves no Redis: %s", exc)

        return count


# Instancia singleton global do servico
asset_coverage_service = AssetCoverageService()
