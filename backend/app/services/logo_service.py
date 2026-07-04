"""
Servico de busca de logo de ativos.

Fontes (em ordem de prioridade):
  1. BRAPI /quote/{ticker}  -> campo 'logourl'  (ativos BR: ACAO, FII, ETF, BDR)
  2. Clearbit Logo API      -> https://logo.clearbit.com/{domain} (STOCK internacional)

Retorna a URL do logo como string, ou None em caso de falha.
Nao propaga excecoes — degradacao gracosa.
"""
import logging
import httpx

from app.models.asset import AssetType
from app.core.asset_types import BR_TYPES
from app.integrations.brapi import BRAPI_BASE, _auth_headers

logger = logging.getLogger(__name__)

# Mapa de ticker -> dominio para Clearbit (stocks conhecidos)
_CLEARBIT_DOMAIN_MAP: dict[str, str] = {
    "AAPL": "apple.com",
    "MSFT": "microsoft.com",
    "GOOGL": "google.com",
    "AMZN": "amazon.com",
    "TSLA": "tesla.com",
    "META": "meta.com",
    "NVDA": "nvidia.com",
    "NFLX": "netflix.com",
}

_CLEARBIT_BASE = "https://logo.clearbit.com"
_TIMEOUT = 8.0


async def _fetch_brapi_logo(ticker: str) -> str | None:
    """Busca logo via BRAPI /quote. Retorna URL ou None."""
    url = f"{BRAPI_BASE}/quote/{ticker}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_auth_headers())
            if resp.status_code in (401, 403):
                logger.info("[logo_service] BRAPI sem autorizacao para logo de %s", ticker)
                return None
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results and results[0].get("logourl"):
                return results[0]["logourl"]
    except Exception as e:
        logger.debug("[logo_service] BRAPI logo nao encontrado para %s: %s", ticker, e)
    return None


async def _fetch_clearbit_logo(ticker: str) -> str | None:
    """Tenta Clearbit com dominio mapeado. Retorna URL ou None."""
    domain = _CLEARBIT_DOMAIN_MAP.get(ticker.upper())
    if not domain:
        return None
    url = f"{_CLEARBIT_BASE}/{domain}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                return str(resp.url)
    except Exception as e:
        logger.debug("[logo_service] Clearbit logo nao encontrado para %s: %s", ticker, e)
    return None


async def fetch_logo_url(ticker: str, asset_type: AssetType | str) -> str | None:
    """
    Retorna a URL do logo para o ticker.
    Tenta BRAPI primeiro (ativos BR), depois Clearbit (stocks internacionais).
    Retorna None se nenhuma fonte retornar logo.
    """
    at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type

    if at in BR_TYPES or at in (AssetType.FII, AssetType.BDR, AssetType.ETF_NACIONAL):
        logo = await _fetch_brapi_logo(ticker)
        if logo:
            logger.info("[logo_service] logo BRAPI encontrado para %s: %s", ticker, logo)
            return logo

    if at in (AssetType.STOCK, AssetType.ETF_INTERNACIONAL):
        logo = await _fetch_clearbit_logo(ticker)
        if logo:
            logger.info("[logo_service] logo Clearbit encontrado para %s: %s", ticker, logo)
            return logo

    # Evita chamada duplicada para BR quando já tentamos acima.
    if at not in BR_TYPES and at not in (AssetType.FII, AssetType.BDR, AssetType.ETF_NACIONAL):
        logo = await _fetch_brapi_logo(ticker)
        if logo:
            return logo

    logger.warning("[logo_service] nenhum logo encontrado para %s (%s)", ticker, at)
    return None
