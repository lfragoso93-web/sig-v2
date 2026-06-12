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


async def fetch_logo_url(ticker: str) -> Optional[str]:
    """
    Retorna a URL do logo do ativo via BRAPI.
    A BRAPI devolve o campo `logourl` no objeto de resultado do quote.
    Silencioso em caso de erro — nunca deve quebrar o fluxo de criacao de ativo.
    """
    try:
        info = await fetch_asset_info(ticker)
        if not info:
            return None
        # BRAPI retorna 'logourl' (sem hifen) no resultado do quote
        logo = info.get("logourl") or info.get("logo_url") or info.get("logo")
        return str(logo) if logo else None
    except Exception as e:
        logger.warning(f"BRAPI fetch_logo_url error for {ticker}: {e}")
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
            hist  = data.get("historical") or data.get("prices") or []
            if not hist:
                return None
            last  = hist[-1]
            price = last.get("buyPrice") or last.get("price") or last.get("basePrice")
            return float(price) if price else None
    except Exception as e:
        logger.warning(f"BRAPI treasury historical error for {slug} on {date_str}: {e}")
        return None


async def fetch_ticker_suggestions(
    q: str,
    limit: int = 10,
    asset_type: Optional[str] = None,
) -> list[dict]:
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


async def fetch_crypto_suggestions(q: str, limit: int = 10) -> list[dict]:
    """
    Busca sugestoes de criptomoedas via BRAPI GET /api/v2/crypto/available?search={q}.
    Retorna lista de dicts com coin, name.
    """
    headers = _auth_headers()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/crypto/available",
                headers=headers,
                params={"search": q, "limit": limit},
            )
            resp.raise_for_status()
            data  = resp.json()
            items = data.get("coins") or data.get("available") or (data if isinstance(data, list) else [])
            return items[:limit]
    except Exception as e:
        logger.warning(f"BRAPI crypto suggestions error for q={q!r}: {e}")
        return []


def _yf_search_sync(q: str, limit: int = 10, asset_type: Optional[str] = None) -> list[dict]:
    """
    Busca tickers internacionais via yfinance Search / Lookup.
    asset_type: 'stock' | 'etf' | None (todos via Search)
    Roda em thread (bloqueante).
    """
    try:
        import yfinance as yf
        results = []

        if asset_type == "stock":
            items = yf.Lookup(q).get_stock(count=limit)
        elif asset_type == "etf":
            items = yf.Lookup(q).get_etf(count=limit)
        else:
            search = yf.Search(q, max_results=limit)
            items  = search.quotes or []

        for item in items:
            if hasattr(item, "to_dict"):
                row = item
                ticker = str(getattr(row, "symbol", "") or "")
                name   = str(getattr(row, "longname", "") or getattr(row, "shortname", "") or "")
                kind   = str(getattr(row, "quoteType", "") or asset_type or "")
            elif isinstance(item, dict):
                ticker = item.get("symbol") or item.get("ticker") or ""
                name   = item.get("longname") or item.get("shortname") or ""
                kind   = item.get("quoteType") or asset_type or ""
            else:
                continue
            if ticker:
                results.append({"ticker": ticker.upper(), "name": name, "type": kind.lower()})
        return results[:limit]
    except Exception as e:
        logger.warning(f"yfinance search error for q={q!r} type={asset_type!r}: {e}")
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
