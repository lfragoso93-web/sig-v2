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
    if not tickers:
        return {}
    results: dict[str, float] = {}
    chunks  = [tickers[i:i+50] for i in range(0, len(tickers), 50)]
    headers = _auth_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        for chunk in chunks:
            joined = ",".join(chunk)
            url    = f"{BRAPI_BASE}/quote/{joined}"
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
    result = await fetch_quotes([ticker])
    return result.get(ticker)


async def fetch_asset_info(ticker: str) -> Optional[dict]:
    headers = _auth_headers()
    url = f"{BRAPI_BASE}/quote/{ticker}?modules=summaryProfile,defaultKeyStatistics"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data    = resp.json()
            results = data.get("results", [])
            return results[0] if results else None
    except Exception as e:
        logger.warning(f"BRAPI asset info error for {ticker}: {e}")
        return None


async def fetch_historical_price(ticker: str, date_str: str) -> Optional[float]:
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


async def fetch_treasury_price_by_date(slug: str, date_str: str) -> Optional[float]:
    """
    Busca o PU (preco unitario) de um titulo do Tesouro Direto em uma data especifica.
    Endpoint BRAPI: GET /api/v2/treasury/{slug}/historical?from=YYYY-MM-DD&to=YYYY-MM-DD
    O slug deve ser o identificador do titulo (ex: tesouro-ipca-15082029).
    Quando o slug e texto livre (fallback estatico), retorna None.
    Requer plano Pro na BRAPI.
    """
    from datetime import date, timedelta
    headers = _auth_headers()
    try:
        ref_date  = date.fromisoformat(date_str)
        date_from = (ref_date - timedelta(days=5)).isoformat()
        date_to   = ref_date.isoformat()
        url = (
            f"{BRAPI_BASE}/v2/treasury/{slug}/historical"
            f"?from={date_from}&to={date_to}"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data  = resp.json()
            # Resposta esperada: { "historical": [{"date": "...", "buyPrice": ..., ...}] }
            hist  = data.get("historical") or data.get("prices") or []
            if not hist:
                return None
            last  = hist[-1]
            price = last.get("buyPrice") or last.get("price") or last.get("basePrice")
            return float(price) if price else None
    except Exception as e:
        logger.warning(f"BRAPI treasury historical error for {slug} on {date_str}: {e}")
        return None


async def fetch_ticker_suggestions(q: str, limit: int = 10, asset_type: Optional[str] = None) -> list[dict]:
    """
    Busca sugestoes de tickers da B3 via BRAPI /api/quote/list.
    asset_type: 'stock' | 'fund' | 'etf' | 'bdr' | None (todos)
    """
    headers = _auth_headers()
    try:
        params: dict = {"search": q, "limit": limit}
        if asset_type:
            params["type"] = asset_type
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BRAPI_BASE}/quote/list", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("stocks") or []
    except Exception as e:
        logger.warning(f"BRAPI ticker suggestions error for q={q!r} type={asset_type!r}: {e}")
        return []


async def fetch_treasury_list() -> list[dict]:
    headers = _auth_headers()
    url = f"{BRAPI_BASE}/v2/treasury/list"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data  = resp.json()
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
