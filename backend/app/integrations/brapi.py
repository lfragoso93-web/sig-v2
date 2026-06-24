import httpx
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

BRAPI_BASE = "https://brapi.dev/api"

# Limite de dias a partir do qual usamos range=max em vez de range=custom.
# Acima de ~5 anos, range=custom pode ser rejeitado pela BRAPI dependendo do plano.
_MAX_RANGE_THRESHOLD_DAYS = 365 * 5


def _auth_headers() -> dict:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


def _parse_history_rows(
    history: list[dict],
    ticker: str,
    label: str,
) -> list[tuple[datetime, float]]:
    """Converte a lista historicalDataPrice da BRAPI em (datetime UTC, float)."""
    rows: list[tuple[datetime, float]] = []
    for entry in history:
        close = entry.get("close") or entry.get("adjclose")
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


# ── Cotações atuais ───────────────────────────────────────────────────────────────────

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


async def fetch_quotes_with_meta(tickers: list[str]) -> dict[str, dict]:
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


# ── Catálogo de ativos — /api/v2/tickers (endpoint oficial, substitui /quote/list) ──────

async def fetch_all_tickers_v2(
    sub_type: str,
    limit: int = 2000,
) -> list[dict]:
    """
    Busca todos os tickers de um subtipo via /api/v2/tickers com paginação real.

    sub_type aceitos: 'stock' | 'unit' | 'fii' | 'etf' | 'fi-infra' | 'fi-agro' | 'bdr'

    O endpoint suporta limit de até 2000 por página e paginação por 'page'.
    Retorna lista de dicts com pelo menos: stock (ticker), name, sector, subType.
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

        all_items.extend(items)
        logger.info(
            f"[brapi] /v2/tickers subType={sub_type} page={page}: "
            f"{len(items)} itens ({len(all_items)} acumulados)"
        )

        # Paginação real: se retornou menos que o limit, chegamos ao fim
        if len(items) < limit:
            break
        page += 1

    return all_items


# ── Histórico diário de preços (BRAPI Pro) ───────────────────────────────────────

async def fetch_price_history(
    ticker: str,
    date_from: str,
    date_to: str,
) -> list[tuple[datetime, float]]:
    """
    Busca historico de precos diarios via BRAPI (endpoint legado /quote/{ticker}).

    Estrategia adaptativa (BRAPI Pro):
      - Janela <= 5 anos: usa range=custom com from/to exatos.
      - Janela >  5 anos: delega para fetch_price_history_full (range=max)
        e filtra os registros fora da janela solicitada.

    Para novos consumidores, prefira fetch_stocks_historical_v2 ou
    fetch_fii_historical_v2 que usam os endpoints v2 oficiais.
    """
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
    url = (
        f"{BRAPI_BASE}/quote/{ticker}"
        f"?range=custom&interval=1d"
        f"&from={date_from}&to={date_to}"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
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
    """
    Busca o historico completo de precos diarios via BRAPI Pro (range=max).
    Endpoint legado /quote/{ticker} — preferir fetch_stocks_historical_v2
    para novos consumidores.
    """
    headers = _auth_headers()
    url = f"{BRAPI_BASE}/quote/{ticker}?range=max&interval=1d"
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
    """
    Busca historico de precos via /api/v2/stocks/historical (endpoint oficial v2).

    Usado para: ACAO (stock + unit), ETF_NACIONAL, BDR.
    range_ pode ser: '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max'
    Se date_from e date_to forem fornecidos, usa startDate/endDate em vez de range.
    """
    headers = _auth_headers()
    params: dict = {"symbols": ticker, "interval": "1d"}
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

            # Resposta esperada: {"results": [{"symbol": "PETR4", "historicalDataPrice": [...]}]}
            results = data.get("results") or data.get("stocks") or []
            if not results:
                logger.warning(f"[brapi] fetch_stocks_historical_v2: sem resultados para {ticker}")
                return []

            history = results[0].get("historicalDataPrice") or []
            if not history:
                # Fallback: snapshot atual como único ponto
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
    """
    Busca historico de precos via /api/v2/fii/historical (endpoint oficial v2).

    Usado para: FII, FI_INFRA (mapeado como FII), FI_AGRO (mapeado como FII).
    Plano Pro necessário para range=max.
    """
    headers = _auth_headers()
    params: dict = {"symbols": ticker, "interval": "1d"}
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


# ── Moedas — cotação atual e histórico (BRAPI v2/currency) ───────────────────────────

def _extract_price_from_item(item: dict) -> Optional[float]:
    """
    Extrai preco de um item de resposta de moeda da BRAPI.
    Tenta multiplos campos em ordem de preferencia.
    'close' adicionado pois e o campo retornado pelo endpoint /v2/currency na resposta atual.
    """
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
    """
    Retorna a cotacao atual de um par cambial via BRAPI /v2/currency.

    Tenta o par no formato recebido (ex: 'USD-BRL') e tambem sem hifen ('USDBRL').
    Retorna None se a BRAPI falhar ou o par nao for encontrado.
    """
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
    """
    Retorna historico diario de cotacao de um par cambial via BRAPI /v2/currency/historical.

    Tenta o par no formato 'USD-BRL' e 'USDBRL' (sem hifen).
    Retorna [] se BRAPI falhar — o chamador deve tratar o fallback.
    """
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


# ── Cripto (BRAPI Pro) ─────────────────────────────────────────────────────────────────

async def fetch_crypto_quote(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}

    headers = _auth_headers()
    results: dict[str, float] = {}

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


async def get_quotes_bulk(tickers: list[str]) -> list[dict]:
    """Retorna lista de dicts com dados completos de cotacao para um lote de tickers."""
    if not tickers:
        return []
    results: list[dict] = []
    chunks  = [tickers[i:i+20] for i in range(0, len(tickers), 20)]
    headers = _auth_headers()
    async with httpx.AsyncClient(timeout=15.0) as client:
        for chunk in chunks:
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
    """
    Fallback de busca de ticker via yfinance.

    yfinance >= 0.2.50 usa yf.Lookup com atributos de propriedade (nao metodos):
      - yf.Lookup(q).stock       -> DataFrame com acoes
      - yf.Lookup(q).etf         -> DataFrame com ETFs
      - yf.Search(q).quotes      -> lista de dicts (busca geral)

    Versoes antigas usavam yf.Lookup(q).get_stock() (metodo) — removido na 0.2.50+.
    """
    try:
        import yfinance as yf
        results = []

        def _rows_from_df(df) -> list[dict]:
            """Converte DataFrame do Lookup em lista de dicts normalizados."""
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
