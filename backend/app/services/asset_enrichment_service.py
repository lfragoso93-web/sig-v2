"""Servico de enriquecimento de ativos, fundamentos e dados macroeconomicos (Issue #130).

Gerencia consultas tipadas a FIIs (Bloco 5), fundamentos de acoes (Bloco 6),
dados macroeconomicos/cambio (Bloco 7), alem de ativos internacionais (Finnhub),
criptoativos (BRAPI + CoinGecko) e Tesouro Direto.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend

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
TTL_DIVIDENDS_SECONDS = 21600  # 6 horas para histórico de proventos

ETF_CURATED_DATA: dict[str, dict[str, Any]] = {
    "BOVA11": {
        "benchmark": "Índice Bovespa (IBOV)",
        "expense_ratio": 0.10,
        "manager": "BlackRock (iShares)",
        "administrator": "BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Renda Variável Brasil",
        "description": "Replica a carteira teórica do Ibovespa, principal indicador do mercado acionário brasileiro.",
    },
    "SMAL11": {
        "benchmark": "Índice Small Cap (SMLL)",
        "expense_ratio": 0.50,
        "manager": "BlackRock (iShares)",
        "administrator": "BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Small Caps Brasil",
        "description": "Oferece exposição diversificada às empresas de menor capitalização de mercado listadas na B3.",
    },
    "IVVB11": {
        "benchmark": "S&P 500 Index (USD)",
        "expense_ratio": 0.23,
        "manager": "BlackRock (iShares)",
        "administrator": "BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Renda Variável Internacional",
        "description": "Replica o desempenho das 500 maiores empresas de capital aberto dos EUA com exposição cambial.",
    },
    "SPXI11": {
        "benchmark": "S&P 500 Index (USD)",
        "expense_ratio": 0.18,
        "manager": "Itaú (It Now)",
        "administrator": "Itaú Unibanco S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Renda Variável Internacional",
        "description": "Fundo de índice que busca retornos correspondentes à performance em Reais do índice S&P 500.",
    },
    "NDIV11": {
        "benchmark": "IBOV Smart Dividendos B3",
        "expense_ratio": 0.50,
        "manager": "Nu Asset Management",
        "administrator": "Banco BNP Paribas Brasil S.A.",
        "dividend_policy": "Distribuição Mensal de Proventos",
        "dividend_yield": 8.4,
        "category": "Estratégia Smart Beta Dividendos",
        "description": "Primeiro ETF brasileiro a pagar dividendos mensais aos cotistas, ponderado por histórico de proventos.",
    },
    "NSDV11": {
        "benchmark": "IBOV Smart Dividendos B3",
        "expense_ratio": 0.50,
        "manager": "Nu Asset Management",
        "administrator": "Banco BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Estratégia Smart Beta Dividendos",
        "description": "Versão com acumulação de proventos do índice IBOV Smart Dividendos B3.",
    },
    "HASH11": {
        "benchmark": "Nasdaq Crypto Index (NCI)",
        "expense_ratio": 1.30,
        "manager": "Hashdex Gestora de Recursos",
        "administrator": "Genial Investimentos CVM",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Criptoativos & Cesta Multimoedas",
        "description": "ETF pioneiro de criptoativos no Brasil, acompanhando o índice desenvolvido pela Nasdaq e Hashdex.",
    },
    "BBOV11": {
        "benchmark": "Índice Bovespa (IBOV)",
        "expense_ratio": 0.10,
        "manager": "BB Gestão de Recursos",
        "administrator": "Banco do Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Renda Variável Brasil",
        "description": "ETF de baixo custo referenciado no Índice Bovespa gerido pela BB Asset.",
    },
    "DIVO11": {
        "benchmark": "Índice Dividendos (IDIV)",
        "expense_ratio": 0.50,
        "manager": "Itaú (It Now)",
        "administrator": "Itaú Unibanco S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Dividendos Brasil",
        "description": "Rastreia empresas com os maiores dividend yields e regularidade de distribuição na bolsa brasileira.",
    },
    "BRAX11": {
        "benchmark": "Índice Brasil IBrX-100",
        "expense_ratio": 0.20,
        "manager": "BlackRock (iShares)",
        "administrator": "BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Renda Variável Brasil Amplo",
        "description": "Composto pelas 100 ações mais negociadas na B3, ponderadas pela capitalização de mercado.",
    },
    "XINA11": {
        "benchmark": "MSCI China Index",
        "expense_ratio": 0.30,
        "manager": "XP Vista Asset Management",
        "administrator": "BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Internacional Mercados Emergentes",
        "description": "Exposição direta em Reais ao mercado acionário e às maiores companhias da China continental.",
    },
    "NASD11": {
        "benchmark": "Nasdaq-100 Index",
        "expense_ratio": 0.30,
        "manager": "XP Vista Asset Management",
        "administrator": "BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Internacional Tecnologia EUA",
        "description": "Proporciona exposição às 100 maiores empresas não-financeiras listadas na bolsa Nasdaq.",
    },
    "WRLD11": {
        "benchmark": "FTSE Global All Cap Index",
        "expense_ratio": 0.30,
        "manager": "Investo Gestão de Recursos",
        "administrator": "BNP Paribas Brasil S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Mercado Global Amplo (VT)",
        "description": "Investe em mais de 9.000 ações ao redor do mundo, replicando o consagrado Vanguard Total World Stock ETF.",
    },
    "IMAB11": {
        "benchmark": "Índice IMA-B (IPCA+)",
        "expense_ratio": 0.25,
        "manager": "Itaú (It Now)",
        "administrator": "Itaú Unibanco S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Renda Fixa Inflação Pública",
        "description": "Replica a cesta de títulos públicos indexados à inflação (NTN-B / Tesouro IPCA+) de todos os prazos.",
    },
    "B5P211": {
        "benchmark": "Índice IMA-B 5 P2",
        "expense_ratio": 0.20,
        "manager": "Itaú (It Now)",
        "administrator": "Itaú Unibanco S.A.",
        "dividend_policy": "Reinvestimento Automático de Proventos",
        "dividend_yield": None,
        "category": "Renda Fixa Inflação Curto Prazo",
        "description": "Títulos do Tesouro IPCA+ com prazo de até 5 anos, garantindo menor volatilidade e alíquota de IR de 15%.",
    },
    "VOO": {
        "benchmark": "S&P 500 Index",
        "expense_ratio": 0.03,
        "manager": "Vanguard",
        "administrator": "The Vanguard Group, Inc.",
        "dividend_policy": "Distribuição Trimestral de Dividendos",
        "dividend_yield": 1.45,
        "category": "Renda Variável EUA Large Cap",
        "description": "Um dos maiores ETFs do mundo, acompanhando com taxa ultrabaixa o índice S&P 500.",
    },
    "SPY": {
        "benchmark": "S&P 500 Index",
        "expense_ratio": 0.09,
        "manager": "State Street Global Advisors (SPDR)",
        "administrator": "State Street Bank and Trust",
        "dividend_policy": "Distribuição Trimestral de Dividendos",
        "dividend_yield": 1.42,
        "category": "Renda Variável EUA Large Cap",
        "description": "O ETF mais antigo e líquido do mundo, referência absoluta de liquidez para o índice S&P 500.",
    },
    "QQQ": {
        "benchmark": "Nasdaq-100 Index",
        "expense_ratio": 0.20,
        "manager": "Invesco",
        "administrator": "The Bank of New York Mellon",
        "dividend_policy": "Distribuição Trimestral de Dividendos",
        "dividend_yield": 0.60,
        "category": "Renda Variável EUA Tecnologia",
        "description": "Acompanha os gigantes globais de tecnologia e inovação listados na Nasdaq.",
    },
    "SCHD": {
        "benchmark": "Dow Jones U.S. Dividend 100",
        "expense_ratio": 0.06,
        "manager": "Charles Schwab Investment Management",
        "administrator": "Charles Schwab",
        "dividend_policy": "Distribuição Trimestral de Dividendos",
        "dividend_yield": 3.45,
        "category": "Renda Variável EUA Dividendos de Qualidade",
        "description": "Focado em ações americanas com histórico de 10+ anos de pagamento e crescimento consistente de proventos.",
    },
    "VTI": {
        "benchmark": "CRSP US Total Market Index",
        "expense_ratio": 0.03,
        "manager": "Vanguard",
        "administrator": "The Vanguard Group, Inc.",
        "dividend_policy": "Distribuição Trimestral de Dividendos",
        "dividend_yield": 1.40,
        "category": "Renda Variável Total Market EUA",
        "description": "Proporciona exposição a 100% do mercado de ações dos Estados Unidos, incluindo small, mid e large caps.",
    },
    "VNQ": {
        "benchmark": "MSCI US REIT Index",
        "expense_ratio": 0.12,
        "manager": "Vanguard",
        "administrator": "The Vanguard Group, Inc.",
        "dividend_policy": "Distribuição Trimestral de Dividendos",
        "dividend_yield": 3.90,
        "category": "Real Estate Global / REITs EUA",
        "description": "Investe em Fundos de Investimento Imobiliário dos EUA (Real Estate Investment Trusts - REITs).",
    },
}

BDR_MAP: dict[str, tuple[str, str, str]] = {
    "AAPL34": ("AAPL", "Apple Inc.", "1:20 (0.05 ação)"),
    "MSFT34": ("MSFT", "Microsoft Corporation", "1:30 (0.033 ação)"),
    "NVDA34": ("NVDA", "NVIDIA Corporation", "1:10 (0.10 ação)"),
    "AMZO34": ("AMZN", "Amazon.com, Inc.", "1:20 (0.05 ação)"),
    "GOGL34": ("GOOGL", "Alphabet Inc. (Google)", "1:20 (0.05 ação)"),
    "TSLA34": ("TSLA", "Tesla, Inc.", "1:20 (0.05 ação)"),
    "META34": ("META", "Meta Platforms, Inc.", "1:20 (0.05 ação)"),
    "DISB34": ("DIS", "The Walt Disney Company", "1:10 (0.10 ação)"),
    "NFLX34": ("NFLX", "Netflix, Inc.", "1:30 (0.033 ação)"),
    "COCA34": ("KO", "The Coca-Cola Company", "1:5 (0.20 ação)"),
    "MCDC34": ("MCD", "McDonald's Corporation", "1:10 (0.10 ação)"),
    "BERK34": ("BRK.B", "Berkshire Hathaway Inc.", "1:10 (0.10 ação)"),
    "JNJB34": ("JNJ", "Johnson & Johnson", "1:10 (0.10 ação)"),
    "PGCO34": ("PG", "Procter & Gamble Company", "1:10 (0.10 ação)"),
}


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
    # ETFs e Fundos de Índice
    # -------------------------------------------------------------------------

    async def get_etf_indicators(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
        *,
        force_refresh: bool = False,
    ) -> Optional[dict[str, Any]]:
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            return None

        cache_key = f"etf_indicators:{clean_ticker}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached

        # 1. Verifica dados curados
        curated = ETF_CURATED_DATA.get(clean_ticker)
        if curated:
            data = {
                "symbol": clean_ticker,
                "benchmark": curated.get("benchmark"),
                "expense_ratio": curated.get("expense_ratio"),
                "manager": curated.get("manager"),
                "administrator": curated.get("administrator"),
                "dividend_policy": curated.get("dividend_policy"),
                "dividend_yield": curated.get("dividend_yield"),
                "net_assets": None,
                "category": curated.get("category"),
                "description": curated.get("description"),
            }
            try:
                quotes = await self._client.fetch_quotes([clean_ticker])
                q = quotes.get(clean_ticker)
                if q and q.market_cap:
                    data["net_assets"] = q.market_cap
            except Exception:
                pass
            await self._set_cached(cache_key, data, TTL_FUNDAMENTALS_SECONDS)
            return data

        # 2. Inferência dinâmica para outros ETFs
        manager = "Gestão de Recursos Especializada"
        benchmark = "Índice de Mercado"
        category = "Fundo de Índice (ETF)"
        dividend_policy = "Reinvestimento Automático de Proventos"
        expense_ratio = 0.30
        desc = f"Fundo de Índice (ETF) {clean_ticker} negociado em bolsa com carteira teórica de ativos."

        try:
            quotes = await self._client.fetch_quotes([clean_ticker])
            q = quotes.get(clean_ticker)
            if q:
                name = (q.long_name or q.short_name or "").upper()
                if "ISHARES" in name or "BLACKROCK" in name:
                    manager = "BlackRock (iShares)"
                elif "IT NOW" in name or "ITAÚ" in name or "ITAU" in name:
                    manager = "Itaú (It Now)"
                elif "VANGUARD" in name:
                    manager = "Vanguard"
                elif "SPDR" in name or "STATE STREET" in name:
                    manager = "State Street (SPDR)"
                elif "XP" in name or "VISTA" in name:
                    manager = "XP Asset Management"
                elif "INVESTO" in name:
                    manager = "Investo"
                elif "BB" in name:
                    manager = "BB Asset"

                if "IBOV" in name or "BOVESPA" in name:
                    benchmark = "Índice Bovespa (IBOV)"
                    category = "Renda Variável Brasil"
                elif "S&P" in name:
                    benchmark = "S&P 500"
                    category = "Internacional EUA"
                elif "SMALL" in name or "SMLL" in name:
                    benchmark = "Índice Small Cap (SMLL)"
                    category = "Small Caps Brasil"
                elif "NASDAQ" in name:
                    benchmark = "Nasdaq-100"
                    category = "Internacional Tecnologia"
                elif "IMA-B" in name or "INFLA" in name:
                    benchmark = "IMA-B (Títulos Públicos IPCA+)"
                    category = "Renda Fixa Inflação"
                elif "CRYPTO" in name or "CRIPTO" in name or "BITCOIN" in name:
                    benchmark = "Criptoativos"
                    category = "Criptoativos"

                if "DIV" in clean_ticker and not clean_ticker.startswith("NSDV"):
                    dividend_policy = "Distribuição Periódica de Proventos"
        except Exception:
            pass

        data = {
            "symbol": clean_ticker,
            "benchmark": benchmark,
            "expense_ratio": expense_ratio,
            "manager": manager,
            "administrator": "Instituição Custodiante Autorizada B3",
            "dividend_policy": dividend_policy,
            "dividend_yield": None,
            "net_assets": None,
            "category": category,
            "description": desc,
        }
        await self._set_cached(cache_key, data, TTL_FUNDAMENTALS_SECONDS)
        return data

    # -------------------------------------------------------------------------
    # BDRs (Brazilian Depositary Receipts)
    # -------------------------------------------------------------------------

    async def get_bdr_indicators(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
        *,
        force_refresh: bool = False,
    ) -> Optional[dict[str, Any]]:
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            return None

        cache_key = f"bdr_indicators:{clean_ticker}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached

        underlying = clean_ticker[:4]
        company = f"{clean_ticker[:4]} Global"
        ratio = "1 BDR = 1 cota de recibo"

        if clean_ticker in BDR_MAP:
            underlying, company, ratio = BDR_MAP[clean_ticker]

        data = {
            "symbol": clean_ticker,
            "underlying_ticker": underlying,
            "underlying_company": company,
            "origin_market": "Bolsas Americanas (NYSE / NASDAQ)",
            "origin_currency": "USD",
            "depositary_bank": "Banco B3 S.A.",
            "ratio": ratio,
            "dividend_yield": None,
            "pe": None,
            "market_cap_usd": None,
            "description": f"Brazilian Depositary Receipt representativo de ações ordinárias de {company}.",
        }

        try:
            intl = await self.get_international_fundamentals(underlying, force_refresh=force_refresh)
            if intl:
                stock_fund = intl.get("stock_fundamentals") or {}
                profile = intl.get("international_profile") or {}
                data["pe"] = stock_fund.get("pe")
                data["dividend_yield"] = stock_fund.get("dividend_yield")
                data["market_cap_usd"] = profile.get("market_cap_usd")
                if profile.get("country"):
                    data["origin_market"] = f"{profile.get('exchange', 'Bolsa Global')} ({profile.get('country')})"
        except Exception:
            pass

        await self._set_cached(cache_key, data, TTL_FUNDAMENTALS_SECONDS)
        return data

    # -------------------------------------------------------------------------
    # Histórico de Dividendos e Proventos Canônicos
    # -------------------------------------------------------------------------

    async def get_dividend_history(
        self,
        ticker: str,
        *,
        db: Optional[AsyncSession] = None,
        force_refresh: bool = False,
    ) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
        """Obtém histórico canônico de dividendos/proventos do ativo e métricas de distribuição."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            return [], None

        cache_key = f"dividend_history:{clean_ticker}"
        if not force_refresh:
            cached = await self._get_cached(cache_key)
            if cached is not None and isinstance(cached, dict):
                return cached.get("history", []), cached.get("metrics")

        history: list[dict[str, Any]] = []

        # 1. Tenta carregar do banco de dados canônico (AssetDividend)
        if db is not None:
            try:
                stmt = (
                    select(AssetDividend)
                    .join(Asset, Asset.id == AssetDividend.asset_id)
                    .where(
                        or_(
                            Asset.ticker == clean_ticker,
                            Asset.ticker == f"{clean_ticker}.SA",
                            Asset.ticker == clean_ticker.replace(".SA", ""),
                        )
                    )
                    .order_by(
                        AssetDividend.payment_date.desc().nullslast(),
                        AssetDividend.record_date.desc().nullslast(),
                        AssetDividend.ex_date.desc(),
                    )
                    .limit(60)
                )
                res = await db.execute(stmt)
                db_dividends = res.scalars().all()
                for div in db_dividends:
                    raw_type = (div.dividend_type.value if hasattr(div.dividend_type, "value") else str(div.dividend_type)).upper()
                    if "JCP" in raw_type or "JUROS" in raw_type:
                        norm_type = "JCP"
                    elif "REND" in raw_type:
                        norm_type = "RENDIMENTO"
                    elif "AMORT" in raw_type:
                        norm_type = "AMORTIZACAO"
                    else:
                        norm_type = "DIVIDENDO"

                    rec_date = div.record_date or div.ex_date
                    history.append({
                        "payment_date": div.payment_date.isoformat() if div.payment_date else None,
                        "record_date": rec_date.isoformat() if rec_date else None,
                        "ex_date": div.ex_date.isoformat() if div.ex_date else None,
                        "type": norm_type,
                        "value": float(div.value_per_unit),
                        "gross_value": float(div.gross_value_per_unit) if div.gross_value_per_unit is not None else None,
                    })
            except Exception as exc:
                logger.debug("Falha ao consultar AssetDividend no DB para %s: %s", sanitize_log_value(clean_ticker), sanitize_log_value(exc))

        # 2. Se DB não tiver proventos suficientes, complementa com provedor BRAPI
        if len(history) < 3:
            try:
                cash_divs, _ = await self._client.fetch_dividends_and_events(clean_ticker)
                seen_dates = {
                    (h.get("payment_date"), h.get("record_date"), h.get("type"))
                    for h in history
                }
                for cd in cash_divs:
                    raw_type = (cd.label or "DIVIDENDO").upper()
                    if "JCP" in raw_type or "JUROS" in raw_type:
                        norm_type = "JCP"
                    elif "REND" in raw_type:
                        norm_type = "RENDIMENTO"
                    elif "AMORT" in raw_type:
                        norm_type = "AMORTIZACAO"
                    else:
                        norm_type = "DIVIDENDO"

                    pay_dt = cd.payment_date.isoformat() if cd.payment_date else None
                    rec_dt = cd.last_date_prior.isoformat() if cd.last_date_prior else None
                    sig = (pay_dt, rec_dt, norm_type)
                    if sig not in seen_dates:
                        seen_dates.add(sig)
                        history.append({
                            "payment_date": pay_dt,
                            "record_date": rec_dt,
                            "ex_date": rec_dt,
                            "type": norm_type,
                            "value": float(cd.rate),
                            "gross_value": float(cd.rate),
                        })
            except Exception:
                pass

        history.sort(
            key=lambda x: (x.get("payment_date") or x.get("record_date") or "1900-01-01"),
            reverse=True,
        )

        # 3. Calcula métricas consolidadas dos últimos 12 meses
        metrics: Optional[dict[str, Any]] = None
        if history:
            now_date = datetime.now(timezone.utc).date()
            cutoff_date = (now_date - timedelta(days=365)).isoformat()

            recent_payments = [
                h for h in history
                if (h.get("payment_date") and h["payment_date"] >= cutoff_date)
                or (h.get("record_date") and h["record_date"] >= cutoff_date)
            ]

            eval_list = recent_payments if recent_payments else history[:12]
            total_12m = sum(float(h.get("value") or 0.0) for h in eval_list)
            payments_count_12m = len(eval_list)
            last_date = history[0].get("payment_date") or history[0].get("record_date")

            frequency = "Eventual"
            if payments_count_12m >= 10:
                frequency = "Mensal"
            elif payments_count_12m in (3, 4, 5):
                frequency = "Trimestral"
            elif payments_count_12m in (1, 2):
                frequency = "Semestral"

            metrics = {
                "total_paid_12m": round(total_12m, 4),
                "payments_count_12m": payments_count_12m,
                "last_payment_date": last_date,
                "frequency": frequency,
                "dy_12m": None,
            }

        await self._set_cached(cache_key, {"history": history, "metrics": metrics}, TTL_DIVIDENDS_SECONDS)
        return history, metrics

    # -------------------------------------------------------------------------
    # Enriquecimento Unificado por Ativo
    # -------------------------------------------------------------------------

    async def get_asset_enrichment(
        self,
        ticker: str,
        asset_type: Optional[str] = None,
        *,
        db: Optional[AsyncSession] = None,
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
            "asset_class": tipo or "OUTRO",
            "coverage_status": status,
            "capabilities": capabilities,
            "fii_indicators": None,
            "stock_fundamentals": None,
            "etf_indicators": None,
            "bdr_indicators": None,
            "crypto_indicators": None,
            "treasury_indicators": None,
            "international_profile": None,
            "dividend_history": [],
            "dividend_metrics": None,
        }

        # 1. Criptoativos
        known_cryptos = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "LTC", "BNB"}
        is_crypto = (
            tipo in ("CRIPTO", "CRYPTO")
            or clean_ticker in known_cryptos
            or clean_ticker.endswith(("-USD", "-BRL", "USDT"))
        )
        if is_crypto:
            result["asset_class"] = "CRIPTO"
            result["crypto_indicators"] = await self.get_crypto_indicators(clean_ticker, force_refresh=force_refresh)
            return result

        # 2. Tesouro Direto / Renda Fixa Pública
        is_treasury = (
            tipo in ("TESOURO_DIRETO", "RENDA_FIXA")
            or clean_ticker.lower().startswith("tesouro-")
            or "tesouro" in clean_ticker.lower()
        )
        if is_treasury:
            result["asset_class"] = "TESOURO_DIRETO"
            result["treasury_indicators"] = await self.get_treasury_indicators(clean_ticker, force_refresh=force_refresh)
            return result

        # Busca histórico de dividendos para classes de renda variável
        div_history, div_metrics = await self.get_dividend_history(clean_ticker, db=db, force_refresh=force_refresh)
        result["dividend_history"] = div_history
        result["dividend_metrics"] = div_metrics

        # 3. ETFs (Nacionais e Internacionais)
        is_etf = (
            tipo in ("ETF_NACIONAL", "ETF_INTERNACIONAL", "ETF_INT", "ETF")
            or clean_ticker in ETF_CURATED_DATA
            or (clean_ticker.endswith("11") and clean_ticker.startswith(("BOVA", "SMAL", "IVVB", "SPXI", "NDIV", "NSDV", "HASH", "BBOV", "DIVO", "BRAX", "XINA", "NASD", "WRLD", "IMAB", "B5P2")))
        )
        if is_etf:
            result["asset_class"] = "ETF"
            result["etf_indicators"] = await self.get_etf_indicators(clean_ticker, asset_type=tipo, force_refresh=force_refresh)
            if result["etf_indicators"] and div_metrics and div_metrics.get("dy_12m") is not None:
                result["etf_indicators"]["dividend_yield"] = div_metrics["dy_12m"]
            return result

        # 4. BDRs (Brazilian Depositary Receipts)
        is_bdr = (
            tipo == "BDR"
            or clean_ticker in BDR_MAP
            or clean_ticker.endswith(("34", "35"))
        )
        if is_bdr:
            result["asset_class"] = "BDR"
            result["bdr_indicators"] = await self.get_bdr_indicators(clean_ticker, asset_type=tipo, force_refresh=force_refresh)
            return result

        # 5. Fundos Imobiliários (FII)
        is_fii = (
            tipo == "FII"
            or (not tipo and clean_ticker.endswith("11"))
        )
        if is_fii:
            result["asset_class"] = "FII"
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

        # 6. Ativos Internacionais (Stocks)
        is_intl = (
            tipo == "STOCK"
            or (not tipo and bool(re.match(r"^[A-Z]{1,5}$", clean_ticker)) and not bool(re.search(r"\d", clean_ticker)))
        )
        if is_intl:
            result["asset_class"] = "STOCK"
            intl_data = await self.get_international_fundamentals(clean_ticker, force_refresh=force_refresh)
            if intl_data:
                result["stock_fundamentals"] = intl_data.get("stock_fundamentals")
                result["international_profile"] = intl_data.get("international_profile")
                return result

        # 7. Ações Nacionais (Default / Ações B3)
        result["asset_class"] = "ACAO"
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
