import httpx
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_BASE = "https://brapi.dev/api"


def _auth_headers() -> dict:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


# ── Cotações atuais ───────────────────────────────────────────────────────────────────

async def fetch_quotes(tickers: list[str]) -> dict[str, float]:
    """
    Retorna apenas {ticker: price}.
    Mantido para compatibilidade com quotes_service e demais usos.
    """
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


async def fetch_quotes_with_meta(tickers: list[str]) -> dict[str, dict]:
    """
    Retorna {ticker: {price: float, logo_url: str | None}}.
    Usado por calc_positions para enriquecer posições com logo e cotação.
    """
    if not tickers:
        return {}
    results: dict[str, dict] = {}
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
                    logo   = (
                        item.get("logourl")
                        or item.get("logo_url")
                        or item.get("logo")
                    )
                    if symbol:
                        results[symbol] = {
                            "price":    float(price) if price is not None else None,
                            "logo_url": str(logo) if logo else None,
                        }
            except Exception as e:
                logger.warning(f"BRAPI quote meta error for chunk {chunk}: {e}")
    return results


async def fetch_quote_single(ticker: str) -> Optional[float]:
    result = await fetch_quotes([ticker])
    return result.get(ticker)


# ── Histórico diário de preços (BRAPI Pro) ───────────────────────────────────────

async def fetch_price_history(
    ticker: str,
    date_from: str,
    date_to: str,
) -> list[tuple[datetime, float]]:
    """
    Busca histórico diário de fechamento via BRAPI Pro.
    Suporta: ações BR, FIIs, ETFs nacionais, cripto (via /quote/{ticker}).

    Retorna lista de (datetime_utc, close_price) ordenada por data asc.
    Retorna [] se BRAPI falhar (sem lançar exceção — fallback para yfinance).

    Uso:
        rows = await fetch_price_history("PETR4", "2025-01-01", "2026-01-01")
        rows = await fetch_price_history("BTC",   "2025-06-01", "2025-06-15")
    """
    headers = _auth_headers()
    url = (
        f"{BRAPI_BASE}/quote/{ticker}"
        f"?range=custom&interval=1d"
        f"&from={date_from}&to={date_to}"
    )
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data    = resp.json()
            results = data.get("results", [])
            if not results:
                logger.warning(f"BRAPI price_history: sem resultados para {ticker} ({date_from} a {date_to})")
                return []

            history = results[0].get("historicalDataPrice", [])
            if not history:
                # Sem histórico mas tem preço atual: retorna snapshot do dia
                price = results[0].get("regularMarketPrice")
                if price:
                    now = datetime.now(timezone.utc).replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )
                    return [(now, float(price))]
                return []

            rows: list[tuple[datetime, float]] = []
            for entry in history:
                close = entry.get("close") or entry.get("adjclose")
                ts_raw = entry.get("date") or entry.get("timestamp")
                if close is None or ts_raw is None:
                    continue
                # ts_raw pode ser epoch (int) ou string ISO
                if isinstance(ts_raw, (int, float)):
                    dt = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
                else:
                    try:
                        dt = datetime.fromisoformat(str(ts_raw))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue
                rows.append((dt, float(close)))

            rows.sort(key=lambda x: x[0])
            logger.info(f"BRAPI price_history: {ticker} — {len(rows)} registros ({date_from} a {date_to})")
            return rows

    except Exception as e:
        logger.warning(f"BRAPI fetch_price_history error for {ticker}: {e}")
        return []


async def fetch_historical_price(ticker: str, date_str: str) -> Optional[float]:
    """
    Retorna o preco de fechamento de um ativo em uma data específica.
    Consulta uma janela de 5 dias antes para cobrir fins de semana/feriados.
    """
    ref_date  = date.fromisoformat(date_str)
    date_from = (ref_date - timedelta(days=5)).isoformat()
    rows = await fetch_price_history(ticker, date_from, date_str)
    if rows:
        return rows[-1][1]  # ultimo fechamento disponivel na janela
    return None


# ── Cripto (BRAPI Pro) ─────────────────────────────────────────────────────────────────

async def fetch_crypto_quote(tickers: list[str]) -> dict[str, float]:
    """
    Busca cotação atual de criptomoedas via BRAPI Pro (/api/v2/crypto).
    Retorna {ticker: price_brl}.

    Centraliza a lógica que antes estava inline em quotes_service.py.
    Tickers sem cotação ficam ausentes no resultado (nunca retorna None como valor).
    """
    if not tickers:
        return {}

    headers = _auth_headers()
    results: dict[str, float] = {}

    # BRAPI v2/crypto aceita múltiplos coins separados por vírgula
    joined = ",".join(t.upper() for t in tickers)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/crypto",
                headers=headers,
                params={"coin": joined, "currency": "BRL"},
            )
            resp.raise_for_status()
            data  = resp.json()
            coins = data.get("coins") or []
            for coin in coins:
                symbol = coin.get("coin") or coin.get("symbol") or ""
                price  = coin.get("regularMarketPrice") or coin.get("price")
                if symbol and price is not None:
                    results[symbol.upper()] = float(price)
    except Exception as e:
        logger.warning(f"BRAPI fetch_crypto_quote error for {tickers}: {e}")

    return results


# ── Informações do ativo ──────────────────────────────────────────────────────────────

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
    Silencioso em caso de erro — nunca deve quebrar o fluxo de criação de ativo.
    """
    try:
        info = await fetch_asset_info(ticker)
        if not info:
            return None
        logo = info.get("logourl") or info.get("logo_url") or info.get("logo")
        return str(logo) if logo else None
    except Exception as e:
        logger.warning(f"BRAPI fetch_logo_url error for {ticker}: {e}")
        return None


# ── Tesouro Direto ────────────────────────────────────────────────────────────────────

async def fetch_treasury_price_by_date(slug: str, date_str: str) -> Optional[float]:
    headers = _auth_headers()
    try:
        ref_date  = date.fromisoformat(date_str)
        date_from = (ref_date - timedelta(days=5)).isoformat()
        date_to   = date_str
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


# ── Busca / sugestões de ticker ────────────────────────────────────────────────────────

async def fetch_ticker_suggestions(
    q: str,
    limit: int = 10,
    asset_type: Optional[str] = None,
) -> list[dict]:
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
                row    = item
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
