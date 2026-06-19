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

logger = logging.getLogger(__name__)

# Mapa de ticker -> dominio para Clearbit (stocks conhecidos)
# Pode ser expandido conforme necessidade
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
_BRAPI_BASE = "https://brapi.dev/api"
_TIMEOUT = 8.0


async def _fetch_brapi_logo(ticker: str) -> str | None:
    """Busca logo via BRAPI /quote. Retorna URL ou None."""
    url = f"{_BRAPI_BASE}/quote/{ticker}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results and results[0].get("logourl"):
                return results[0]["logourl"]
    except Exception as e:
        logger.debug(f"[logo_service] BRAPI logo nao encontrado para {ticker}: {e}")
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
        logger.debug(f"[logo_service] Clearbit logo nao encontrado para {ticker}: {e}")
    return None


async def fetch_logo_url(ticker: str, asset_type: AssetType | str) -> str | None:
    """
    Retorna a URL do logo para o ticker.
    Tenta BRAPI primeiro (ativos BR), depois Clearbit (stocks internacionais).
    Retorna None se nenhuma fonte retornar logo.
    """
    at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type

    # Ativos BR: BRAPI tem campo logourl
    if at in BR_TYPES or at in (AssetType.FII, AssetType.BDR, AssetType.ETF_NACIONAL):
        logo = await _fetch_brapi_logo(ticker)
        if logo:
            logger.info(f"[logo_service] logo BRAPI encontrado para {ticker}: {logo}")
            return logo

    # Stocks internacionais: tenta Clearbit
    if at in (AssetType.STOCK, AssetType.ETF_INTERNACIONAL):
        logo = await _fetch_clearbit_logo(ticker)
        if logo:
            logger.info(f"[logo_service] logo Clearbit encontrado para {ticker}: {logo}")
            return logo

    # Fallback final: tenta BRAPI mesmo para internacionais (alguns estao listados)
    logo = await _fetch_brapi_logo(ticker)
    if logo:
        return logo

    logger.warning(f"[logo_service] nenhum logo encontrado para {ticker} ({at})")
    return None
