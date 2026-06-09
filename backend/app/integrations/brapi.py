import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_BASE = "https://brapi.dev/api"


async def fetch_quotes(tickers: list[str]) -> dict[str, float]:
    """
    Busca cotacoes de uma lista de tickers nacionais via BRAPI.
    Retorna dict {ticker: preco_atual}.
    Tickers invalidos/nao encontrados sao ignorados silenciosamente.
    """
    if not tickers:
        return {}

    # BRAPI aceita ate 50 tickers por chamada
    results: dict[str, float] = {}
    chunks = [tickers[i:i+50] for i in range(0, len(tickers), 50)]

    headers = {}
    if settings.BRAPI_TOKEN:
        headers["Authorization"] = f"Bearer {settings.BRAPI_TOKEN}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        for chunk in chunks:
            joined = ",".join(chunk)
            url = f"{BRAPI_BASE}/quote/{joined}"
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", []):
                    symbol = item.get("symbol", "")
                    price  = item.get("regularMarketPrice")
                    if symbol and price is not None:
                        results[symbol] = float(price)
            except Exception as e:
                logger.warning(f"BRAPI quote error for chunk {chunk}: {e}")

    return results


async def fetch_quote_single(ticker: str) -> Optional[float]:
    """Busca cotacao de um unico ticker."""
    result = await fetch_quotes([ticker])
    return result.get(ticker)


async def fetch_asset_info(ticker: str) -> Optional[dict]:
    """
    Retorna informacoes completas de um ativo nacional:
    nome, setor, tipo, historico de precos, etc.
    """
    headers = {}
    if settings.BRAPI_TOKEN:
        headers["Authorization"] = f"Bearer {settings.BRAPI_TOKEN}"

    url = f"{BRAPI_BASE}/quote/{ticker}?modules=summaryProfile,defaultKeyStatistics"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            return results[0] if results else None
    except Exception as e:
        logger.warning(f"BRAPI asset info error for {ticker}: {e}")
        return None
