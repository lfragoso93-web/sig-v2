import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_BASE = "https://brapi.dev/api"
HEADERS = {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}


async def get_quote(ticker: str, dividends: bool = False) -> Optional[dict]:
    """
    GET /api/quote/{ticker}
    Retorna cotacao atual + opcionalmente dividendos e eventos corporativos.
    Com plano PRO: inclui DIVIDENDS, JCP, SPLIT, BONUS.
    """
    params = {"fundamental": "false"}
    if dividends:
        params["dividends"] = "true"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/quote/{ticker}",
                params=params,
                headers=HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return results[0] if results else None
    except Exception as e:
        logger.error(f"[BRAPI] Erro ao buscar cotacao {ticker}: {e}")
        return None


async def get_quotes_bulk(tickers: list[str]) -> list[dict]:
    """
    GET /api/quote/{ticker1,ticker2,...}
    Busca multiplos tickers em uma unica chamada (limite PRO: 50 por request).
    """
    if not tickers:
        return []
    results = []
    chunk_size = 50
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        joined = ",".join(chunk)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{BRAPI_BASE}/quote/{joined}",
                    params={"fundamental": "false"},
                    headers=HEADERS,
                )
                resp.raise_for_status()
                data = resp.json()
                results.extend(data.get("results", []))
        except Exception as e:
            logger.error(f"[BRAPI] Erro ao buscar bulk {joined}: {e}")
    return results


async def get_dividends_and_events(ticker: str) -> list[dict]:
    """
    Retorna lista de eventos corporativos do ativo:
    dividendos, JCP, splits, grupamentos e bonificacoes.
    Requer plano PRO.
    """
    data = await get_quote(ticker, dividends=True)
    if not data:
        return []
    return data.get("dividendsData", {}).get("cashDividends", []) or []


async def search_ticker(query: str) -> list[dict]:
    """
    GET /api/available - busca tickers disponiveis na BRAPI.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/available",
                params={"search": query},
                headers=HEADERS,
            )
            resp.raise_for_status()
            return resp.json().get("stocks", [])
    except Exception as e:
        logger.error(f"[BRAPI] Erro ao buscar ticker {query}: {e}")
        return []
