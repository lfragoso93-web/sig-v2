"""Busca cotacao USD/BRL via BRAPI."""
import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

FALLBACK_RATE = 5.40  # fallback se API falhar


async def get_usd_brl() -> float:
    """Retorna cotacao atual USD/BRL."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{settings.BRAPI_BASE_URL}/quote/USDBRL=X",
                params={"token": settings.BRAPI_TOKEN},
            )
            resp.raise_for_status()
            data = resp.json()
            rate = data["results"][0]["regularMarketPrice"]
            return float(rate)
    except Exception as e:
        logger.warning(f"Falha ao buscar USD/BRL: {e}. Usando fallback {FALLBACK_RATE}")
        return FALLBACK_RATE
