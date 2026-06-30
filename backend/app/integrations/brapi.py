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
# Ex: tesouro-selic-01032031, tesouro-ipca-com-juros-semestrais-15082045
_TREASURY_SLUG_RE = re.compile(r"^tesouro-[a-z0-9-]+$")

# Cache em memoria do catalogo de slugs BRAPI (populado pelo fallback dinamico)
# Estrutura: { symbol/slug: True }, expira a cada 6h
_TREASURY_CATALOG_CACHE: dict[str, str] = {}  # slug_norm -> symbol_brapi
_TREASURY_CATALOG_EXPIRES: float = 0.0
_TREASURY_CATALOG_TTL = 21600.0  # 6 horas


def _slug_from_raw(raw: str) -> str:
    """Converte string arbitraria em formato slug: lowercase, espacos -> hifen,
    remove caracteres especiais exceto hifen e digitos."""
    s = raw.strip().lower()
    s = re.sub(r"[+]", "", s)           # remove o '+' de IPCA+
    s = re.sub(r"[^a-z0-9\s-]", "", s)  # remove caracteres especiais
    s = re.sub(r"[\s]+", "-", s)        # espacos -> hifen
    s = re.sub(r"-+", "-", s)           # colapsa hifens duplos
    return s.strip("-")


def _normalize_treasury_ticker(ticker: str, catalog: Optional[dict[str, str]] = None) -> str:
    """
    Resolve o ticker interno do usuario para o slug BRAPI do Tesouro Direto.

    Ordem de resolucao (3 camadas):
      1. Mapa estatico _TREASURY_NAME_MAP — cobre 95% dos casos sem I/O
         Ex: 'Tesouro Selic 2031' -> 'tesouro-selic-01032031'
      2. Deteccao de slug ja no formato correto — passagem direta
         Ex: 'tesouro-selic-01032031' -> 'tesouro-selic-01032031'
      3. Fuzzy match no catalogo dinamico (se fornecido) — cobre titulos novos
         Ex: 'Tesouro IPCA 2060' -> match parcial no catalogo BRAPI

    Retorna o slug BRAPI se encontrado, ou o ticker original slugificado
    como melhor esforco.
    """
    t_upper = ticker.strip().upper()

    # Camada 1: mapa estatico (case-insensitive)
    if t_upper in _TREASURY_NAME_MAP:
        resolved = _TREASURY_NAME_MAP[t_upper]
        logger.debug("[treasury] Camada 1 (mapa): %s -> %s", ticker, resolved)
        return resolved

    # Camada 2: ja e um slug BRAPI valido
    t_lower = ticker.strip().lower()
    if _TREASURY_SLUG_RE.match(t_lower):
        logger.debug("[treasury] Camada 2 (slug direto): %s", t_lower)
        return t_lower

    # Camada 3: fuzzy match no catalogo dinamico
    if catalog:
        slug_candidate = _slug_from_raw(ticker)
        # Tenta match exato no catalogo normalizado
        if slug_candidate in catalog:
            resolved = catalog[slug_candidate]
            logger.debug("[treasury] Camada 3 (catalogo exato): %s -> %s", ticker, resolved)
            return resolved
        # Tenta match parcial: o slug do usuario esta contido num slug do catalogo
        for cat_slug_norm, cat_symbol in catalog.items():
            if slug_candidate in cat_slug_norm or cat_slug_norm in slug_candidate:
                logger.debug("[treasury] Camada 3 (catalogo parcial): %s -> %s", ticker, cat_symbol)
                return cat_symbol

    # Melhor esforco: retorna o ticker slugificado
    fallback = _slug_from_raw(ticker)
    logger.warning("[treasury] _normalize_treasury_ticker: sem match para %r — usando slug=%s", ticker, fallback)
    return fallback


async def _load_treasury_catalog() -> dict[str, str]:
    """
    Carrega (e cacheia por 6h) o catalogo completo de slugs BRAPI via /v2/treasury/list.
    Retorna dict { slug_normalizado: symbol_original }, usado pelo fallback dinamico
    da Camada 3 de _normalize_treasury_ticker.
    """
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
    """
    Extrai o codigo base de um ticker de criptomoeda.

    Ordem de resolucao:
      1. Nomes completos via _CRYPTO_NAME_MAP (ex: BITCOIN -> BTC, CARDANO -> ADA)
      2. Sufixos com separador via regex (ex: BTC-USD -> BTC)
      3. Sufixos colados sem separador (ex: ETHBRL -> ETH, BTCUSDT -> BTC)
    """
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
    """Converte a lista historicalDataPrice da BRAPI em (datetime UTC, float)."""
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
    logger.info(f"BRAPI price_history [{label}]: {ticker} — {len(rows)} registros")
    return rows


# ── Validação de tickers BRAPI ────────────────────────────────────────────────────────────────────

async def fetch_valid_brapi_tickers(
    tickers: list[str],
    asset_type: Optional[str] = None,
) -> set[str]:
    """
    Valida quais tickers do lote existem na base da BRAPI.
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


# ── Helpers internos de cotacao ───────────────────────────────────────────────────────────────

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
        logger.warning("[brapi] fetch_quotes HTTP error no chunk %s", chunk)
    except Exception as e:
        logger.warning("[brapi] fetch_quotes error no chunk %s: %s", chunk, e)

    return results


# ── Cotações atuais ─────────────────────────────────────────────────────────────────────────────

async def fetch_quotes(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}

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


# ── Catálogo de ativos — /api/v2/tickers ────────────────────────────────────────────────────────

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


# ── Dividendos em batch — /api/v2/stocks/dividends e /api/v2/fii/dividends ──────────────────────

# Estrutura de retorno normalizada para um provento individual
# { ex_date, payment_date, value_per_unit, dividend_type }
_DividendRow = dict  # alias legivel


def _parse_dividend_items(raw_items: list[dict]) -> list[_DividendRow]:
    """
    Normaliza a lista de proventos retornada pela BRAPI em um formato interno
    consistente, independente do endpoint (stocks ou fii).
    """
    rows: list[_DividendRow] = []
    for item in raw_items:
        # ex_date: lastDatePrior (stocks) ou exDate (fii) ou approvedOn
        ex_str = (
            item.get("lastDatePrior")
            or item.get("exDate")
            or item.get("ex_date")
            or item.get("approvedOn")
            or ""
        )
        # payment_date: paymentDate ou paidAt
        pay_str = (
            item.get("paymentDate")
            or item.get("paidAt")
            or item.get("payment_date")
            or ""
        )
        # value: rate (stocks) ou value (fii)
        raw_val = item.get("rate") or item.get("value") or item.get("amount") or 0
        # type: type ou dividendType
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
    """
    Busca historico de proventos para ACAO, BDR e ETF_NACIONAL via
    GET /api/v2/stocks/dividends?symbols=TICK1,TICK2,...

    Aceita ate BRAPI_DIVIDENDS_CHUNK (20) tickers por chamada.
    Retorna { ticker_upper: [DividendRow, ...] }.
    Tickers sem proventos retornam lista vazia.
    """
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
                        "[brapi] fetch_stocks_dividends_batch: sem autorizacao "
                        "(plano BRAPI pode nao incluir dividends) — chunk=%s", chunk
                    )
                    continue
                resp.raise_for_status()
                data = resp.json()

                # Resposta esperada: { results: [{ symbol, dividends: [...] }, ...] }
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
                        "[brapi] fetch_stocks_dividends_batch: %s — %d proventos",
                        symbol, len(parsed),
                    )

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[brapi] fetch_stocks_dividends_batch HTTP %s no chunk %s: %s",
                    e.response.status_code, chunk, e,
                )
            except Exception as e:
                logger.warning(
                    "[brapi] fetch_stocks_dividends_batch erro no chunk %s: %s",
                    chunk, e,
                )

    return results


async def fetch_fii_dividends_batch(
    tickers: list[str],
) -> dict[str, list[_DividendRow]]:
    """
    Busca historico de proventos para FII via
    GET /api/v2/fii/dividends?symbols=FII1,FII2,...

    Aceita ate BRAPI_DIVIDENDS_CHUNK (20) tickers por chamada.
    Retorna { ticker_upper: [DividendRow, ...] }.
    Tickers sem proventos retornam lista vazia.
    """
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
                        "[brapi] fetch_fii_dividends_batch: sem autorizacao "
                        "(plano BRAPI pode nao incluir dividends) — chunk=%s", chunk
                    )
                    continue
                resp.raise_for_status()
                data = resp.json()

                # Resposta esperada: { results: [{ symbol, dividends: [...] }, ...] }
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
                        "[brapi] fetch_fii_dividends_batch: %s — %d proventos",
                        symbol, len(parsed),
                    )

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[brapi] fetch_fii_dividends_batch HTTP %s no chunk %s: %s",
                    e.response.status_code, chunk, e,
                )
            except Exception as e:
                logger.warning(
                    "[brapi] fetch_fii_dividends_batch erro no chunk %s: %s",
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


# ── Cripto ─────────────────────────────────────────────────────────────────────────────────

async def fetch_crypto_quote(tickers: list[str]) -> dict[str, float]:
    """
    Busca cotacao de criptomoedas via /api/v2/crypto.
    Normaliza tickers usando _normalize_crypto_ticker (mapa + sufixos).
    Retorna resultado indexado pelo ticker ORIGINAL.
    """
    if not tickers:
        return {}

    headers = _auth_headers()
    results: dict[str, float] = {}

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
                    price_f = float(price)
                    for original in norm_map.get(symbol, []):
                        results[original] = price_f
                        logger.debug(
                            "[brapi] fetch_crypto_quote: %s <- %s = %.4f",
                            original, symbol, price_f,
                        )
                    results[symbol] = price_f
    except Exception as e:
        logger.warning(f"BRAPI fetch_crypto_quote error for {tickers}: {e}")

    missing = [t for t in tickers if t not in results]
    if missing:
        logger.warning(
            "[brapi] fetch_crypto_quote: sem cotacao para %s (codigos: %s)",
            missing,
            [_normalize_crypto_ticker(t) for t in missing],
        )

    return results


# ── Informações do ativo ──────────────────────────────────────────────────────────────────

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


# ── Tesouro Direto ──────────────────────────────────────────────────────────────────────────

async def fetch_treasury_list() -> list[dict]:
    """
    Lista os titulos disponiveis no Tesouro Direto via /api/v2/treasury/list.
    Usado para popular o catalogo dinamico (_load_treasury_catalog).
    Campo correto de identificacao: 'symbol' (nao 'slug').
    """
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


async def fetch_treasury_indicators() -> list[dict]:
    """
    Busca precos e taxas atuais de todos os titulos do Tesouro Direto.

    Estrategia em 3 tentativas:
      1. /api/v2/treasury/indicators — disponivel apenas com token BRAPI valido (plano pago).
         Tentado SOMENTE se BRAPI_TOKEN estiver configurado.
         Se retornar 400/401/403, cai imediatamente no proximo fallback.
      2. /api/v2/treasury/list — endpoint publico gratuito que retorna
         buyPrice/sellPrice por symbol. Sempre tentado como primeiro fallback.
      3. api.radaropcoes.com — fallback externo gratuito com dados em tempo real
         do Tesouro Direto. Usado quando BRAPI nao responde ou retorna lista vazia.

    Retorna lista de dicts com pelo menos:
      { "symbol": "tesouro-selic-01032031", "buyPrice": 14312.50, ... }
    """
    headers = _auth_headers()

    # Tentativa 1: /indicators — somente se token configurado e valido
    if settings.BRAPI_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{BRAPI_BASE}/v2/treasury/indicators",
                    headers=headers,
                )
                if resp.status_code not in (400, 401, 403):
                    resp.raise_for_status()
                    data  = resp.json()
                    items = (
                        data.get("treasuries")
                        or data.get("indicators")
                        or data.get("data")
                        or data.get("results")
                        or (data if isinstance(data, list) else [])
                    )
                    if items:
                        logger.info(
                            "[treasury] fetch_treasury_indicators (/indicators): %d titulos",
                            len(items),
                        )
                        return items if isinstance(items, list) else []
                else:
                    logger.warning(
                        "[treasury] /indicators retornou %d (token invalido/expirado) — usando fallback",
                        resp.status_code,
                    )
        except Exception as e:
            logger.warning("[treasury] fetch_treasury_indicators (/indicators) error: %s", e)

    # Tentativa 2: /list — disponivel no plano free, sem token
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/treasury/list",
                headers=headers,
            )
            resp.raise_for_status()
            data  = resp.json()
            items = (
                data.get("treasuries")
                or data.get("data")
                or data.get("results")
                or (data if isinstance(data, list) else [])
            )
            if items and isinstance(items, list):
                logger.info(
                    "[treasury] fetch_treasury_indicators (/list): %d titulos",
                    len(items),
                )
                return items
    except Exception as e:
        logger.warning("[treasury] fetch_treasury_indicators (/list) error: %s", e)

    # Tentativa 3: Radar Opcoes — fallback externo gratuito
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://api.radaropcoes.com/tesouro-direto")
            resp.raise_for_status()
            data = resp.json()
            # Normaliza para o formato interno { symbol, buyPrice, sellPrice, annualRate }
            raw_items = (
                data.get("data")
                or data.get("treasuries")
                or data.get("results")
                or (data if isinstance(data, list) else [])
            )
            items = []
            for item in raw_items:
                symbol = (
                    item.get("symbol")
                    or item.get("slug")
                    or item.get("name")
                    or ""
                ).strip()
                buy_price = (
                    item.get("buyPrice")
                    or item.get("buy_price")
                    or item.get("preco_compra")
                    or item.get("price")
                )
                if symbol and buy_price is not None:
                    items.append({
                        "symbol":     symbol,
                        "buyPrice":   float(buy_price),
                        "sellPrice":  item.get("sellPrice") or item.get("sell_price"),
                        "annualRate": item.get("annualRate") or item.get("taxa"),
                    })
            if items:
                logger.info(
                    "[treasury] fetch_treasury_indicators (radaropcoes): %d titulos",
                    len(items),
                )
                return items
    except Exception as e:
        logger.warning("[treasury] fetch_treasury_indicators (radaropcoes) error: %s", e)

    logger.warning("[treasury] fetch_treasury_indicators: todos os fallbacks falharam")
    return []


async def fetch_treasury_prices(tickers: list[str]) -> dict[str, float]:
    """
    Busca o preco atual (buyPrice) para uma lista de tickers de Tesouro Direto.

    Fluxo de 4 camadas:
      Camada 1 — Mapa estatico _TREASURY_NAME_MAP (ex: 'Tesouro Selic 2031' -> slug)
      Camada 2 — Slug ja no formato correto (passagem direta)
      Camada 3 — Fallback dinamico via catalogo /v2/treasury/list (titulos novos na BRAPI)
      Camada 4 — Fallback API publica do Tesouro Nacional (titulos ausentes da BRAPI)

    Retorna { ticker_original: preco_float }.
    """
    if not tickers:
        return {}

    # Carrega catalogo dinamico (Camada 3) — cached 6h
    catalog = await _load_treasury_catalog()

    # Mapa: slug_brapi -> [tickers_originais]
    slug_map: dict[str, list[str]] = {}
    for t in tickers:
        slug = _normalize_treasury_ticker(t, catalog=catalog)
        slug_map.setdefault(slug, []).append(t)

    # Busca todos os indicadores de uma vez (1 request para N titulos)
    indicators = await fetch_treasury_indicators()

    # Constroi price_map: symbol_brapi -> buyPrice
    price_map: dict[str, float] = {}
    for item in indicators:
        symbol = (
            item.get("symbol")
            or item.get("slug")
            or item.get("name")
            or ""
        ).strip()
        price = (
            item.get("buyPrice")
            or item.get("regularMarketPrice")
            or item.get("price")
            or item.get("basePrice")
        )
        if symbol and price is not None:
            try:
                price_map[symbol] = float(price)
                price_map[_slug_from_raw(symbol)] = float(price)
            except (ValueError, TypeError):
                pass

    # Propaga precos para os tickers originais
    results: dict[str, float] = {}
    for slug, originals in slug_map.items():
        price = price_map.get(slug) or price_map.get(_slug_from_raw(slug))
        if price is not None:
            for original in originals:
                results[original] = price
                logger.debug(
                    "[treasury] fetch_treasury_prices: %s <- %s = %.2f",
                    original, slug, price,
                )
        else:
            logger.warning(
                "[treasury] fetch_treasury_prices: sem preco BRAPI para ticker=%r slug=%r",
                originals, slug,
            )

    # ── Camada 4: fallback API publica do Tesouro Nacional ─────────────────────────────────
    missing = [t for t in tickers if t not in results]
    if missing:
        logger.info(
            "[treasury] Camada 4 (TN fallback) para %d tickers: %s",
            len(missing), missing,
        )
        try:
            from app.integrations.tesouro_nacional import fetch_tn_prices
            tn_prices = await fetch_tn_prices(missing)
            for ticker, price in tn_prices.items():
                results[ticker] = price
                logger.info(
                    "[treasury] Camada 4 (TN): %r = %.2f", ticker, price
                )
        except Exception as e:
            logger.warning("[treasury] Camada 4 (TN) erro: %s", e)

    still_missing = [t for t in tickers if t not in results]
    if still_missing:
        logger.warning(
            "[treasury] fetch_treasury_prices: %d tickers sem preco apos todas as camadas: %s",
            len(still_missing), still_missing,
        )

    return results


async def fetch_treasury_price_by_date(slug: str, date_str: str) -> Optional[float]:
    """
    Busca o preco historico de um titulo do Tesouro Direto para uma data especifica.
    Normaliza o slug usando as 3 camadas antes de chamar a API.
    Fallback para API do Tesouro Nacional se BRAPI nao retornar resultado.
    """
    catalog = await _load_treasury_catalog()
    resolved_slug = _normalize_treasury_ticker(slug, catalog=catalog)
    headers = _auth_headers()
    try:
        ref_date  = date.fromisoformat(date_str)
        date_from = (ref_date - timedelta(days=5)).isoformat()
        date_to   = date_str
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BRAPI_BASE}/v2/treasury/{resolved_slug}/historical",
                headers=headers,
                params={"startDate": date_from, "endDate": date_to},
            )
            resp.raise_for_status()
            data  = resp.json()
            hist  = (
                data.get("historical")
                or data.get("prices")
                or data.get("data")
                or []
            )
            if hist:
                last  = hist[-1]
                price = (
                    last.get("buyPrice")
                    or last.get("price")
                    or last.get("basePrice")
                    or last.get("regularMarketPrice")
                )
                if price:
                    return float(price)
    except Exception as e:
        logger.warning(f"[treasury] fetch_treasury_price_by_date BRAPI error for {resolved_slug!r} on {date_str}: {e}")

    # Fallback Tesouro Nacional para preco historico
    try:
        from app.integrations.tesouro_nacional import fetch_tn_price_by_date
        tn_price = await fetch_tn_price_by_date(slug, date_str)
        if tn_price:
            logger.info(
                "[treasury] fetch_treasury_price_by_date TN fallback: %r em %s = %.2f",
                slug, date_str, tn_price,
            )
            return tn_price
    except Exception as e:
        logger.warning("[treasury] fetch_treasury_price_by_date TN fallback erro: %s", e)

    return None


# ── Busca / sugestões de ticker ───────────────────────────────────────────────────────────────

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
