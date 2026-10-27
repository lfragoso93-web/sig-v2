"""Registry estático de provedores de mercado e proteção de segredos.

Governança:
- Provedores pertencem a workers/sincronizadores controlados.
- Nenhuma credencial completa retorna pela API (apenas mascarada).
- Fallback seguro para configurações estáticas (.env).
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import StrEnum
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


class ProviderId(StrEnum):
    BRAPI = "brapi"
    B3_COTAHIST = "b3_cotahist"
    YAHOO_FINANCE = "yahoo_finance"
    TESOURO_TRANSPARENTE = "tesouro_transparente"
    BACEN_SGS = "bacen_sgs"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    TIINGO = "tiingo"


class ProviderCapability(StrEnum):
    QUOTES_INTRADAY = "quotes_intraday"
    QUOTES_HISTORICAL = "quotes_historical"
    DIVIDENDS = "dividends"
    CORPORATE_EVENTS = "corporate_events"
    FUNDAMENTALS = "fundamentals"
    BENCHMARK_RATES = "benchmark_rates"
    TREASURY_BONDS = "treasury_bonds"
    FX_RATES = "fx_rates"


@dataclass(frozen=True)
class ProviderDefinition:
    id: ProviderId
    display_name: str
    description: str
    capabilities: tuple[ProviderCapability, ...]
    default_base_url: str | None
    requires_auth: bool
    env_key_var: str | None
    is_official_authority: bool
    default_timeout_seconds: int = 30
    default_rate_limit_per_minute: int | None = None
    default_priority: int = 10
    doc_url: str | None = None
    probe_endpoint_path: str | None = None


PROVIDER_REGISTRY: dict[ProviderId, ProviderDefinition] = {
    ProviderId.B3_COTAHIST: ProviderDefinition(
        id=ProviderId.B3_COTAHIST,
        display_name="B3 / COTAHIST Oficial",
        description=(
            "Autoridade primária oficial para cotações históricas diárias "
            "e catálogo de ativos B3."
        ),
        capabilities=(
            ProviderCapability.QUOTES_HISTORICAL,
            ProviderCapability.CORPORATE_EVENTS,
        ),
        default_base_url=None,
        requires_auth=False,
        env_key_var=None,
        is_official_authority=True,
        default_timeout_seconds=60,
        default_priority=1,
        doc_url="https://www.b3.com.br",
    ),
    ProviderId.BRAPI: ProviderDefinition(
        id=ProviderId.BRAPI,
        display_name="BRAPI",
        description=(
            "Cotações em tempo real/intradiárias, proventos, dividendos e "
            "indicadores fundamentalistas."
        ),
        capabilities=(
            ProviderCapability.QUOTES_INTRADAY,
            ProviderCapability.DIVIDENDS,
            ProviderCapability.FUNDAMENTALS,
        ),
        default_base_url="https://brapi.dev",
        requires_auth=True,
        env_key_var="BRAPI_TOKEN",
        is_official_authority=False,
        default_timeout_seconds=15,
        default_rate_limit_per_minute=300,
        default_priority=5,
        doc_url="https://brapi.dev/docs",
        probe_endpoint_path="/api/available",
    ),
    ProviderId.YAHOO_FINANCE: ProviderDefinition(
        id=ProviderId.YAHOO_FINANCE,
        display_name="Yahoo Finance",
        description=(
            "Fallback explícito para ativos sem cobertura B3, benchmarks "
            "internacionais e criptoativos."
        ),
        capabilities=(
            ProviderCapability.QUOTES_HISTORICAL,
            ProviderCapability.QUOTES_INTRADAY,
        ),
        default_base_url="https://query1.finance.yahoo.com",
        requires_auth=False,
        env_key_var=None,
        is_official_authority=False,
        default_timeout_seconds=20,
        default_priority=20,
        doc_url="https://finance.yahoo.com",
        probe_endpoint_path="/v8/finance/chart/%5EBVSP?range=1d&interval=1d",
    ),
    ProviderId.TESOURO_TRANSPARENTE: ProviderDefinition(
        id=ProviderId.TESOURO_TRANSPARENTE,
        display_name="Tesouro Transparente (STN)",
        description=(
            "Autoridade oficial da STN para preços, taxas e catálogo de "
            "títulos públicos."
        ),
        capabilities=(
            ProviderCapability.TREASURY_BONDS,
        ),
        default_base_url="https://www.tesourotransparente.gov.br",
        requires_auth=False,
        env_key_var=None,
        is_official_authority=True,
        default_timeout_seconds=30,
        default_priority=1,
        doc_url="https://www.tesourotransparente.gov.br/ckan",
        probe_endpoint_path=(
            "/ckan/api/3/action/package_show?id="
            "taxas-dos-titulos-ofertados-pelo-tesouro-direto"
        ),
    ),
    ProviderId.BACEN_SGS: ProviderDefinition(
        id=ProviderId.BACEN_SGS,
        display_name="BACEN / SGS",
        description=(
            "Sistema Gerenciador de Séries Temporais do Banco Central "
            "(taxas CDI, Selic e IPCA)."
        ),
        capabilities=(
            ProviderCapability.BENCHMARK_RATES,
        ),
        default_base_url="https://api.bcb.gov.br",
        requires_auth=False,
        env_key_var=None,
        is_official_authority=True,
        default_timeout_seconds=15,
        default_priority=1,
        doc_url="https://dadosabertos.bcb.gov.br",
        probe_endpoint_path=(
            "/dados/serie/bcdata.sgs.11/dados/ultimos/1?formato=json"
        ),
    ),
    ProviderId.ALPHA_VANTAGE: ProviderDefinition(
        id=ProviderId.ALPHA_VANTAGE,
        display_name="Alpha Vantage",
        description=(
            "Provedor de taxas de câmbio (FX) e moedas internacionais."
        ),
        capabilities=(
            ProviderCapability.FX_RATES,
        ),
        default_base_url="https://www.alphavantage.co",
        requires_auth=True,
        env_key_var="ALPHA_VANTAGE_API_KEY",
        is_official_authority=False,
        default_timeout_seconds=20,
        default_rate_limit_per_minute=5,
        default_priority=15,
        doc_url="https://www.alphavantage.co/documentation",
        probe_endpoint_path=(
            "/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD"
            "&to_currency=BRL"
        ),
    ),
    ProviderId.FINNHUB: ProviderDefinition(
        id=ProviderId.FINNHUB,
        display_name="Finnhub Stock API",
        description=(
            "Cotacoes intraday em tempo real, status de mercado e perfis de ativos "
            "internacionais (US Stocks, ETFs)."
        ),
        capabilities=(
            ProviderCapability.QUOTES_INTRADAY,
            ProviderCapability.QUOTES_HISTORICAL,
        ),
        default_base_url="https://finnhub.io/api/v1",
        requires_auth=True,
        env_key_var="FINNHUB_API_KEY",
        is_official_authority=False,
        default_timeout_seconds=15,
        default_rate_limit_per_minute=60,
        default_priority=5,
        doc_url="https://finnhub.io/docs/api",
        probe_endpoint_path="/quote?symbol=AAPL",
    ),
    ProviderId.TIINGO: ProviderDefinition(
        id=ProviderId.TIINGO,
        display_name="Tiingo",
        description=(
            "Precos historicos de fechamento (EOD) auditados, ajustes por splits e "
            "proventos, IEX e dados de criptoativos/forex."
        ),
        capabilities=(
            ProviderCapability.QUOTES_HISTORICAL,
            ProviderCapability.QUOTES_INTRADAY,
            ProviderCapability.DIVIDENDS,
        ),
        default_base_url="https://api.tiingo.com",
        requires_auth=True,
        env_key_var="TIINGO_API_KEY",
        is_official_authority=False,
        default_timeout_seconds=20,
        default_rate_limit_per_minute=50,
        default_priority=6,
        doc_url="https://api.tiingo.com/documentation",
        probe_endpoint_path="/tiingo/daily/aapl",
    ),
}


def _get_cipher_suite() -> Fernet:
    """Deriva chave de 32 bytes para Fernet a partir de settings.SECRET_KEY."""
    raw_key = settings.SECRET_KEY.encode("utf-8")
    derived = hashlib.sha256(raw_key).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    return Fernet(fernet_key)


def encrypt_secret(plain_text: str | None) -> str | None:
    """Criptografa segredo de forma determinística e reversível."""
    if not plain_text or not plain_text.strip():
        return None
    cipher = _get_cipher_suite()
    return cipher.encrypt(plain_text.strip().encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher_text: str | None) -> str | None:
    """Descriptografa segredo criptografado com a chave do sistema."""
    if not cipher_text or not cipher_text.strip():
        return None
    try:
        cipher = _get_cipher_suite()
        return cipher.decrypt(
            cipher_text.strip().encode("utf-8")
        ).decode("utf-8")
    except Exception:
        return None


def mask_secret(secret: str | None) -> str | None:
    """Retorna máscara segura do segredo para exibição (ex: 'br_****7f')."""
    if not secret:
        return None
    cleaned = secret.strip()
    length = len(cleaned)
    if length <= 4:
        return "****"
    if length <= 8:
        return f"{cleaned[:2]}****{cleaned[-2:]}"
    return f"{cleaned[:3]}****{cleaned[-3:]}"
