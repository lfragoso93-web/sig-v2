"""Servico de enriquecimento de ativos, fundamentos e dados macroeconomicos (Issue #130).

Gerencia consultas tipadas a FIIs (Bloco 5), fundamentos de acoes (Bloco 6)
e dados macroeconomicos/cambio (Bloco 7), respeitando cache, TTLs e diagnostico
de cobertura do AssetCoverageService.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.core.cache import get_redis
from app.integrations.brapi_v2_client import (
    BrapiV2Client,
    CompanyFundamentalsDTO,
    FIIIndicatorDTO,
    MacroSeriesPointDTO,
)
from app.services.asset_coverage_service import asset_coverage_service

logger = logging.getLogger(__name__)

# TTLs de cache para dados enriquecidos
TTL_FUNDAMENTALS_SECONDS = 86400  # 24 horas para fundamentos e indicadores
TTL_MACRO_SECONDS = 43200  # 12 horas para series macroeconomicas


class AssetEnrichmentService:
    """Orquestrador de dados fundamentalistas, de vacancia e macroeconomicos."""

    def __init__(self, client: Optional[BrapiV2Client] = None) -> None:
        self._client = client or BrapiV2Client()
        self._memory_cache: dict[str, tuple[float, Any]] = {}

    # -------------------------------------------------------------------------
    # Bloco 5: Indicadores e Vacancia de FIIs
    # -------------------------------------------------------------------------

    async def get_fii_indicators(
        self,
        ticker: str,
        *,
        force_refresh: bool = False,
    ) -> Optional[FIIIndicatorDTO]:
        """Obtem metricas operacionais e de vacancia de FII com cache e respeito a cobertura."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            return None

        # 1. Verifica se a capacidade esta bloqueada por cooldown no coverage service
        if not force_refresh:
            supported = await asset_coverage_service.is_supported(clean_ticker, "indicators")
            if not supported:
                return None

        # 2. Cache L1 / L2
        cache_key = f"fii_indicators:{clean_ticker}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                return FIIIndicatorDTO(**cached)

        # 3. Consulta ao provedor via cliente tipado v2
        try:
            dto = await self._client.fetch_fii_indicators(clean_ticker)
            if dto is not None:
                await asset_coverage_service.record_capability(
                    clean_ticker, "indicators", True
                )
                if dto.properties_count or dto.physical_vacancy is not None:
                    await asset_coverage_service.record_capability(
                        clean_ticker, "real_estate", True
                    )
                # Salva em cache
                payload = {
                    "symbol": dto.symbol,
                    "pvp": dto.pvp,
                    "dividend_yield": dto.dividend_yield,
                    "net_worth": dto.net_worth,
                    "share_holders": dto.share_holders,
                    "physical_vacancy": dto.physical_vacancy,
                    "financial_vacancy": dto.financial_vacancy,
                    "properties_count": dto.properties_count,
                    "segment": dto.segment,
                }
                await self._set_cached(cache_key, payload, TTL_FUNDAMENTALS_SECONDS)
                return dto
            else:
                await asset_coverage_service.record_capability(
                    clean_ticker, "indicators", False, error_code="404"
                )
                return None
        except Exception as exc:
            logger.warning("Falha ao enriquecer FII %s: %s", clean_ticker, exc)
            await asset_coverage_service.record_capability(
                clean_ticker, "indicators", False, error_code="ERROR"
            )
            return None

    # -------------------------------------------------------------------------
    # Bloco 6: Fundamentos de Acoes
    # -------------------------------------------------------------------------

    async def get_stock_fundamentals(
        self,
        ticker: str,
        *,
        force_refresh: bool = False,
    ) -> Optional[CompanyFundamentalsDTO]:
        """Obtem metricas fundamentalistas consolidadas para acoes com cache."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            return None

        # 1. Verifica cobertura previa
        if not force_refresh:
            supported = await asset_coverage_service.is_supported(clean_ticker, "indicators")
            if not supported:
                return None

        # 2. Cache L1 / L2
        cache_key = f"stock_fundamentals:{clean_ticker}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                return CompanyFundamentalsDTO(**cached)

        # 3. Consulta ao provedor via cliente tipado v2
        try:
            dto = await self._client.fetch_company_fundamentals(clean_ticker)
            if dto is not None:
                await asset_coverage_service.record_capability(
                    clean_ticker, "indicators", True
                )
                payload = {
                    "symbol": dto.symbol,
                    "pe": dto.pe,
                    "pb": dto.pb,
                    "dividend_yield": dto.dividend_yield,
                    "eps": dto.eps,
                    "market_cap": dto.market_cap,
                    "net_revenue": dto.net_revenue,
                    "net_income": dto.net_income,
                    "ebitda": dto.ebitda,
                    "net_margin": dto.net_margin,
                    "roe": dto.roe,
                    "net_debt": dto.net_debt,
                }
                await self._set_cached(cache_key, payload, TTL_FUNDAMENTALS_SECONDS)
                return dto
            else:
                await asset_coverage_service.record_capability(
                    clean_ticker, "indicators", False, error_code="404"
                )
                return None
        except Exception as exc:
            logger.warning("Falha ao buscar fundamentos de %s: %s", clean_ticker, exc)
            await asset_coverage_service.record_capability(
                clean_ticker, "indicators", False, error_code="ERROR"
            )
            return None

    # -------------------------------------------------------------------------
    # Bloco 7: Series Macroeconomicas e Indicadores
    # -------------------------------------------------------------------------

    async def get_macro_series(
        self,
        indicator_name: str,
        *,
        force_refresh: bool = False,
    ) -> list[MacroSeriesPointDTO]:
        """Obtem serie historica macroeconomica (SELIC, CDI, IPCA, IGPM, USD-BRL)."""
        clean_name = indicator_name.strip().upper()
        if not clean_name:
            return []

        cache_key = f"macro_series:{clean_name}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if isinstance(cached, list):
                from datetime import date
                return [
                    MacroSeriesPointDTO(
                        name=clean_name,
                        point_date=date.fromisoformat(item["date"]),
                        value=float(item["value"]),
                    )
                    for item in cached
                ]

        try:
            points = await self._client.fetch_macro_series(clean_name)
            if points:
                payload = [
                    {"date": p.point_date.isoformat(), "value": p.value}
                    for p in points
                ]
                await self._set_cached(cache_key, payload, TTL_MACRO_SECONDS)
            return points
        except Exception as exc:
            logger.warning("Falha ao buscar serie macro %s: %s", clean_name, exc)
            return []

    # -------------------------------------------------------------------------
    # Enriquecimento Unificado por Ativo
    # -------------------------------------------------------------------------

    async def get_asset_enrichment(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
    ) -> dict[str, Any]:
        """Retorna diagnostico e dados consolidados conforme a classe do ativo."""
        clean_ticker = ticker.strip().upper()
        tipo = (asset_type or "").upper()

        report = await asset_coverage_service.get_coverage(clean_ticker)
        status = report.status if report else "UNKNOWN"
        capabilities = report.capabilities if report else {}

        result: dict[str, Any] = {
            "ticker": clean_ticker,
            "coverage_status": status,
            "capabilities": capabilities,
            "fii_indicators": None,
            "stock_fundamentals": None,
        }

        if tipo == "FII" or (not tipo and (clean_ticker.endswith("11") and not clean_ticker.startswith("B"))):
            fii_dto = await self.get_fii_indicators(clean_ticker)
            if fii_dto:
                result["fii_indicators"] = {
                    "pvp": fii_dto.pvp,
                    "dividend_yield": fii_dto.dividend_yield,
                    "net_worth": fii_dto.net_worth,
                    "share_holders": fii_dto.share_holders,
                    "physical_vacancy": fii_dto.physical_vacancy,
                    "financial_vacancy": fii_dto.financial_vacancy,
                    "properties_count": fii_dto.properties_count,
                    "segment": fii_dto.segment,
                }
        else:
            stock_dto = await self.get_stock_fundamentals(clean_ticker)
            if stock_dto:
                result["stock_fundamentals"] = {
                    "pe": stock_dto.pe,
                    "pb": stock_dto.pb,
                    "dividend_yield": stock_dto.dividend_yield,
                    "eps": stock_dto.eps,
                    "market_cap": stock_dto.market_cap,
                    "net_revenue": stock_dto.net_revenue,
                    "net_income": stock_dto.net_income,
                    "ebitda": stock_dto.ebitda,
                    "net_margin": stock_dto.net_margin,
                    "roe": stock_dto.roe,
                    "net_debt": stock_dto.net_debt,
                }

        return result

    # -------------------------------------------------------------------------
    # Helpers de Cache
    # -------------------------------------------------------------------------

    async def _get_cached(self, key: str) -> Optional[Any]:
        # Memoria L1
        import time
        if key in self._memory_cache:
            expires_at, val = self._memory_cache[key]
            if time.time() < expires_at:
                return val
            del self._memory_cache[key]

        # Redis L2
        redis_client = await get_redis()
        if redis_client is not None:
            try:
                raw = await redis_client.get(key)
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        return None

    async def _set_cached(self, key: str, val: Any, ttl_seconds: int) -> None:
        import time
        self._memory_cache[key] = (time.time() + ttl_seconds, val)

        redis_client = await get_redis()
        if redis_client is not None:
            try:
                await redis_client.set(key, json.dumps(val), ex=ttl_seconds)
            except Exception:
                pass


# Instancia singleton
asset_enrichment_service = AssetEnrichmentService()
