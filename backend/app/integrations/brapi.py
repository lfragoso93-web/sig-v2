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

# Tamanho maximo de tickers por request de dividendos (limite BRAPI)
BRAPI_DIVIDENDS_CHUNK = 20

# Regex para extrair o codigo base de um ticker de cripto.
_CRYPTO_SUFFIX_RE = re.compile(r"[-/](USD|BRL|USDT|USDC|EUR|GBP|BTC)$", re.IGNORECASE)

# Mapa de nomes completos de criptomoedas para seus codigos de mercado.
_CRYPTO_NAME_MAP: dict[str, str] = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "CARDANO": "ADA",
    "SOLANA": "SOL",
    "DOGECOIN": "DOGE",
    "RIPPLE": "XRP",
    "POLKADOT": "DOT",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "LITECOIN": "LTC",
    "UNISWAP": "UNI",
    "STELLAR": "XLM",
    "TETHER": "USDT",
    "BINANCECOIN": "BNB",
    "BNBCOIN": "BNB",
    "SHIBA": "SHIB",
    "SHIBAINUTOKEN": "SHIB",
    "POLYGON": "MATIC",
    "NEARPROTOCOL": "NEAR",
    "ATOMCOSMOS": "ATOM",
    "COSMOS": "ATOM",
    "TRON": "TRX",
    "ALGORAND": "ALGO",
    "VECHAIN": "VET",
    "FILECOIN": "FIL",
    "INTERNETCOMPUTER": "ICP",
    "APTOS": "APT",
    "ARBITRUM": "ARB",
    "OPTIMISM": "OP",
    "INJECTIVE": "INJ",
    "AAVE": "AAVE",
    "MAKER": "MKR",
    "COMPOUND": "COMP",
    "MONERO": "XMR",
    "ZCASH": "ZEC",
    "DASH": "DASH",
    "ETHEREUMCLASSIC": "ETC",
    "BITCOINCASH": "BCH",
    "BITCOINSV": "BSV",
}

# ── Tesouro Direto — mapa estático de nomes comuns → slug BRAPI ─────────────────────
#
# Camada 1: resolve variações de digitação do usuário para o slug exato da BRAPI.
# Inclui variações com/sem acento, com/sem espaço, abreviacoes comuns.
# Atualizar aqui quando a STN emitir novos titulos que usuarios cadastrarem
# com nomes nao cobertos pela normalizacao dinamica (Camada 2/3).
_TREASURY_NAME_MAP: dict[str, str] = {
    # ── Tesouro Selic ──────────────────────────────────────────────────────────────────────
    "TESOURO SELIC 2026":                         "tesouro-selic-01032026",
    "TESOURO SELIC 2027":                         "tesouro-selic-01032027",
    "TESOURO SELIC 2029":                         "tesouro-selic-01032029",
    "TESOURO SELIC 2031":                         "tesouro-selic-01032031",
    "LFT 2026":                                   "tesouro-selic-01032026",
    "LFT 2027":                                   "tesouro-selic-01032027",
    "LFT 2029":                                   "tesouro-selic-01032029",
    "LFT 2031":                                   "tesouro-selic-01032031",
    # ── Tesouro Prefixado ───────────────────────────────────────────────────────────────
    "TESOURO PREFIXADO 2026":                     "tesouro-prefixado-01012026",
    "TESOURO PREFIXADO 2027":                     "tesouro-prefixado-01012027",
    "TESOURO PREFIXADO 2029":                     "tesouro-prefixado-01012029",
    "TESOURO PREFIXADO 2031":                     "tesouro-prefixado-01012031",
    "TESOURO PREFIXADO 2033":                     "tesouro-prefixado-01012033",
    "LTN 2026":                                   "tesouro-prefixado-01012026",
    "LTN 2027":                                   "tesouro-prefixado-01012027",
    "LTN 2029":                                   "tesouro-prefixado-01012029",
    "LTN 2031":                                   "tesouro-prefixado-01012031",
    # ── Tesouro Prefixado com Juros Semestrais ───────────────────────────────────────
    "TESOURO PREFIXADO COM JUROS SEMESTRAIS 2027": "tesouro-prefixado-com-juros-semestrais-01012027",
    "TESOURO PREFIXADO COM JUROS SEMESTRAIS 2029": "tesouro-prefixado-com-juros-semestrais-01012029",
    "TESOURO PREFIXADO COM JUROS SEMESTRAIS 2031": "tesouro-prefixado-com-juros-semestrais-01012031",
    "TESOURO PREFIXADO COM JUROS SEMESTRAIS 2033": "tesouro-prefixado-com-juros-semestrais-01012033",
    "TESOURO PREFIXADO JUROS SEMESTRAIS 2027":     "tesouro-prefixado-com-juros-semestrais-01012027",
    "TESOURO PREFIXADO JUROS SEMESTRAIS 2029":     "tesouro-prefixado-com-juros-semestrais-01012029",
    "TESOURO PREFIXADO JUROS SEMESTRAIS 2031":     "tesouro-prefixado-com-juros-semestrais-01012031",
    "NTN-F 2027":                                 "tesouro-prefixado-com-juros-semestrais-01012027",
    "NTN-F 2029":                                 "tesouro-prefixado-com-juros-semestrais-01012029",
    "NTN-F 2031":                                 "tesouro-prefixado-com-juros-semestrais-01012031",
    # ── Tesouro IPCA+ ──────────────────────────────────────────────────────────────────
    "TESOURO IPCA+ 2026":                         "tesouro-ipca-15082026",
    "TESOURO IPCA 2026":                          "tesouro-ipca-15082026",
    "TESOURO IPCA+ 2029":                         "tesouro-ipca-15052029",
    "TESOURO IPCA 2029":                          "tesouro-ipca-15052029",
    "TESOURO IPCA+ 2035":                         "tesouro-ipca-15052035",
    "TESOURO IPCA 2035":                          "tesouro-ipca-15052035",
    "TESOURO IPCA+ 2045":                         "tesouro-ipca-15052045",
    "TESOURO IPCA 2045":                          "tesouro-ipca-15052045",
    "NTN-B PRINCIPAL 2026":                       "tesouro-ipca-15082026",
    "NTN-B PRINCIPAL 2029":                       "tesouro-ipca-15052029",
    "NTN-B PRINCIPAL 2035":                       "tesouro-ipca-15052035",
    # ── Tesouro IPCA+ com Juros Semestrais ─────────────────────────────────────────
    "TESOURO IPCA+ COM JUROS SEMESTRAIS 2026":    "tesouro-ipca-com-juros-semestrais-15082026",
    "TESOURO IPCA+ COM JUROS SEMESTRAIS 2030":    "tesouro-ipca-com-juros-semestrais-15082030",
    "TESOURO IPCA+ COM JUROS SEMESTRAIS 2032":    "tesouro-ipca-com-juros-semestrais-15082032",
    "TESOURO IPCA+ COM JUROS SEMESTRAIS 2035":    "tesouro-ipca-com-juros-semestrais-15082035",
    "TESOURO IPCA+ COM JUROS SEMESTRAIS 2040":    "tesouro-ipca-com-juros-semestrais-15082040",
    "TESOURO IPCA+ COM JUROS SEMESTRAIS 2045":    "tesouro-ipca-com-juros-semestrais-15082045",
    "TESOURO IPCA+ COM JUROS SEMESTRAIS 2055":    "tesouro-ipca-com-juros-semestrais-15082055",
    "TESOURO IPCA COM JUROS SEMESTRAIS 2035":     "tesouro-ipca-com-juros-semestrais-15082035",
    "TESOURO IPCA COM JUROS SEMESTRAIS 2045":     "tesouro-ipca-com-juros-semestrais-15082045",
    "TESOURO IPCA JUROS SEMESTRAIS 2035":         "tesouro-ipca-com-juros-semestrais-15082035",
    "TESOURO IPCA JUROS SEMESTRAIS 2045":         "tesouro-ipca-com-juros-semestrais-15082045",
    "NTN-B 2026":                                 "tesouro-ipca-com-juros-semestrais-15082026",
    "NTN-B 2030":                                 "tesouro-ipca-com-juros-semestrais-15082030",
    "NTN-B 2035":                                 "tesouro-ipca-com-juros-semestrais-15082035",
    "NTN-B 2040":                                 "tesouro-ipca-com-juros-semestrais-15082040",
    "NTN-B 2045":                                 "tesouro-ipca-com-juros-semestrais-15082045",
    "NTN-B 2055":                                 "tesouro-ipca-com-juros-semestrais-15082055",
    # ── Tesouro RendA+ ──────────────────────────────────────────────────────────────────
    "TESOURO RENDA+ 2030":                        "tesouro-renda-mais-2030",
    "TESOURO RENDA+ 2035":                        "tesouro-renda-mais-2035",
    "TESOURO RENDA+ 2040":                        "tesouro-renda-mais-2040",
    "TESOURO RENDA+ 2045":                        "tesouro-renda-mais-2045",
    "TESOURO RENDA+ 2050":                        "tesouro-renda-mais-2050",
    "TESOURO RENDA+ 2055":                        "tesouro-renda-mais-2055",
    "TESOURO RENDA+ 2060":                        "tesouro-renda-mais-2060",
    "TESOURO RENDA MAIS 2030":                    "tesouro-renda-mais-2030",
    "TESOURO RENDA MAIS 2035":                    "tesouro-renda-mais-2035",
    "TESOURO RENDA MAIS 2040":                    "tesouro-renda-mais-2040",
    "TESOURO RENDA MAIS 2045":                    "tesouro-renda-mais-2045",
    "TESOURO RENDA MAIS 2050":                    "tesouro-renda-mais-2050",
    "TESOURO RENDA MAIS 2055":                    "tesouro-renda-mais-2055",
    "TESOURO RENDA MAIS 2060":                    "tesouro-renda-mais-2060",
    # ── Tesouro Educa+ ──────────────────────────────────────────────────────────────────
    "TESOURO EDUCA+ 2026":                        "tesouro-educa-mais-2026",
    "TESOURO EDUCA+ 2029":                        "tesouro-educa-mais-2029",
    "TESOURO EDUCA+ 2031":                        "tesouro-educa-mais-2031",
    "TESOURO EDUCA MAIS 2026":                    "tesouro-educa-mais-2026",
    "TESOURO EDUCA MAIS 2029":                    "tesouro-educa-mais-2029",
    "TESOURO EDUCA MAIS 2031":                    "tesouro-educa-mais-2031",
}

# Regex para detectar se o ticker ja tem formato de slug BRAPI
_TREASURY_SLUG_RE = re.compile(r"^tesouro-[a-z0-9-]+$")

# Cache em memoria do catalogo de slugs (populado pelo fallback dinamico)
_TREASURY_CATALOG_CACHE: dict[str, str] = {}
_TREASURY_CATALOG_EXPIRES: float = 0.0
_TREASURY_CATALOG_TTL = 21600.0  # 6 horas


def _slug_from_raw(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"[+]", "", s)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def _normalize_treasury_ticker(ticker: str, catalog: Optional[dict[str, str]] = None) -> str:
    t_upper = ticker.strip().upper()

    if t_upper in _TREASURY_NAME_MAP:
        resolved = _TREASURY_NAME_MAP[t_upper]
        logger.debug("[treasury] Camada 1 (mapa): %s -> %s", ticker, resolved)
        return resolved

    t_lower = ticker.strip().lower()
    if _TREASURY_SLUG_RE.match(t_lower):
        logger.debug("[treasury] Camada 2 (slug direto): %s", t_lower)
        return t_lower

    if catalog:
        slug_candidate = _slug_from_raw(ticker)
        if slug_candidate in catalog:
            resolved = catalog[slug_candidate]
            logger.debug("[treasury] Camada 3 (catalogo exato): %s -> %s", ticker, resolved)
            return resolved
        for cat_slug_norm, cat_symbol in catalog.items():
            if slug_candidate in cat_slug_norm or cat_slug_norm in slug_candidate:
                logger.debug("[treasury] Camada 3 (catalogo parcial): %s -> %s", ticker, cat_symbol)
                return cat_symbol

    fallback = _slug_from_raw(ticker)
    logger.warning("[treasury] sem match para %r — usando slug=%s", ticker, fallback)
    return fallback


async def _load_treasury_catalog() -> dict[str, str]:
    global _TREASURY_CATALOG_CACHE, _TREASURY_CATALOG_EXPIRES

    now = time.monotonic()
    if _TREASURY_CATALOG_CACHE and now < _TREASURY_CATALOG_EXPIRES:
        return _TREASURY_CATALOG_CACHE

    items = await fetch_treasury_list()
    catalog: dict[str, str] = {}
    for item in items:
        symbol = (
            item.get("symbol")
            or item.get("slug")
            or item.get("name")
            or ""
        ).strip()
        if symbol:
            catalog[_slug_from_raw(symbol)] = symbol

    _TREASURY_CATALOG_CACHE = catalog
    _TREASURY_CATALOG_EXPIRES = now + _TREASURY_CATALOG_TTL
    logger.info("[treasury] catalogo carregado: %d titulos", len(catalog))
    return catalog


def _auth_headers() -> dict:
    if settings.BRAPI_TOKEN:
        return {"Authorization": f"Bearer {settings.BRAPI_TOKEN}"}
    return {}


def _normalize_crypto_ticker(ticker: str) -> str:
    t = ticker.strip().upper()
    if t in _CRYPTO_NAME_MAP:
        return _CRYPTO_NAME_MAP[t]
    t = _CRYPTO_SUFFIX_RE.sub("", t)
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
    """Converte a lista historicalDataPrice em (datetime UTC, float)."""
    rows: list[tuple[datetime, float]] = []
    for entry in history:
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
    logger.debug("[market_data] price_history [%s]: %s — %d registros", label, ticker, len(rows))
    return rows


# ── Validação de tickers ────────────────────────────────────────────────────────────────────

async def fetch_valid_brapi_tickers(
    tickers: list[str],
    asset_type: Optional[str] = None,
) -> set[str]:
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
                    logger.debug("[market_data] ticker nao encontrado: %s", ticker)
            except Exception as e:
                logger.warning("[market_data] fetch_valid_tickers erro para %s: %s", ticker, e)
                _BRAPI_TICKER_CACHE[ticker] = (True, now + 300.0)
                known.add(ticker)

    return known


async def is_known_by_brapi(ticker: str, asset_type: Optional[str] = None) -> bool:
    result = await fetch_valid_brapi_tickers([ticker], asset_type=asset_type)
    return ticker in result


# ── Helpers internos de cotacao ───────────────────────────────────────────────────────────────

def _is_cached_invalid(ticker: str) -> bool:
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
                logger.debug("[market_data] ticker invalido marcado no cache: %s", ticker)
                return None
            r.raise_for_status()
            data = r.json()
            items = data.get("results", [])
            if items:
                return items[0].get("regularMarketPrice")
        except Exception as e:
            logger.debug("[market_data] _single error para %s: %s", ticker, e)
        return None

    joined = ",".join(chunk)
    url = f"{BRAPI_BASE}/quote/{joined}"
    try:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 400:
            logger.warning(
                "[market_data] fetch_quotes 400 no chunk %s — retentando ticker a ticker", chunk
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
        logger.warning("[market_data] fetch_quotes HTTP error no chunk %s", chunk)
    except Exception as e:
        logger.warning("[market_data] fetch_quotes error no chunk %s: %s", chunk, e)

    return results


# ── Cotações atuais ─────────────────────────────────────────────────────────────────────────────

async def fetch_quotes(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}

    valid = [t for t in tickers if not _is_cached_invalid(t)]
    skipped = len(tickers) - len(valid)
    if skipped:
        logger.debug("[market_data] fetch_quotes: %d tickers invalidos ignorados pelo cache", skipped)

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
                    logger.warning("[market_data] fetch_quotes_with_meta 400 no chunk %s", chunk)
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
                logger.warning("[market_data] fetch_quotes_with_meta error chunk %s: %s", chunk, e)

    return results


async def fetch_quote_single(ticker: str) -> Optional[float]:
    result = await fetch_quotes([ticker])
    return result.get(ticker)


# ── Catálogo de ativos ────────────────────────────────────────────────────────────────────────

async def fetch_all_tickers_v2(
    sub_type: str,
    limit: int = 2000,
) -> list[dict]:
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
            logger.error("[market_data] /v2/tickers subType=%s page=%d: %s", sub_type, page, e)
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
            "[market_data] catalogo subType=%s page=%d: %d itens (%d acumulados)",
            sub_type, page, len(items), len(all_items),
        )

        if len(items) < limit:
            break
        page += 1

    return all_items


async def fetch_crypto_available_all(limit: int = 500) -> list[dict]:
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
            logger.error("[market_data] /v2/crypto/available page=%d: %s", page, e)
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
            "[market_data] crypto catalog page=%d: %d moedas (%d acumuladas)",
            page, len(items), len(all_coins),
        )

        if len(items) < limit:
            break
        page += 1

    return all_coins


# ── Dividendos em batch ──────────────────────────────────────────────────────────────────────

_DividendRow = dict


def _parse_dividend_items(raw_items: list[dict]) -> list[_DividendRow]:
    rows: list[_DividendRow] = []
    for item in raw_items:
        ex_str = (
            item.get("lastDatePrior")
            or item.get("exDate")
            or item.get("ex_date")
            or item.get("approvedOn")
            or ""
        )
        pay_str = (
            item.get("paymentDate")
            or item.get("paidAt")
            or item.get("payment_date")
            or ""
        )
        raw_val = item.get("rate") or item.get("value") or item.get("amount") or 0
        div_type_raw = str(
            item.get("type") or item.get("dividendType") or "DIVIDENDO"
        ).upper()

        if not ex_str:
            continue
        try:
            ex_date = date.fromisoformat(str(ex_str)[:10])
            pay_date = date.fromisoformat(str(pay_str)[:10]) if pay_str else None
            value = float(raw_val)
        except (ValueError, TypeError):
            continue

        if value <= 0:
            continue

        rows.append({
            "ex_date": ex_date,
            "payment_date": pay_date,
            "value_per_unit": value,
            "dividend_type": div_type_raw,
        })
    return rows


async def fetch_stocks_dividends_batch(
    tickers: list[str],
) -> dict[str, list[_DividendRow]]:
    if not tickers:
        return {}

    results: dict[str, list[_DividendRow]] = {t.upper(): [] for t in tickers}
    headers = _auth_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(tickers), BRAPI_DIVIDENDS_CHUNK):
            chunk = [t.upper() for t in tickers[i: i + BRAPI_DIVIDENDS_CHUNK]]
            symbols = ",".join(chunk)
            try:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/stocks/dividends",
                    headers=headers,
                    params={"symbols": symbols},
                )
                if resp.status_code in (401, 403):
                    logger.warning(
                        "[market_data] fetch_stocks_dividends_batch: sem autorizacao — chunk=%s", chunk
                    )
                    continue
                resp.raise_for_status()
                data = resp.json()

                result_items = (
                    data.get("results")
                    or data.get("stocks")
                    or data.get("dividends")
                    or []
                )

                for entry in result_items:
                    symbol = (
                        entry.get("symbol")
                        or entry.get("ticker")
                        or entry.get("stock")
                        or ""
                    ).upper()
                    if not symbol:
                        continue
                    raw_divs = (
                        entry.get("dividends")
                        or entry.get("cashDividends")
                        or entry.get("data")
                        or []
                    )
                    parsed = _parse_dividend_items(raw_divs)
                    if symbol in results:
                        results[symbol] = parsed
                    logger.debug(
                        "[market_data] dividends batch: %s — %d proventos",
                        symbol, len(parsed),
                    )

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[market_data] fetch_stocks_dividends_batch HTTP %s no chunk %s: %s",
                    e.response.status_code, chunk, e,
                )
            except Exception as e:
                logger.warning(
                    "[market_data] fetch_stocks_dividends_batch erro no chunk %s: %s",
                    chunk, e,
                )

    return results


async def fetch_fii_dividends_batch(
    tickers: list[str],
) -> dict[str, list[_DividendRow]]:
    if not tickers:
        return {}

    results: dict[str, list[_DividendRow]] = {t.upper(): [] for t in tickers}
    headers = _auth_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(tickers), BRAPI_DIVIDENDS_CHUNK):
            chunk = [t.upper() for t in tickers[i: i + BRAPI_DIVIDENDS_CHUNK]]
            symbols = ",".join(chunk)
            try:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/fii/dividends",
                    headers=headers,
                    params={"symbols": symbols},
                )
                if resp.status_code in (401, 403):
                    logger.warning(
                        "[market_data] fetch_fii_dividends_batch: sem autorizacao — chunk=%s", chunk
                    )
                    continue
                resp.raise_for_status()
                data = resp.json()

                result_items = (
                    data.get("results")
                    or data.get("fiis")
                    or data.get("dividends")
                    or []
                )

                for entry in result_items:
                    symbol = (
                        entry.get("symbol")
                        or entry.get("ticker")
                        or entry.get("fii")
                        or ""
                    ).upper()
                    if not symbol:
                        continue
                    raw_divs = (
                        entry.get("dividends")
                        or entry.get("cashDividends")
                        or entry.get("data")
                        or []
                    )
                    parsed = _parse_dividend_items(raw_divs)
                    if symbol in results:
                        results[symbol] = parsed
                    logger.debug(
                        "[market_data] fii dividends batch: %s — %d proventos",
                        symbol, len(parsed),
                    )

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[market_data] fetch_fii_dividends_batch HTTP %s no chunk %s: %s",
                    e.response.status_code, chunk, e,
                )
            except Exception as e:
                logger.warning(
                    "[market_data] fetch_fii_dividends_batch erro no chunk %s: %s",
                    chunk, e,
                )

    return results


# ── Histórico diário de preços ────────────────────────────────────────────────────────────────────

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
        logger.info("[market_data] %s janela %dd > threshold — usando range=max", ticker, delta)
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
        logger.warning("[market_data] fetch_price_history v2 error for %s: %s", ticker, e)

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
                logger.warning("[market_data] sem resultados para %s (%s a %s)", ticker, date_from, date_to)
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
        logger.warning("[market_data] fetch_price_history error for %s: %s", ticker, e)
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
                logger.warning("[market_data] price_history_full: sem resultados para %s", ticker)
                return []

            history = results[0].get("historicalDataPrice", [])
            if not history:
                price = results[0].get("regularMarketPrice")
                if price:
                    now = datetime.now(timezone.utc).replace(
                        hour=18, minute=0, second=0, microsecond=0
                    )
                    logger.info("[market_data] %s sem historico, usando snapshot atual", ticker)
                    return [(now, float(price))]
                return []

            return _parse_history_rows(history, ticker, "range=max")

    except Exception as e:
        logger.warning("[market_data] fetch_price_history_full error for %s: %s", ticker, e)
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
                logger.warning("[market_data] fetch_stocks_historical_v2: sem resultados para %s", ticker)
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
        logger.warning("[market_data] fetch_stocks_historical_v2 error for %s: %s", ticker, e)
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
                logger.warning("[market_data] fetch_fii_historical_v2: sem resultados para %s", ticker)
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
        logger.warning("[market_data] fetch_fii_historical_v2 error for %s: %s", ticker, e)
        return []


async def fetch_historical_price(ticker: str, date_str: str) -> Optional[float]:
    ref_date  = date.fromisoformat(date_str)
    date_from = (ref_date - timedelta(days=5)).isoformat()
    rows = await fetch_price_history(ticker, date_from, date_str)
    if rows:
        return rows[-1][1]
    return None


# ── Moedas ──────────────────────────────────────────────────────────────────────────────────

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
                    if price:
                        logger.debug("[market_data] currency %s: %.4f", pair, price)
                        return price

        except Exception as e:
            logger.warning("[market_data] fetch_currency_rate %s error: %s", pair_fmt, e)

    logger.warning("[market_data] fetch_currency_rate: sem resultado para %s", pair)
    return None


async def fetch_crypto_quote(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}

    headers = _auth_headers()
    results: dict[str, float] = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for ticker in tickers:
            coin_code = _normalize_crypto_ticker(ticker)
            try:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/crypto",
                    headers=headers,
                    params={"coin": coin_code, "currency": "BRL"},
                )
                resp.raise_for_status()
                data = resp.json()
                coins = data.get("coins") or data.get("results") or []
                for item in coins:
                    price = item.get("regularMarketPrice") or item.get("price")
                    if price is not None:
                        results[ticker] = float(price)
                        break
            except Exception as e:
                logger.warning("[market_data] fetch_crypto_quote error para %s: %s", ticker, e)

    return results


async def fetch_treasury_prices(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}

    catalog = await _load_treasury_catalog()
    headers = _auth_headers()
    results: dict[str, float] = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for ticker in tickers:
            slug = _normalize_treasury_ticker(ticker, catalog)
            try:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/treasury/{slug}",
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                price = (
                    data.get("price")
                    or data.get("currentPrice")
                    or data.get("pu")
                    or (data.get("treasury") or {}).get("price")
                )
                if price is not None:
                    results[ticker] = float(price)
                    logger.debug("[market_data] treasury %s (%s): %.4f", ticker, slug, float(price))
                else:
                    logger.warning("[market_data] treasury %s (%s): preco ausente na resposta", ticker, slug)
            except Exception as e:
                logger.warning("[market_data] fetch_treasury_prices error para %s (slug=%s): %s", ticker, slug, e)

    return results


async def fetch_treasury_list() -> list[dict]:
    headers = _auth_headers()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BRAPI_BASE}/v2/treasury/list", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("treasuries") or data.get("results") or []
    except Exception as e:
        logger.warning("[market_data] fetch_treasury_list error: %s", e)
        return []
