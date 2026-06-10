import httpx
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_BASE = "https://brapi.dev/api"


def _auth_headers() -> dict:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


async def fetch_quotes(tickers: list[str]) -> dict[str, float]:
    """
    Busca cotacoes de uma lista de tickers nacionais via BRAPI.
    Retorna dict {ticker: preco_atual}.
    """
    if not tickers:
        return {}

    results: dict[str, float] = {}
    chunks = [tickers[i:i+50] for i in range(0, len(tickers), 50)]
    headers = _auth_headers()

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
    Retorna informacoes completas de um ativo nacional (cotacao atual + metadados).
    """
    headers = _auth_headers()
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


async def fetch_historical_price(ticker: str, date_str: str) -> Optional[float]:
    """
    Busca o preco de fechamento de um ticker em uma data especifica (YYYY-MM-DD).
    Usa range=custom com janela de 5 dias anteriores para cobrir feriados/fins de semana.
    """
    from datetime import date, timedelta
    headers = _auth_headers()

    try:
        ref_date  = date.fromisoformat(date_str)
        date_from = (ref_date - timedelta(days=5)).isoformat()
        date_to   = ref_date.isoformat()

        url = (
            f"{BRAPI_BASE}/quote/{ticker}"
            f"?range=custom&interval=1d"
            f"&from={date_from}&to={date_to}"
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data    = resp.json()
            results = data.get("results", [])
            if not results:
                return None
            history = results[0].get("historicalDataPrice", [])
            if not history:
                return results[0].get("regularMarketPrice")
            last  = history[-1]
            close = last.get("close") or last.get("adjclose")
            return float(close) if close else None
    except Exception as e:
        logger.warning(f"BRAPI historical price error for {ticker} on {date_str}: {e}")
        return None


async def fetch_treasury_list() -> list[dict]:
    """
    Busca a lista de titulos do Tesouro Direto via BRAPI.
    Endpoint correto: GET /api/v2/treasury/list
    Requer plano Pro; sem token retorna apenas 3 titulos sandbox.
    """
    headers = _auth_headers()
    url = f"{BRAPI_BASE}/v2/treasury/list"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # A API retorna { "treasuries": [...] }
            items = (
                data.get("treasuries")
                or data.get("data")
                or data.get("results")
                or (data if isinstance(data, list) else [])
            )
            return items if isinstance(items, list) else []
    except Exception as e:
        logger.warning(f"BRAPI treasury list error: {e}")
        return []
