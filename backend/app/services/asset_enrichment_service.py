"""Servico de enriquecimento de ativos, fundamentos e dados macroeconomicos (Issue #130).

Gerencia consultas tipadas a FIIs (Bloco 5), fundamentos de acoes (Bloco 6),
dados macroeconomicos/cambio (Bloco 7), alem de ativos internacionais (Finnhub),
criptoativos (BRAPI + CoinGecko) e Tesouro Direto.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.core.cache import get_redis
from app.core.log_safety import sanitize_log_value
from app.integrations.brapi_crypto_catalog import fetch_crypto_quote_and_metrics
from app.integrations.brapi_treasury import fetch_treasury_bond_detail
from app.integrations.brapi_v2_client import (
    BrapiV2Client,
    CompanyFundamentalsDTO,
    FIIIndicatorDTO,
    MacroSeriesPointDTO,
)
from app.integrations.finnhub import fetch_finnhub_enrichment
from app.services.asset_coverage_service import asset_coverage_service

logger = logging.getLogger(__name__)

# TTLs de cache para dados enriquecidos
TTL_FUNDAMENTALS_SECONDS = 86400  # 24 horas para fundamentos e indicadores
TTL_MACRO_SECONDS = 43200  # 12 horas para series macroeconomicas
TTL_CRYPTO_SECONDS = 600  # 10 minutos para criptoativos
TTL_TREASURY_SECONDS = 43200  # 12 horas para títulos públicos


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
            if cached is not None and isinstance(cached, dict):
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
                    "dividend_yield_1m": dto.dividend_yield_1m,
                    "net_worth": dto.net_worth,
                    "nav_per_share": dto.nav_per_share,
                    "share_holders": dto.share_holders,
                    "shares_outstanding": dto.shares_outstanding,
                    "physical_vacancy": dto.physical_vacancy,
                    "financial_vacancy": dto.financial_vacancy,
                    "properties_count": dto.properties_count,
                    "total_area_m2": dto.total_area_m2,
                    "segment": dto.segment,
                    "segment_type": dto.segment_type,
                    "management_type": dto.management_type,
                    "administrator_name": dto.administrator_name,
                    "administrator_cnpj": dto.administrator_cnpj,
                    "cnpj": dto.cnpj,
                }
                await self._set_cached(cache_key, payload, TTL_FUNDAMENTALS_SECONDS)
                return dto
            else:
                await asset_coverage_service.record_capability(
                    clean_ticker, "indicators", False, error_code="404"
                )
                return None
        except Exception as exc:
            logger.warning("Falha ao enriquecer FII %s: %s", sanitize_log_value(clean_ticker), sanitize_log_value(exc))
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
            if cached is not None and isinstance(cached, dict):
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
                    "forward_pe": dto.forward_pe,
                    "pb": dto.pb,
                    "dividend_yield": dto.dividend_yield,
                    "eps": dto.eps,
                    "market_cap": dto.market_cap,
                    "enterprise_value": dto.enterprise_value,
                    "enterprise_to_ebitda": dto.enterprise_to_ebitda,
                    "net_revenue": dto.net_revenue,
                    "net_income": dto.net_income,
                    "ebitda": dto.ebitda,
                    "net_margin": dto.net_margin,
                    "operating_margin": dto.operating_margin,
                    "gross_margin": dto.gross_margin,
                    "roe": dto.roe,
                    "roa": dto.roa,
                    "net_debt": dto.net_debt,
                    "total_debt": dto.total_debt,
                    "free_cash_flow": dto.free_cash_flow,
                    "book_value": dto.book_value,
                    "peg_ratio": dto.peg_ratio,
                    "beta": dto.beta,
                    "sector": dto.sector,
                    "industry": dto.industry,
                    "description": dto.description,
                    "website": dto.website,
                    "employees": dto.employees,
                    "recommendation": dto.recommendation,
                    "target_price": dto.target_price,
                }
                await self._set_cached(cache_key, payload, TTL_FUNDAMENTALS_SECONDS)
                return dto
            else:
                await asset_coverage_service.record_capability(
                    clean_ticker, "indicators", False, error_code="404"
                )
                return None
        except Exception as exc:
            logger.warning("Falha ao buscar fundamentos de %s: %s", sanitize_log_value(clean_ticker), sanitize_log_value(exc))
            await asset_coverage_service.record_capability(
                clean_ticker, "indicators", False, error_code="ERROR"
            )
            return None

    # -------------------------------------------------------------------------
    # Ativos Internacionais: Finnhub Enrichment
    # -------------------------------------------------------------------------

    async def get_international_fundamentals(
        self,
        ticker: str,
        *,
        force_refresh: bool = False,
    ) -> Optional[dict[str, Any]]:
        """Obtém fundamentos e consenso internacional consolidando Finnhub."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            return None

        cache_key = f"intl_fundamentals:{clean_ticker}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached

        try:
            finnhub_raw = await fetch_finnhub_enrichment(clean_ticker)
            if not finnhub_raw:
                return None

            raw_p = finnhub_raw.get("profile")
            profile: dict[str, Any] = raw_p if isinstance(raw_p, dict) else {}
            raw_m = finnhub_raw.get("metrics")
            metrics: dict[str, Any] = raw_m if isinstance(raw_m, dict) else {}
            raw_r = finnhub_raw.get("recommendations")
            recs: dict[str, Any] = raw_r if isinstance(raw_r, dict) else {}

            stock_fundamentals = {
                "pe": metrics.get("pe"),
                "forward_pe": None,
                "pb": metrics.get("pb"),
                "dividend_yield": metrics.get("dividend_yield"),
                "eps": metrics.get("eps"),
                "market_cap": profile.get("market_cap"),
                "enterprise_value": None,
                "enterprise_to_ebitda": None,
                "net_revenue": None,
                "net_income": None,
                "ebitda": None,
                "net_margin": metrics.get("net_margin"),
                "operating_margin": metrics.get("operating_margin"),
                "gross_margin": None,
                "roe": metrics.get("roe"),
                "roa": metrics.get("roa"),
                "net_debt": None,
                "total_debt": None,
                "free_cash_flow": None,
                "book_value": None,
                "peg_ratio": None,
                "beta": metrics.get("beta"),
                "sector": profile.get("industry"),
                "industry": profile.get("industry"),
                "description": f"{profile.get('name', clean_ticker)} é uma empresa listada em {profile.get('exchange', 'Bolsa Global')} ({profile.get('country', 'Exterior')}).",
                "website": profile.get("weburl"),
                "employees": None,
                "recommendation": recs.get("consensus"),
                "target_price": None,
            }

            intl_profile = {
                "country": profile.get("country"),
                "currency": profile.get("currency"),
                "exchange": profile.get("exchange"),
                "industry": profile.get("industry"),
                "weburl": profile.get("weburl"),
                "logo": profile.get("logo"),
                "market_cap_usd": profile.get("market_cap"),
                "consensus": recs.get("consensus"),
                "strong_buy": recs.get("strong_buy"),
                "buy": recs.get("buy"),
                "hold": recs.get("hold"),
                "sell": recs.get("sell"),
                "strong_sell": recs.get("strong_sell"),
            }

            data = {
                "stock_fundamentals": stock_fundamentals,
                "international_profile": intl_profile,
            }
            await self._set_cached(cache_key, data, TTL_FUNDAMENTALS_SECONDS)
            return data
        except Exception as exc:
            logger.warning("Falha ao enriquecer internacional %s: %s", sanitize_log_value(clean_ticker), sanitize_log_value(exc))
            return None

    # -------------------------------------------------------------------------
    # Criptoativos: BRAPI + CoinGecko
    # -------------------------------------------------------------------------

    async def get_crypto_indicators(
        self,
        coin: str,
        *,
        force_refresh: bool = False,
    ) -> Optional[dict[str, Any]]:
        """Obtém dados ao vivo e indicadores operacionais de criptomoeda."""
        clean_coin = coin.strip().upper()
        if not clean_coin:
            return None

        cache_key = f"crypto_indicators:{clean_coin}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached

        try:
            data = await fetch_crypto_quote_and_metrics(clean_coin)
            if data is not None:
                await self._set_cached(cache_key, data, TTL_CRYPTO_SECONDS)
                return data
            return None
        except Exception as exc:
            logger.warning("Falha ao buscar indicadores cripto %s: %s", sanitize_log_value(clean_coin), sanitize_log_value(exc))
            return None

    # -------------------------------------------------------------------------
    # Tesouro Direto: BRAPI Treasury
    # -------------------------------------------------------------------------

    async def get_treasury_indicators(
        self,
        symbol_or_name: str,
        *,
        force_refresh: bool = False,
    ) -> Optional[dict[str, Any]]:
        """Obtém taxas indicativas, PU e características de título público."""
        raw = symbol_or_name.strip()
        if not raw:
            return None

        cache_key = f"treasury_indicators:{raw.lower()}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached

        try:
            data = await fetch_treasury_bond_detail(raw)
            if data is not None:
                await self._set_cached(cache_key, data, TTL_TREASURY_SECONDS)
                return data
            return None
        except Exception as exc:
            logger.warning("Falha ao buscar indicadores do Tesouro %s: %s", sanitize_log_value(raw), sanitize_log_value(exc))
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
            logger.warning("Falha ao buscar serie macro %s: %s", sanitize_log_value(clean_name), sanitize_log_value(exc))
            return []

    # -------------------------------------------------------------------------
    # Enriquecimento Unificado por Ativo
    # -------------------------------------------------------------------------

    async def get_asset_enrichment(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
        *,
        force_refresh: bool = False,
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
            "crypto_indicators": None,
            "treasury_indicators": None,
            "international_profile": None,
        }

        # 1. Criptoativos
        known_cryptos = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "LTC", "BNB"}
        is_crypto = (
            tipo in ("CRIPTO", "CRYPTO")
            or clean_ticker in known_cryptos
            or clean_ticker.endswith(("-USD", "-BRL", "USDT"))
        )
        if is_crypto:
            result["crypto_indicators"] = await self.get_crypto_indicators(clean_ticker, force_refresh=force_refresh)
            return result

        # 2. Tesouro Direto / Renda Fixa Pública
        is_treasury = (
            tipo in ("TESOURO_DIRETO", "RENDA_FIXA")
            or clean_ticker.lower().startswith("tesouro-")
            or "tesouro" in clean_ticker.lower()
        )
        if is_treasury:
            result["treasury_indicators"] = await self.get_treasury_indicators(clean_ticker, force_refresh=force_refresh)
            return result

        # 3. Fundos Imobiliários (FII)
        is_fii = tipo == "FII" or (not tipo and (clean_ticker.endswith("11") and not clean_ticker.startswith("B") and not clean_ticker.startswith("IVV")))
        if is_fii:
            fii_dto = await self.get_fii_indicators(clean_ticker, force_refresh=force_refresh)
            if fii_dto:
                result["fii_indicators"] = {
                    "pvp": fii_dto.pvp,
                    "dividend_yield": fii_dto.dividend_yield,
                    "dividend_yield_1m": fii_dto.dividend_yield_1m,
                    "net_worth": fii_dto.net_worth,
                    "nav_per_share": fii_dto.nav_per_share,
                    "share_holders": fii_dto.share_holders,
                    "shares_outstanding": fii_dto.shares_outstanding,
                    "physical_vacancy": fii_dto.physical_vacancy,
                    "financial_vacancy": fii_dto.financial_vacancy,
                    "properties_count": fii_dto.properties_count,
                    "total_area_m2": fii_dto.total_area_m2,
                    "segment": fii_dto.segment,
                    "segment_type": fii_dto.segment_type,
                    "management_type": fii_dto.management_type,
                    "administrator_name": fii_dto.administrator_name,
                    "administrator_cnpj": fii_dto.administrator_cnpj,
                    "cnpj": fii_dto.cnpj,
                }
            return result

        # 4. Ativos Internacionais (Stocks e ETFs globais)
        is_intl = (
            tipo in ("STOCK", "ETF_INT")
            or (not tipo and bool(re.match(r"^[A-Z]{1,5}$", clean_ticker)) and not bool(re.search(r"\d", clean_ticker)))
        )
        if is_intl:
            intl_data = await self.get_international_fundamentals(clean_ticker, force_refresh=force_refresh)
            if intl_data:
                result["stock_fundamentals"] = intl_data.get("stock_fundamentals")
                result["international_profile"] = intl_data.get("international_profile")
                return result

        # 5. Ações Nacionais (Default / Ações B3)
        stock_dto = await self.get_stock_fundamentals(clean_ticker, force_refresh=force_refresh)
        if stock_dto:
            result["stock_fundamentals"] = {
                "pe": stock_dto.pe,
                "forward_pe": stock_dto.forward_pe,
                "pb": stock_dto.pb,
                "dividend_yield": stock_dto.dividend_yield,
                "eps": stock_dto.eps,
                "market_cap": stock_dto.market_cap,
                "enterprise_value": stock_dto.enterprise_value,
                "enterprise_to_ebitda": stock_dto.enterprise_to_ebitda,
                "net_revenue": stock_dto.net_revenue,
                "net_income": stock_dto.net_income,
                "ebitda": stock_dto.ebitda,
                "net_margin": stock_dto.net_margin,
                "operating_margin": stock_dto.operating_margin,
                "gross_margin": stock_dto.gross_margin,
                "roe": stock_dto.roe,
                "roa": stock_dto.roa,
                "net_debt": stock_dto.net_debt,
                "total_debt": stock_dto.total_debt,
                "free_cash_flow": stock_dto.free_cash_flow,
                "book_value": stock_dto.book_value,
                "peg_ratio": stock_dto.peg_ratio,
                "beta": stock_dto.beta,
                "sector": stock_dto.sector,
                "industry": stock_dto.industry,
                "description": stock_dto.description,
                "website": stock_dto.website,
                "employees": stock_dto.employees,
                "recommendation": stock_dto.recommendation,
                "target_price": stock_dto.target_price,
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
