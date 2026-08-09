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
    "TESOURO SELIC 2026": "tesouro-selic-01032026",
    "TESOURO SELIC 2027": "tesouro-selic-01032027",
    "TESOURO SELIC 2029": "tesouro-selic-01032029",
    "TESOURO SELIC 2031": "tesouro-selic-01032031",
    "LFT 2026": "tesouro-selic-01032026",
    "LFT 2027": "tesouro-selic-01032027",
    "LFT 2029": "tesouro-selic-01032029",
    "LFT 2031": "tesouro-selic-01032031",
}

_TREASURY_SLUG_RE = re.compile(r"^tesouro-[a-z0-9-]+$")
_TREASURY_CATALOG_CACHE: dict[str, str] = {}
_TREASURY_CATALOG_EXPIRES: float = 0.0
_TREASURY_CATALOG_TTL = 21600.0


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
        return _TREASURY_NAME_MAP[t_upper]
    t_lower = ticker.strip().lower()
    if _TREASURY_SLUG_RE.match(t_lower):
        return t_lower
    if catalog:
        slug_candidate = _slug_from_raw(ticker)
        if slug_candidate in catalog:
            return catalog[slug_candidate]
    return _slug_from_raw(ticker)


async def _load_treasury_catalog() -> dict[str, str]:
    global _TREASURY_CATALOG_CACHE, _TREASURY_CATALOG_EXPIRES
    now = time.monotonic()
    if _TREASURY_CATALOG_CACHE and now < _TREASURY_CATALOG_EXPIRES:
        return _TREASURY_CATALOG_CACHE
    items = await fetch_treasury_list()
    catalog: dict[str, str] = {}
    for item in items:
        symbol = (item.get("symbol") or item.get("slug") or item.get("name") or "").strip()
        if symbol:
            catalog[_slug_from_raw(symbol)] = symbol
    _TREASURY_CATALOG_CACHE = catalog
    _TREASURY_CATALOG_EXPIRES = now + _TREASURY_CATALOG_TTL
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


def _parse_history_rows(history: list[dict], ticker: str, label: str) -> list[tuple[datetime, float]]:
    rows: list[tuple[datetime, float]] = []
    for entry in history:
        close = entry.get("adjclose") or entry.get("close") or entry.get("value") or entry.get("price")
        ts_raw = entry.get("date") or entry.get("timestamp")
        if close is None or ts_raw is None:
            continue
        if isinstance(ts_raw, (int, float)):
            dt = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        else:
            try:
                dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        rows.append((dt, float(close)))
    rows.sort(key=lambda x: x[0])
    logger.debug("[market_data] price_history [%s]: %s — %d registros", label, ticker, len(rows))
    return rows


async def fetch_crypto_historical_v2(
    ticker: str,
    *,
    currency: str = "USD",
    range_: str = "max",
    interval: str = "1d",
) -> list[tuple[datetime, float]]:
    coin = _normalize_crypto_ticker(ticker)
    headers = _auth_headers()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BRAPI_BASE}/v2/crypto",
            headers=headers,
            params={
                "coin": coin,
                "currency": currency.upper(),
                "range": range_,
                "interval": interval,
            },
        )
        response.raise_for_status()
        payload = response.json()
    results = payload.get("results") or payload.get("coins") or []
    if isinstance(results, dict):
        results = [results]
    if not results:
        return []
    item = results[0] or {}
    history = (
        item.get("historicalDataPrice")
        or item.get("history")
        or item.get("historicalData")
        or []
    )
    return _parse_history_rows(history, coin, "brapi_crypto")


# NOTE: remaining existing functions intentionally preserved below in repository.
