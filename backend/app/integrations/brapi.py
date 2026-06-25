import httpx
import logging
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_BASE = "https://brapi.dev/api"

# Limite de dias a partir do qual usamos range=max em vez de range=custom.
_MAX_RANGE_THRESHOLD_DAYS = 365 * 5

# Cache em memoria de tickers conhecidos pela BRAPI.
# Estrutura: {ticker: (is_known: bool, expires_at: float)}
_BRAPI_TICKER_CACHE: dict[str, tuple[bool, float]] = {}
_BRAPI_TICKER_CACHE_TTL = 3600.0  # 1 hora
_BRAPI_TICKER_INVALID_TTL = 86400.0  # 24h para tickers marcados como invalidos

# Tamanho maximo de tickers por request /quote
BRAPI_QUOTE_CHUNK = 20

# Regex para extrair o codigo base de um ticker de cripto.
# Ex: BTC-USD -> BTC | ETHBRL -> ETH | bitcoin -> BITCOIN (normalizado pelo caller)
_CRYPTO_SUFFIX_RE = re.compile(r"[-/](USD|BRL|USDT|USDC|EUR|GBP|BTC)$", re.IGNORECASE)


def _auth_headers() -> dict:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


def _normalize_crypto_ticker(ticker: str) -> str:
    """
    Extrai o codigo base de um ticker de criptomoeda.
    BTC-USD -> BTC | ETHBRL -> ETH | BTC -> BTC
    """
    t = ticker.strip().upper()
    t = _CRYPTO_SUFFIX_RE.sub("", t)
    # Remove sufixos colados sem separador: ETHBRL -> ETH, BTCUSDT -> BTC
    for suffix in ("USDT", "USDC", "BRL", "USD", "EUR", "GBP"):
        if t.endswith(suffix) and len(t) > len(suffix):
            t = t[: -len(suffix)]
            break
    return t


def _parse_history_rows(
    history: list[dict],
    ticker: str,
    label: str,
) -> list[tuple[datetime, float]]:
    """Converte a lista historicalDataPrice da BRAPI em (datetime UTC, float).

    Prioriza adjclose (preco ajustado por splits/dividendos) sobre close bruto
    para garantir consistencia historica em ativos com eventos corporativos.
    """
    rows: list[tuple[datetime, float]] = []
    for entry in history:
        # adjclose tem prioridade: ja vem ajustado por desdobramentos e proventos
        close = entry.get("adjclose") or entry.get("close")
        ts_raw = entry.get("date") or entry.get("timestamp")
        if close is None or ts_raw is None:
            continue
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
    logger.info(f"BRAPI price_history [{label}]: {ticker} — {len(rows)} registros")
    return rows


# ── Validação de tickers BRAPI ────────────────────────────────────────────────

async def fetch_valid_brapi_tickers(
    tickers: list[str],
    asset_type: Optional[str] = None,
) -> set[str]:
    """
    Valida quais tickers do lote existem na base da BRAPI.

    Se asset_type == 'CRIPTO', usa /api/v2/crypto/available em vez de
    /api/v2/tickers (que retorna apenas ativos da B3 e causava confusao
    entre cripto e ETF).

    Usa cache em memoria com TTL de 1 hora para evitar requests repetidos.
    Tickers nao encontrados sao marcados como invalidos no cache (is_known=False)
    para que o chamador pule direto para yfinance.
    """
    if not tickers:
        return set()

    now = time.monotonic()
    known: set[str] = set()
    to_check: list[str] = []

    for t in tickers:
        cached = _BRAPI_TICKER_CACHE.get(t)
        if cached is not None and now < cached[1]:
            if cached[0]:
                known.add(t)
        else:
            to_check.append(t)

    if not to_check:
        return known

    is_crypto = (asset_type or "").upper() == "CRIPTO"
    headers = _auth_headers()

    async with httpx.AsyncClient(timeout=10.0) as client:
        for ticker in to_check:
            try:
                if is_crypto:
                    coin_code = _normalize_crypto_ticker(ticker)
                    resp = await client.get(
                        f"{BRAPI_BASE}/v2/crypto/available",
                        headers=headers,
                        params={"search": coin_code, "limit": 5},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("coins") or data.get("available") or []
                    is_known = any(
                        (item.get("coin") or item.get("symbol") or "").upper() == coin_code.upper()
                        for item in items
                    )
                else:
                    resp = await client.get(
                        f"{BRAPI_BASE}/v2/tickers",
                        headers=headers,
                        params={"search": ticker.upper(), "limit": 1},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    items = (
                        data.get("tickers")
                        or data.get("stocks")
                        or data.get("results")
                        or []
                    )
                    is_known = any(
                        (item.get("stock") or item.get("symbol") or item.get("ticker") or "").upper() == ticker.upper()
                        for item in items
                    )

                ttl = _BRAPI_TICKER_CACHE_TTL if is_known else _BRAPI_TICKER_INVALID_TTL
                _BRAPI_TICKER_CACHE[ticker] = (is_known, now + ttl)
                if is_known:
                    known.add(ticker)
                else:
                    logger.debug("[brapi] ticker nao encontrado na BRAPI: %s", ticker)
            except Exception as e:
                logger.warning("[brapi] fetch_valid_brapi_tickers erro para %s: %s", ticker, e)
                _BRAPI_TICKER_CACHE[ticker] = (True, now + 300.0)
                known.add(ticker)

    return known


async def is_known_by_brapi(ticker: str, asset_type: Optional[str] = None) -> bool:
    result = await fetch_valid_brapi_tickers([ticker], asset_type=asset_type)
    return ticker in result


# ── Helpers internos de cotacao ───────────────────────────────────────────────

def _is_cached_invalid(ticker: str) -> bool:
    """Retorna True se o ticker esta marcado como invalido no cache."""
    cached = _BRAPI_TICKER_CACHE.get(ticker)
    if cached is None:
        return False
    is_known, expires_at = cached
    if time.monotonic() > expires_at:
        return False
    return not is_known


async def _fetch_chunk_with_fallback(
    client: httpx.AsyncClient,
    chunk: list[str],
    headers: dict,
) -> dict[str, float]:
    """
    Tenta buscar o chunk inteiro. Se receber 400 ou erro HTTP, faz retry
    ticker a ticker — marcando os invalidos no cache para evitar futuras
    tentativas desnecessarias.
    """
    results: dict[str, float] = {}

    async def _single(ticker: str) -> Optional[float]:
        try:
            r = await client.get(
                f"{BRAPI_BASE}/quote/{ticker.upper()}",
                headers=headers,
            )
            if r.status_code == 400:
                now = time.monotonic()
                _BRAPI_TICKER_CACHE[ticker] = (False, now + _BRAPI_TICKER_INVALID_TTL)
                logger.debug("[brapi] ticker invalido marcado no cache: %s", ticker)
                return None
            r.raise_for_status()
            data = r.json()
            items = data.get("results", [])
            if items:
                return items[0].get("regularMarketPrice")
        except Exception as e:
            logger.debug("[brapi] _single error para %s: %s", ticker, e)
        return None

    joined = ",".join(chunk)
    url = f"{BRAPI_BASE}/quote/{joined}"
    try:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 400:
            # Chunk tem tickers invalidos — descobre quais via retry individual
            logger.warning(
                "[brapi] fetch_quotes 400 no chunk %s — retentando ticker a ticker", chunk
            )
            for ticker in chunk:
                if _is_cached_invalid(ticker):
                    continue
                price = await _single(ticker)
                if price is not None:
                    results[ticker] = float(price)
            return results

        resp.raise_for_status()
        data = resp.json()
        for item in data.get("results", []):
            symbol = item.get("symbol", "")
            price = item.get("regularMarketPrice")
            if symbol and price is not None:
                results[symbol] = float(price)
    except httpx.HTTPStatusError:
        # ja tratado acima para 400; outros status chegam aqui
        logger.warning("[brapi] fetch_quotes HTTP error no chunk %s", chunk)
    except Exception as e:
        logger.warning("[brapi] fetch_quotes error no chunk %s: %s", chunk, e)

    return results


# ── Cotações atuais ───────────────────────────────────────────────────────────

async def fetch_quotes(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}

    # Filtra ja de saida os tickers marcados como invalidos no cache
    valid = [t for t in tickers if not _is_cached_invalid(t)]
    skipped = len(tickers) - len(valid)
    if skipped:
        logger.debug("[brapi] fetch_quotes: %d tickers invalidos ignorados pelo cache", skipped)

    if not valid:
        return {}

    results: dict[str, float] = {}
    headers = _auth_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i in range(0, len(valid), BRAPI_QUOTE_CHUNK):
            chunk = valid[i: i + BRAPI_QUOTE_CHUNK]
            chunk_results = await _fetch_chunk_with_fallback(client, chunk, headers)
            results.update(chunk_results)

    return results


async def fetch_quotes_with_meta(tickers: list[str]) -> dict[str, dict]:
    if not tickers:
        return {}

    valid = [t for t in tickers if not _is_cached_invalid(t)]
    if not valid:
        return {}

    results: dict[str, dict] = {}
    headers = _auth_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i in range(0, len(valid), BRAPI_QUOTE_CHUNK):
            chunk = valid[i: i + BRAPI_QUOTE_CHUNK]
            joined = ",".join(chunk)
            url = f"{BRAPI_BASE}/quote/{joined}"
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 400:
                    logger.warning("[brapi] fetch_quotes_with_meta 400 no chunk %s", chunk)
                    continue
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("results", []):
                    symbol = item.get("symbol", "")
                    price = item.get("regularMarketPrice")
                    logo = (
                        item.get("logourl")
                        or item.get("logo_url")
                        or item.get("logo")
                    )
                    if symbol:
                        results[symbol] = {
                            "price": float(price) if price is not None else None,
                            "logo_url": str(logo) if logo else None,
                        }
            except Exception as e:
                logger.warning("[brapi] fetch_quotes_with_meta error chunk %s: %s", chunk, e)

    return results


async def fetch_quote_single(ticker: str) -> Optional[float]:
    result = await fetch_quotes([ticker])
    return result.get(ticker)


# ── Catálogo de ativos — /api/v2/tickers ─────────────────────────────────────

async def fetch_all_tickers_v2(
    sub_type: str,
    limit: int = 2000,
) -> list[dict]:
    """
    Busca todos os tickers de um subtipo via /api/v2/tickers com paginacao real.
    sub_type aceitos: 'stock' | 'unit' | 'fii' | 'etf' | 'fi-infra' | 'fi-agro' | 'bdr'
    """
    headers   = _auth_headers()
    all_items: list[dict] = []
    page      = 1

    while True:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/tickers",
                    headers=headers,
                    params={
                        "subType":   sub_type,
                        "limit":     limit,
                        "page":      page,
                        "sortBy":    "symbol",
                        "sortOrder": "asc",
                    },
                )
                resp.raise_for_status()
                data  = resp.json()
                items = (
                    data.get("tickers")
                    or data.get("stocks")
                    or data.get("results")
                    or []
                )
        except Exception as e:
            logger.error(f"[brapi] /v2/tickers subType={sub_type} page={page}: {e}")
            break

        if not items:
            break

        now = time.monotonic()
        for item in items:
            t = (item.get("stock") or item.get("symbol") or item.get("ticker") or "").upper()
            if t:
                _BRAPI_TICKER_CACHE[t] = (True, now + _BRAPI_TICKER_CACHE_TTL)

        all_items.extend(items)
        logger.info(
            f"[brapi] /v2/tickers subType={sub_type} page={page}: "
            f"{len(items)} itens ({len(all_items)} acumulados)"
        )

        if len(items) < limit:
            break
        page += 1

    return all_items


async def fetch_crypto_available_all(limit: int = 500) -> list[dict]:
    """
    Busca todas as criptomoedas disponiveis na BRAPI via /api/v2/crypto/available
    com paginacao real. Retorna lista de dicts com pelo menos:
      { "coin": "BTC", "coinName": "Bitcoin", ... }

    Usado pelo seed para popular a tabela assets com asset_type=CRIPTO,
    permitindo busca por nome completo (ex: "Bitcoin", "Ethereum", "Cardano").
    """
    headers   = _auth_headers()
    all_coins: list[dict] = []
    page      = 1

    while True:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/crypto/available",
                    headers=headers,
                    params={"limit": limit, "page": page},
                )
                resp.raise_for_status()
                data  = resp.json()
                items = (
                    data.get("coins")
                    or data.get("available")
                    or (data if isinstance(data, list) else [])
                )
        except Exception as e:
            logger.error(f"[brapi] /v2/crypto/available page={page}: {e}")
            break

        if not items:
            break

        now = time.monotonic()
        for item in items:
            coin = (item.get("coin") or item.get("symbol") or "").upper()
            if coin:
                _BRAPI_TICKER_CACHE[coin] = (True, now + _BRAPI_TICKER_CACHE_TTL)

        all_coins.extend(items)
        logger.info(
            f"[brapi] /v2/crypto/available page={page}: "
            f"{len(items)} moedas ({len(all_coins)} acumuladas)"
        )

        if len(items) < limit:
            break
        page += 1

    return all_coins


# ── Histórico diário de preços ────────────────────────────────────────────────

async def fetch_price_history(
    ticker: str,
    date_from: str,
    date_to: str,
) -> list[tuple[datetime, float]]:
    from datetime import date as _date
    try:
        d_from = _date.fromisoformat(date_from)
        d_to   = _date.fromisoformat(date_to)
        delta  = (d_to - d_from).days
    except ValueError:
        delta  = 0

    if delta > _MAX_RANGE_THRESHOLD_DAYS:
        logger.info(f"BRAPI price_history: {ticker} janela {delta}d > threshold — usando range=max")
        rows = await fetch_price_history_full(ticker)
        cutoff_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        cutoff_to   = datetime.fromisoformat(date_to).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
        return [(dt, c) for dt, c in rows if cutoff_from <= dt <= cutoff_to]

    headers = _auth_headers()
    ticker_upper = ticker.upper()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/stocks/historical",
                headers=headers,
                params={
                    "symbols":   ticker_upper,
                    "interval":  "1d",
                    "startDate": date_from,
                    "endDate":   date_to,
                },
            )
            resp.raise_for_status()
            data    = resp.json()
            results = data.get("results") or data.get("stocks") or []
            if results:
                history = results[0].get("historicalDataPrice") or []
                if history:
                    return _parse_history_rows(history, ticker, f"v2/stocks {date_from} a {date_to}")
    except Exception as e:
        logger.warning(f"BRAPI fetch_price_history v2 error for {ticker}: {e}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/quote/{ticker_upper}",
                headers=headers,
                params={
                    "interval":  "1d",
                    "startDate": date_from,
                    "endDate":   date_to,
                },
            )
            resp.raise_for_status()
            data    = resp.json()
            results = data.get("results", [])
            if not results:
                logger.warning(f"BRAPI price_history: sem resultados para {ticker} ({date_from} a {date_to})")
                return []

            history = results[0].get("historicalDataPrice", [])
            if not history:
                price = results[0].get("regularMarketPrice")
                if price:
                    now = datetime.now(timezone.utc).replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )
                    return [(now, float(price))]
                return []

            return _parse_history_rows(history, ticker, f"{date_from} a {date_to}")

    except Exception as e:
        logger.warning(f"BRAPI fetch_price_history error for {ticker}: {e}")
        return []


async def fetch_price_history_full(
    ticker: str,
) -> list[tuple[datetime, float]]:
    headers = _auth_headers()
    ticker_upper = ticker.upper()
    url = f"{BRAPI_BASE}/quote/{ticker_upper}?range=max&interval=1d"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data    = resp.json()
            results = data.get("results", [])
            if not results:
                logger.warning(f"BRAPI price_history_full: sem resultados para {ticker}")
                return []

            history = results[0].get("historicalDataPrice", [])
            if not history:
                price = results[0].get("regularMarketPrice")
                if price:
                    now = datetime.now(timezone.utc).replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )
                    logger.info(f"BRAPI price_history_full: {ticker} sem historico, usando snapshot atual")
                    return [(now, float(price))]
                return []

            return _parse_history_rows(history, ticker, "range=max")

    except Exception as e:
        logger.warning(f"BRAPI fetch_price_history_full error for {ticker}: {e}")
        return []


async def fetch_stocks_historical_v2(
    ticker: str,
    range_: str = "max",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[tuple[datetime, float]]:
    headers = _auth_headers()
    ticker_upper = ticker.upper()
    params: dict = {"symbols": ticker_upper, "interval": "1d"}
    if date_from and date_to:
        params["startDate"] = date_from
        params["endDate"]   = date_to
    else:
        params["range"] = range_

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/stocks/historical",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results") or data.get("stocks") or []
            if not results:
                logger.warning(f"[brapi] fetch_stocks_historical_v2: sem resultados para {ticker}")
                return []

            history = results[0].get("historicalDataPrice") or []
            if not history:
                price = results[0].get("regularMarketPrice")
                if price:
                    now = datetime.now(timezone.utc).replace(hour=21, minute=0, second=0, microsecond=0)
                    return [(now, float(price))]
                return []

            return _parse_history_rows(history, ticker, f"v2/stocks range={range_}")

    except Exception as e:
        logger.warning(f"[brapi] fetch_stocks_historical_v2 error for {ticker}: {e}")
        return []


async def fetch_fii_historical_v2(
    ticker: str,
    range_: str = "max",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[tuple[datetime, float]]:
    headers = _auth_headers()
    ticker_upper = ticker.upper()
    params: dict = {"symbols": ticker_upper, "interval": "1d"}
    if date_from and date_to:
        params["startDate"] = date_from
        params["endDate"]   = date_to
    else:
        params["range"] = range_

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/fii/historical",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results") or data.get("fiis") or []
            if not results:
                logger.warning(f"[brapi] fetch_fii_historical_v2: sem resultados para {ticker}")
                return []

            history = results[0].get("historicalDataPrice") or []
            if not history:
                price = results[0].get("regularMarketPrice")
                if price:
                    now = datetime.now(timezone.utc).replace(hour=21, minute=0, second=0, microsecond=0)
                    return [(now, float(price))]
                return []

            return _parse_history_rows(history, ticker, f"v2/fii range={range_}")

    except Exception as e:
        logger.warning(f"[brapi] fetch_fii_historical_v2 error for {ticker}: {e}")
        return []


async def fetch_historical_price(ticker: str, date_str: str) -> Optional[float]:
    ref_date  = date.fromisoformat(date_str)
    date_from = (ref_date - timedelta(days=5)).isoformat()
    rows = await fetch_price_history(ticker, date_from, date_str)
    if rows:
        return rows[-1][1]
    return None


# ── Moedas ────────────────────────────────────────────────────────────────────

def _extract_price_from_item(item: dict) -> Optional[float]:
    for field in (
        "regularMarketPrice",
        "ask",
        "bid",
        "close",
        "price",
        "high",
        "low",
    ):
        val = item.get(field)
        if val is not None:
            try:
                f = float(val)
                if f > 0:
                    return f
            except (TypeError, ValueError):
                continue
    return None


async def fetch_currency_rate(pair: str = "USD-BRL") -> Optional[float]:
    headers = _auth_headers()
    pairs_to_try = [pair, pair.replace("-", "")]

    for pair_fmt in pairs_to_try:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/currency",
                    headers=headers,
                    params={"currency": pair_fmt},
                )
                resp.raise_for_status()
                data = resp.json()

                currencies = (
                    data.get("currencies")
                    or data.get("results")
                    or (data if isinstance(data, list) else [])
                )

                for item in currencies:
                    if not isinstance(item, dict):
                        continue
                    price = _extract_price_from_item(item)
                    if price is not None:
                        logger.info(f"[brapi] fetch_currency_rate {pair_fmt} = {price}")
                        return price

                for item in currencies:
                    if not isinstance(item, dict):
                        continue
                    hist = item.get("historical") or []
                    if hist and isinstance(hist, list):
                        last = hist[-1] if isinstance(hist[-1], dict) else None
                        if last:
                            price = _extract_price_from_item(last)
                            if price is not None:
                                logger.info(f"[brapi] fetch_currency_rate (hist fallback) {pair_fmt} = {price}")
                                return price

                logger.warning(f"[brapi] fetch_currency_rate: par {pair_fmt!r} sem cotacao na resposta")

        except Exception as e:
            logger.warning(f"[brapi] fetch_currency_rate error for {pair_fmt}: {e}")

    return None


async def fetch_currency_history(
    pair: str,
    start_date: str,
    end_date: str,
) -> list[tuple[date, float]]:
    headers = _auth_headers()
    pairs_to_try = [pair, pair.replace("-", "")]

    for pair_fmt in pairs_to_try:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/currency/historical",
                    headers=headers,
                    params={
                        "currency":  pair_fmt,
                        "startDate": start_date,
                        "endDate":   end_date,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                entries = (
                    data.get("currency")
                    or data.get("historical")
                    or data.get("currencies")
                    or (data if isinstance(data, list) else [])
                )
                if not entries:
                    logger.warning(f"[brapi] fetch_currency_history: sem dados para {pair_fmt} ({start_date} a {end_date})")
                    continue

                flat: list[dict] = []
                for item in entries:
                    hist = item.get("historical") if isinstance(item, dict) else None
                    if hist and isinstance(hist, list):
                        flat.extend(hist)
                    elif isinstance(item, dict) and ("date" in item or "close" in item):
                        flat.append(item)

                rows: list[tuple[date, float]] = []
                for entry in flat:
                    raw_date  = entry.get("date") or entry.get("timestamp")
                    raw_price = (
                        entry.get("close")
                        or entry.get("regularMarketPrice")
                        or entry.get("price")
                        or entry.get("ask")
                    )
                    if raw_date is None or raw_price is None:
                        continue
                    try:
                        if isinstance(raw_date, (int, float)):
                            d = datetime.fromtimestamp(raw_date, tz=timezone.utc).date()
                        else:
                            d = date.fromisoformat(str(raw_date)[:10])
                        f_price = float(raw_price)
                        if f_price > 0:
                            rows.append((d, f_price))
                    except (ValueError, TypeError):
                        continue

                rows.sort(key=lambda x: x[0])
                if rows:
                    logger.info(f"[brapi] fetch_currency_history {pair_fmt}: {len(rows)} registros ({start_date} a {end_date})")
                    return rows

        except Exception as e:
            logger.warning(f"[brapi] fetch_currency_history error for {pair_fmt} ({start_date} a {end_date}): {e}")

    return []


# ── Cripto ────────────────────────────────────────────────────────────────────

async def fetch_crypto_quote(tickers: list[str]) -> dict[str, float]:
    """
    Busca cotacao de criptomoedas via /api/v2/crypto.
    Normaliza os tickers antes de enviar: BTC-USD -> BTC, ETHBRL -> ETH.
    O resultado e indexado pelo ticker ORIGINAL para compatibilidade com
    o cache do quotes_service.
    """
    if not tickers:
        return {}

    headers = _auth_headers()
    results: dict[str, float] = {}

    # Mapa: codigo_normalizado -> [tickers_originais]
    norm_map: dict[str, list[str]] = {}
    for t in tickers:
        code = _normalize_crypto_ticker(t)
        norm_map.setdefault(code, []).append(t)

    joined = ",".join(norm_map.keys())
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
                symbol = (coin.get("coin") or coin.get("symbol") or "").upper()
                price  = coin.get("regularMarketPrice") or coin.get("price")
                if symbol and price is not None:
                    # Propaga o preco para todos os tickers originais que mapeiam para esse codigo
                    for original in norm_map.get(symbol, [symbol]):
                        results[original] = float(price)
                    # Garante que o codigo normalizado tambem esta no resultado
                    results[symbol] = float(price)
    except Exception as e:
        logger.warning(f"BRAPI fetch_crypto_quote error for {tickers}: {e}")

    return results


# ── Informações do ativo ──────────────────────────────────────────────────────

async def fetch_asset_info(ticker: str) -> Optional[dict]:
    headers = _auth_headers()
    url = f"{BRAPI_BASE}/quote/{ticker.upper()}?modules=summaryProfile,defaultKeyStatistics"
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
    try:
        info = await fetch_asset_info(ticker)
        if not info:
            return None
        logo = info.get("logourl") or info.get("logo_url") or info.get("logo")
        return str(logo) if logo else None
    except Exception as e:
        logger.warning(f"BRAPI fetch_logo_url error for {ticker}: {e}")
        return None


# ── Tesouro Direto ────────────────────────────────────────────────────────────

async def fetch_treasury_price_by_date(slug: str, date_str: str) -> Optional[float]:
    headers = _auth_headers()
    try:
        ref_date  = date.fromisoformat(date_str)
        date_from = (ref_date - timedelta(days=5)).isoformat()
        date_to   = date_str
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/treasury/{slug}/historical",
                headers=headers,
                params={"startDate": date_from, "endDate": date_to},
            )
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


# ── Busca / sugestões de ticker ───────────────────────────────────────────────

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


async def get_quotes_bulk(tickers: list[str]) -> list[dict]:
    if not tickers:
        return []
    results: list[dict] = []
    valid = [t for t in tickers if not _is_cached_invalid(t)]
    headers = _auth_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i in range(0, len(valid), BRAPI_QUOTE_CHUNK):
            chunk = valid[i: i + BRAPI_QUOTE_CHUNK]
            joined = ",".join(chunk)
            url    = f"{BRAPI_BASE}/quote/{joined}"
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                results.extend(data.get("results", []))
            except Exception as e:
                logger.warning(f"BRAPI get_quotes_bulk error for chunk {chunk}: {e}")
    return results


def _yf_search_sync(q: str, limit: int = 10, asset_type: Optional[str] = None) -> list[dict]:
    try:
        import yfinance as yf
        results = []

        def _rows_from_df(df) -> list[dict]:
            if df is None or (hasattr(df, 'empty') and df.empty):
                return []
            rows = []
            for _, row in df.iterrows():
                ticker = str(row.get("symbol") or row.get("Symbol") or "").strip()
                name   = str(row.get("longname") or row.get("shortname") or row.get("name") or "").strip()
                kind   = str(row.get("quoteType") or asset_type or "").lower()
                if ticker:
                    rows.append({"ticker": ticker.upper(), "name": name, "type": kind})
            return rows

        if asset_type == "stock":
            try:
                df = yf.Lookup(q).stock
                results = _rows_from_df(df)
            except Exception:
                pass
        elif asset_type == "etf":
            try:
                df = yf.Lookup(q).etf
                results = _rows_from_df(df)
            except Exception:
                pass

        if not results:
            try:
                search = yf.Search(q, max_results=limit)
                items  = search.quotes or []
                for item in items:
                    if isinstance(item, dict):
                        ticker = item.get("symbol") or item.get("ticker") or ""
                        name   = item.get("longname") or item.get("shortname") or ""
                        kind   = item.get("quoteType") or asset_type or ""
                    else:
                        ticker = str(getattr(item, "symbol", "") or "")
                        name   = str(getattr(item, "longname", "") or getattr(item, "shortname", "") or "")
                        kind   = str(getattr(item, "quoteType", "") or asset_type or "")
                    if ticker:
                        results.append({"ticker": ticker.upper(), "name": name, "type": kind.lower()})
            except Exception as e:
                logger.warning(f"yfinance Search fallback error for q={q!r}: {e}")

        return results[:limit]
    except Exception as e:
        logger.warning(f"yfinance search error for q={q!r} type={asset_type!r}: {e}")
        return []
