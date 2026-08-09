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
