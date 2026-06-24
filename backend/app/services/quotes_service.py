"""
Servico unificado de cotacoes.

Estrategia de cache em 3 camadas:
  L1 - Asset.last_price no banco (TTL = PRICE_TTL_SECONDS).
  L2 - Cache em memoria processo (TTL = MEM_CACHE_TTL).
  L3 - API externa: BRAPI Pro, Alpha Vantage ou yfinance.

Roteamento por tipo de ativo:
  BR / FII / ETF_BR  -> BRAPI quotes
  CRIPTO             -> BRAPI crypto
  TESOURO            -> BRAPI treasury list (buyPrice)
  INTL               -> Alpha Vantage GLOBAL_QUOTE (primario)
                        yfinance (fallback se AV falhar ou nao configurado)

Alpha Vantage (ativos internacionais):
  - Primario para INTL_TYPES (substitui yfinance no caminho quente)
  - Rate limiter: alpha_vantage_limiter (4 req/min, burst 4)
  - Se ALPHA_VANTAGE_API_KEY nao estiver configurada, cai direto no yfinance

yfinance threading:
  _fetch_yfinance_current usa _YF_EXECUTOR (ThreadPoolExecutor compartilhado)
  com _yf_thread_lock (threading.Lock) para serializar chamadas entre threads.

Resiliencia:
  Cada chamada externa e envolta em _with_retry() - 3 tentativas.
  YFRateLimitError usa backoff longo (20s, 40s) pois o rate limit do
  yfinance precisa de tempo real para se recuperar.
  Outras excecoes usam backoff curto (1s, 2s).

BRAPI - tickers fracionarios:
  Tickers com sufixo F (ex: PETR4F, ABCB4F) sao direitos de subscricao
  fracionarios da B3 e NAO sao suportados pela BRAPI para cotacao.
  _filter_brapi_tickers() os remove antes de montar o chunk evitando
  erros 400 em massa durante o seed e update_all_quotes.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import BR_TYPES, INTL_TYPES, NO_QUOTE_TYPES, TREASURY_TYPES, yf_ticker
from app.core.rate_limiter import brapi_limiter, alpha_vantage_limiter
from app.integrations.brapi import (
    fetch_quotes as brapi_fetch_quotes,
    fetch_crypto_quote as brapi_fetch_crypto,
    fetch_treasury_list as brapi_fetch_treasury_list,
)
from app.models.asset import Asset, AssetType
from app.services.price_history_service import _YF_EXECUTOR, _yf_thread_lock, _YF_MIN_INTERVAL, _yf_last_call

logger = logging.getLogger(__name__)

PRICE_TTL_SECONDS = 900
MEM_CACHE_TTL = 300  # 5 minutos (era 60s) - reduz frequencia de chamadas ao yfinance

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0
_RETRY_RATELIMIT_DELAY = 20.0  # backoff inicial para YFRateLimitError

_mem_cache: dict[str, tuple[float, float]] = {}


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

async def _with_retry(coro_fn, *args, label: str = "") -> dict[str, float]:
    """
    Executa coro_fn com retry e backoff.
    YFRateLimitError usa backoff longo (20s, 40s) pois o yfinance
    precisa de tempo real para liberar o rate limit.
    Outras excecoes usam backoff curto (1s, 2s).
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return await coro_fn(*args)
        except Exception as e:
            is_rate_limit = "ratelimit" in type(e).__name__.lower() or "rate limit" in str(e).lower() or "too many requests" in str(e).lower()
            if attempt < _RETRY_ATTEMPTS:
                actual_delay = _RETRY_RATELIMIT_DELAY * (2 ** (attempt - 1)) if is_rate_limit else delay
                logger.warning(
                    "[quotes_service] %s tentativa %d/%d falhou%s: %s - retry em %.0fs",
                    label, attempt, _RETRY_ATTEMPTS,
                    " (rate limit)" if is_rate_limit else "",
                    e, actual_delay,
                )
                await asyncio.sleep(actual_delay)
                delay *= 2
            else:
                logger.error(
                    "[quotes_service] %s todas as tentativas esgotadas: %s",
                    label, e,
                )
    return {}


# ---------------------------------------------------------------------------
# Cache L1 / L2
# ---------------------------------------------------------------------------

def _mem_get(ticker: str) -> Optional[float]:
    entry = _mem_cache.get(ticker)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _mem_set(ticker: str, price: float) -> None:
    _mem_cache[ticker] = (price, time.time() + MEM_CACHE_TTL)


def _asset_type_str(asset_type) -> str:
    if isinstance(asset_type, AssetType):
        return asset_type.value
    return str(asset_type)


async def _db_get_fresh(
    db: AsyncSession,
    ticker: str,
    asset_type,
) -> Optional[float]:
    at_str = _asset_type_str(asset_type)
    result = await db.execute(
        select(Asset.last_price, Asset.last_price_updated_at)
        .where(
            Asset.ticker == ticker,
            Asset.asset_type == at_str,
        )
    )
    row = result.first()
    if not row or row.last_price is None or row.last_price_updated_at is None:
        return None
    age = (datetime.now(timezone.utc) - row.last_price_updated_at).total_seconds()
    if age <= PRICE_TTL_SECONDS:
        return float(row.last_price)
    return None


async def _db_set(
    db: AsyncSession,
    ticker: str,
    asset_type,
    price: float,
) -> None:
    at_str = _asset_type_str(asset_type)
    try:
        async with db.begin_nested():
            result = await db.execute(
                select(Asset).where(
                    Asset.ticker == ticker,
                    Asset.asset_type == at_str,
                )
            )
            asset = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            price_decimal = Decimal(str(round(price, 8)))

            if asset:
                asset.last_price = price_decimal
                asset.last_price_updated_at = now
            else:
                asset = Asset(
                    ticker=ticker,
                    asset_type=at_str,
                    last_price=price_decimal,
                    last_price_updated_at=now,
                )
                db.add(asset)
                logger.info(
                    "[quotes_service] Asset criado automaticamente via upsert: %s (%s)",
                    ticker, at_str,
                )
    except Exception as e:
        logger.warning(
            "[quotes_service] _db_set savepoint falhou para %s (%s): %s",
            ticker, at_str, e,
        )


# ---------------------------------------------------------------------------
# Filtro BRAPI - remove tickers fracionarios (sufixo F)
# ---------------------------------------------------------------------------

def _filter_brapi_tickers(tickers: list[str]) -> list[str]:
    """
    Remove tickers com sufixo F (direitos de subscricao fracionarios da B3).
    A BRAPI nao suporta esses tickers para cotacao e retorna 400.
    """
    return [t for t in tickers if not t.endswith('F')]


# ---------------------------------------------------------------------------
# Fetch L3 - Alpha Vantage (INTL primario)
# ---------------------------------------------------------------------------

async def _fetch_alpha_vantage_current(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    from app.integrations.alpha_vantage import fetch_global_quote, _is_configured

    if not _is_configured():
        return {}

    results: dict[str, float] = {}
    for ticker, _ in pairs:
        await alpha_vantage_limiter.acquire()
        price = await fetch_global_quote(ticker)
        if price is not None:
            results[ticker] = price
    return results


# ---------------------------------------------------------------------------
# Fetch L3 - yfinance (fallback para INTL e BR sem BRAPI)
# ---------------------------------------------------------------------------

def _fetch_yf_current_sync(ticker_map: dict[str, str]) -> dict[str, float]:
    """
    Busca cotacoes atuais via yfinance.download().
    Usa _yf_thread_lock compartilhado com price_history_service para
    serializar todas as chamadas yfinance do processo.
    Respeita _YF_MIN_INTERVAL global entre chamadas.
    """
    import time as _time

    if not ticker_map:
        return {}
    yf_syms = list(ticker_map.values())
    results: dict[str, float] = {}

    with _yf_thread_lock:
        # Garante intervalo minimo desde a ultima chamada yfinance (qualquer origem)
        elapsed = _time.monotonic() - _yf_last_call[0]
        if elapsed < _YF_MIN_INTERVAL:
            _time.sleep(_YF_MIN_INTERVAL - elapsed)
        try:
            data = yf.download(
                tickers=yf_syms,
                period="1d",
                interval="1m",
                progress=False,
                auto_adjust=True,
            )
            _yf_last_call[0] = _time.monotonic()

            if data.empty:
                return {}

            is_multi = hasattr(data.columns, 'levels')

            for internal, sym in ticker_map.items():
                try:
                    if is_multi:
                        col = ("Close", sym)
                        if col not in data.columns:
                            continue
                        series = data[col].dropna()
                    else:
                        if "Close" not in data.columns:
                            continue
                        series = data["Close"].dropna()

                    if series.empty:
                        continue
                    results[internal] = float(series.iloc[-1])
                except Exception as e:
                    logger.warning(f"yfinance preco nao encontrado para {sym}: {e}")
        except Exception as e:
            logger.error(f"yfinance download error: {e}")
            _yf_last_call[0] = _time.monotonic()

    return results


async def _fetch_yfinance_current(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    ticker_map = {t: yf_ticker(t, at) for t, at in pairs}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_YF_EXECUTOR, _fetch_yf_current_sync, ticker_map)


# ---------------------------------------------------------------------------
# Fetch Tesouro Direto
# ---------------------------------------------------------------------------

async def _fetch_treasury_prices(slugs: list[str]) -> dict[str, float]:
    if not slugs:
        return {}
    try:
        items = await brapi_fetch_treasury_list() or []
    except Exception as e:
        logger.warning(f"[quotes_service] fetch_treasury_list falhou: {e}")
        return {}

    price_map: dict[str, float] = {}
    for item in items:
        api_slug = (item.get("slug") or "").strip().lower()
        api_name = (item.get("bondType") or item.get("name") or "").strip().lower()
        price = item.get("buyPrice") or item.get("basePrice") or item.get("sellPrice")
        if price is None:
            continue
        p = float(price)
        if api_slug:
            price_map[api_slug] = p
        if api_name:
            price_map[api_name] = p

    results: dict[str, float] = {}
    for slug in slugs:
        key = slug.strip().lower()
        if key in price_map:
            results[slug] = price_map[key]
        else:
            logger.warning(f"[quotes_service] Tesouro slug sem cotacao BRAPI: {slug!r}")
    return results


# ---------------------------------------------------------------------------
# Aliases com rate limit + retry
# ---------------------------------------------------------------------------

async def _fetch_brapi(tickers: list[str]) -> dict[str, float]:
    filtered = _filter_brapi_tickers(tickers)
    if not filtered:
        return {}
    skipped = len(tickers) - len(filtered)
    if skipped:
        logger.debug("[quotes_service] BRAPI: %d tickers fracionarios ignorados", skipped)
    await brapi_limiter.acquire()
    return await _with_retry(brapi_fetch_quotes, filtered, label="BRAPI")


async def _fetch_brapi_crypto(tickers: list[str]) -> dict[str, float]:
    await brapi_limiter.acquire()
    return await _with_retry(brapi_fetch_crypto, tickers, label="BRAPI-crypto")


async def _fetch_intl(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    """
    Cotacao atual para ativos INTL:
      1. Alpha Vantage (primario, se API key configurada)
      2. yfinance (fallback)
    Tickers sem resultado no AV sao complementados pelo yfinance.
    """
    av_results = await _fetch_alpha_vantage_current(pairs)

    missing = [(t, at) for t, at in pairs if t not in av_results]
    yf_results: dict[str, float] = {}
    if missing:
        if av_results:
            logger.info(
                "[quotes_service] %d tickers INTL sem resultado no AV — complementando com yfinance: %s",
                len(missing), [t for t, _ in missing],
            )
        else:
            logger.info("[quotes_service] AV nao configurado/vazio — usando yfinance para INTL")
        yf_results = await _with_retry(_fetch_yfinance_current, missing, label="yfinance-intl")

    return {**av_results, **yf_results}


async def _fetch_yfinance(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    """Fallback yfinance para BR sem BRAPI."""
    return await _with_retry(_fetch_yfinance_current, pairs, label="yfinance")


async def _noop() -> dict:
    return {}


# ---------------------------------------------------------------------------
# get_prices - orquestrador principal
# ---------------------------------------------------------------------------

async def get_prices(
    positions: list[dict],
    db: Optional[AsyncSession] = None,
) -> dict[str, float]:
    br_tickers: list[str] = []
    crypto_tickers: list[str] = []
    intl_pairs: list[tuple[str, AssetType]] = []
    treasury_slugs: list[str] = []
    br_fallback: list[tuple[str, AssetType]] = []
    resolved: dict[str, float] = {}
    type_map: dict[str, AssetType | None] = {}

    for p in positions:
        ticker = p["ticker"]
        raw_type = p.get("asset_type", "")
        try:
            asset_type = AssetType(raw_type) if isinstance(raw_type, str) else raw_type
        except ValueError:
            asset_type = None
            logger.warning(
                "[quotes_service] asset_type invalido '%s' para %s",
                raw_type, ticker,
            )

        type_map[ticker] = asset_type

        if asset_type in NO_QUOTE_TYPES:
            continue

        mem_val = _mem_get(ticker)
        if mem_val is not None:
            resolved[ticker] = mem_val
            continue

        if db and asset_type:
            db_val = await _db_get_fresh(db, ticker, asset_type)
            if db_val is not None:
                resolved[ticker] = db_val
                _mem_set(ticker, db_val)
                continue

        if asset_type in TREASURY_TYPES:
            treasury_slugs.append(ticker)
        elif asset_type == AssetType.CRIPTO:
            crypto_tickers.append(ticker)
        elif asset_type in BR_TYPES:
            br_tickers.append(ticker)
        elif asset_type in INTL_TYPES:
            intl_pairs.append((ticker, asset_type))
        else:
            logger.warning(f"[quotes_service] asset_type desconhecido para {ticker} ({raw_type})")
            br_tickers.append(ticker)

    br_results, crypto_results, intl_results, treasury_results = await asyncio.gather(
        _fetch_brapi(br_tickers) if br_tickers else _noop(),
        _fetch_brapi_crypto(crypto_tickers) if crypto_tickers else _noop(),
        _fetch_intl(intl_pairs) if intl_pairs else _noop(),
        _fetch_treasury_prices(treasury_slugs) if treasury_slugs else _noop(),
    )

    for p in positions:
        ticker = p["ticker"]
        asset_type = type_map.get(ticker)
        if (
            ticker in br_tickers
            and ticker not in br_results
            and ticker not in resolved
            and asset_type is not None
        ):
            br_fallback.append((ticker, asset_type))

    fallback_results: dict[str, float] = {}
    if br_fallback:
        logger.info(f"[quotes_service] BRAPI sem resposta para {[t for t, _ in br_fallback]} - tentando yfinance")
        fallback_results = await _fetch_yfinance(br_fallback)

    fresh = {**br_results, **crypto_results, **intl_results, **treasury_results, **fallback_results}

    for p in positions:
        ticker = p["ticker"]
        price = fresh.get(ticker)
        if price is None:
            continue
        _mem_set(ticker, price)
        if db:
            asset_type = type_map.get(ticker)
            if asset_type is not None:
                await _db_set(db, ticker, asset_type, price)
            else:
                logger.warning("[quotes_service] asset_type invalido para %s", ticker)

    return {**resolved, **fresh}


async def get_current_price(
    ticker: str,
    asset_type: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Optional[float]:
    if asset_type is None:
        logger.warning(f"[quotes_service] get_current_price sem asset_type para {ticker}")
        return None
    result = await get_prices([{"ticker": ticker, "asset_type": asset_type}], db)
    return result.get(ticker)


async def update_all_quotes(db: AsyncSession) -> int:
    from app.models.transaction import Transaction

    asset_result = await db.execute(
        select(Asset.ticker, Asset.asset_type).where(
            Asset.asset_type.notin_([at.value for at in NO_QUOTE_TYPES])
        )
    )
    asset_rows = asset_result.all()

    tx_result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type).distinct()
    )
    tx_rows = tx_result.all()

    positions_map: dict[tuple[str, str], dict] = {
        (r.ticker, str(r.asset_type)): {"ticker": r.ticker, "asset_type": str(r.asset_type)}
        for r in asset_rows
    }
    for row in tx_rows:
        if not row.ticker or not row.asset_type:
            continue
        key = (row.ticker, str(row.asset_type))
        try:
            at = AssetType(str(row.asset_type))
            if at in NO_QUOTE_TYPES:
                continue
        except ValueError:
            pass
        if key not in positions_map:
            positions_map[key] = {"ticker": row.ticker, "asset_type": str(row.asset_type)}

    positions = list(positions_map.values())
    if not positions:
        return 0

    prices = await get_prices(positions, db)
    await db.commit()
    logger.info("[quotes_service] update_all_quotes: %d precos atualizados", len(prices))
    return len(prices)


async def update_quotes_for_portfolio(
    portfolio_id: int,
    db: AsyncSession,
) -> int:
    from app.models.transaction import Transaction

    result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    rows = result.all()
    if not rows:
        return 0

    positions_payload = [
        {"ticker": r.ticker, "asset_type": r.asset_type}
        for r in rows if r.ticker
    ]

    quotes = await get_prices(positions_payload, db=db)
    await db.commit()

    updated = sum(1 for r in rows if r.ticker in quotes)
    logger.info(
        "[quotes_service] Portfolio %d: %d/%d ativos com cotacao atualizada",
        portfolio_id, updated, len(rows),
    )
    return updated


async def get_price_for_transaction(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    date_str: str,
) -> float | None:
    from app.services.price_history_service import get_price_at_date
    try:
        return await get_price_at_date(db, ticker, asset_type, date_str)
    except Exception as e:
        logger.warning(
            "[quotes_service] get_price_for_transaction falhou para %s em %s: %s",
            ticker, date_str, e,
        )
        return None
