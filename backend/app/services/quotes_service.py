"""
Servico unificado de cotacoes.

Estrategia de cache em 3 camadas:
  L1 - Asset.last_price no banco (TTL = PRICE_TTL_SECONDS).
  L2 - Cache em memoria processo (TTL = MEM_CACHE_TTL).
  L3 - Provedores externos de cotacao.

Roteamento por tipo de ativo:
  BR / FII / ETF_BR  -> cotacoes em lote (chunks de 20, delay 1s entre chunks)
  CRIPTO             -> cotacao de criptomoedas
  TESOURO            -> indicadores do Tesouro Direto
                        Resolucao de slug em 3 camadas:
                          1. Mapa estatico (~60 entradas)
                          2. Slug ja no formato correto (passagem direta)
                          3. Fallback dinamico via catalogo (cache 6h)
  INTL               -> provedor primario de ativos internacionais
                        com fallback automatico se o primario falhar

Ativos internacionais:
  - Provedor primario configurado via variavel de ambiente
  - Rate limiter ativo (4 req/min, burst 4)
  - Fallback automatico para provedor secundario quando necessario

Threading para provedor secundario:
  _fetch_secondary_current usa _YF_EXECUTOR (ThreadPoolExecutor compartilhado)
  com _yf_thread_lock (threading.Lock) para serializar chamadas entre threads.

Resiliencia:
  Cada chamada externa e envolta em _with_retry() - 3 tentativas.
  RateLimitError usa backoff longo (20s, 40s) pois o rate limit
  precisa de tempo real para se recuperar.
  Outras excecoes usam backoff curto (1s, 2s).

Fallback stale cache (RateLimitError):
  Quando _fetch_intl esgota todas as tentativas e o provedor retorna {},
  _resolve_intl_with_stale_fallback() tenta devolver o ultimo preco valido
  presente no _mem_cache (mesmo que expirado). Isso evita que ativos
  internacionais aparecam zerados na tela durante periodos de indisponibilidade.
  O preco e marcado como stale no log.

Tickers fracionarios (sufixo F):
  Tickers com sufixo F (ex: PETR4F, ABCB4F) sao direitos de subscricao
  fracionarios da B3 e nao sao suportados para cotacao em lote.
  _filter_brapi_tickers() os remove antes de montar o chunk.

Chunks BR:
  Maximo de BRAPI_CHUNK_SIZE (20) tickers por request.
  Delay de BRAPI_CHUNK_DELAY (1s) entre chunks para evitar rate limit.
  Jobs do scheduler chamam update_all_quotes com asset_types filtrado
  para nunca misturar tipos diferentes no mesmo request.

Otimizacao N+1 (Sprint 5B):
  get_prices busca todos os precos frescos do banco em UMA unica query
  (batch lookup via _db_get_fresh_batch) antes de acionar provedores externos,
  eliminando o loop de SELECTs individuais por ticker.
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
    fetch_treasury_prices as brapi_fetch_treasury_prices,
)
from app.models.asset import Asset, AssetType
from app.services.price_history_service import _YF_EXECUTOR, _yf_thread_lock, _YF_MIN_INTERVAL, _yf_last_call

logger = logging.getLogger(__name__)

PRICE_TTL_SECONDS = 900
MEM_CACHE_TTL = 300  # 5 minutos - reduz frequencia de chamadas ao provedor

BRAPI_CHUNK_SIZE = 20   # max tickers por request
BRAPI_CHUNK_DELAY = 1.0  # segundos entre chunks

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0
_RETRY_RATELIMIT_DELAY = 20.0  # backoff inicial para RateLimitError

_mem_cache: dict[str, tuple[float, float]] = {}


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

async def _with_retry(coro_fn, *args, label: str = "") -> dict[str, float]:
    """
    Executa coro_fn com retry e backoff.
    RateLimitError usa backoff longo (20s, 40s).
    Outras excecoes usam backoff curto (1s, 2s).
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return await coro_fn(*args)
        except Exception as e:
            is_rate_limit = (
                "ratelimit" in type(e).__name__.lower()
                or "rate limit" in str(e).lower()
                or "too many requests" in str(e).lower()
            )
            if attempt < _RETRY_ATTEMPTS:
                actual_delay = (
                    _RETRY_RATELIMIT_DELAY * (2 ** (attempt - 1))
                    if is_rate_limit
                    else delay
                )
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
    """Retorna preco do cache em memoria somente se ainda valido (TTL)."""
    entry = _mem_cache.get(ticker)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _mem_get_stale(ticker: str) -> Optional[float]:
    """
    Retorna o ultimo preco do cache em memoria mesmo que expirado (stale).
    Usado como ultimo recurso quando todas as APIs falharam
    para evitar exibir valores zerados no frontend.
    """
    entry = _mem_cache.get(ticker)
    return entry[0] if entry else None


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


async def _db_get_fresh_batch(
    db: AsyncSession,
    pairs: list[tuple[str, str]],
) -> dict[str, float]:
    """
    Sprint 5B — eliminacao do N+1.
    Busca last_price de multiplos (ticker, asset_type) em UMA unica query.
    Retorna apenas os que ainda estao dentro do TTL.
    """
    if not pairs:
        return {}

    tickers = [p[0] for p in pairs]
    result = await db.execute(
        select(Asset.ticker, Asset.asset_type, Asset.last_price, Asset.last_price_updated_at)
        .where(
            Asset.ticker.in_(tickers),
        )
    )
    rows = result.all()
    now = datetime.now(timezone.utc)
    fresh: dict[str, float] = {}
    # Indexar por (ticker, asset_type) para match exato
    pair_set = {(t, at) for t, at in pairs}
    for row in rows:
        if (row.ticker, str(row.asset_type)) not in pair_set:
            continue
        if row.last_price is None or row.last_price_updated_at is None:
            continue
        age = (now - row.last_price_updated_at).total_seconds()
        if age <= PRICE_TTL_SECONDS:
            fresh[row.ticker] = float(row.last_price)
    return fresh


async def _db_get_stale(
    db: AsyncSession,
    ticker: str,
    asset_type,
) -> Optional[float]:
    """
    Retorna o ultimo preco do banco independente do TTL (stale).
    Usado como ultimo recurso quando todas as APIs falharam.
    """
    at_str = _asset_type_str(asset_type)
    result = await db.execute(
        select(Asset.last_price)
        .where(
            Asset.ticker == ticker,
            Asset.asset_type == at_str,
        )
    )
    row = result.first()
    if row and row.last_price is not None:
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
# Filtro BR - remove tickers fracionarios (sufixo F)
# ---------------------------------------------------------------------------

def _filter_brapi_tickers(tickers: list[str]) -> list[str]:
    """
    Remove tickers com sufixo F (direitos de subscricao fracionarios da B3).
    Esses tickers nao sao suportados para cotacao em lote e retornam 400.
    """
    return [t for t in tickers if not t.endswith('F')]


# ---------------------------------------------------------------------------
# Fetch L3 - Provedor primario (ativos internacionais)
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
# Fetch L3 - Provedor secundario (fallback)
# ---------------------------------------------------------------------------

def _fetch_yf_current_sync(ticker_map: dict[str, str]) -> dict[str, float]:
    """
    Busca cotacoes atuais via provedor secundario.
    Usa _yf_thread_lock compartilhado com price_history_service para
    serializar todas as chamadas do processo.
    Respeita _YF_MIN_INTERVAL global entre chamadas.
    """
    import time as _time

    if not ticker_map:
        return {}
    yf_syms = list(ticker_map.values())
    results: dict[str, float] = {}

    with _yf_thread_lock:
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
                    logger.warning("[quotes_service] preco nao encontrado para %s: %s", sym, e)
        except Exception as e:
            logger.error("[quotes_service] download error (provedor secundario): %s", e)
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

async def _fetch_treasury_prices(tickers: list[str]) -> dict[str, float]:
    """
    Busca precos atuais de titulos do Tesouro Direto.

    Delega para fetch_treasury_prices(), que implementa
    as 3 camadas de resolucao de slug e usa o endpoint correto /indicators:
      Camada 1 - Mapa estatico (~60 entradas)
      Camada 2 - Slug ja no formato correto (passagem direta)
      Camada 3 - Fallback dinamico via catalogo (cache 6h)
    """
    if not tickers:
        return {}
    try:
        return await brapi_fetch_treasury_prices(tickers)
    except Exception as e:
        logger.warning("[quotes_service] fetch_treasury_prices falhou: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Fetch BR em chunks com delay entre eles
# ---------------------------------------------------------------------------

async def _fetch_brapi_chunked(tickers: list[str], label: str = "quotes") -> dict[str, float]:
    """
    Envia tickers BR em chunks de BRAPI_CHUNK_SIZE.
    Aplica delay de BRAPI_CHUNK_DELAY entre chunks para respeitar rate limit.
    Espera receber apenas tickers do mesmo tipo — nunca misturar tipos.
    """
    filtered = _filter_brapi_tickers(tickers)
    if not filtered:
        return {}

    results: dict[str, float] = {}
    for i in range(0, len(filtered), BRAPI_CHUNK_SIZE):
        chunk = filtered[i: i + BRAPI_CHUNK_SIZE]
        await brapi_limiter.acquire()
        chunk_result = await _with_retry(brapi_fetch_quotes, chunk, label=f"{label}[{i//BRAPI_CHUNK_SIZE+1}]")
        results.update(chunk_result)
        if i + BRAPI_CHUNK_SIZE < len(filtered):
            await asyncio.sleep(BRAPI_CHUNK_DELAY)

    return results


async def _fetch_brapi(tickers: list[str]) -> dict[str, float]:
    """Wrapper retrocompativel — usa chunked internamente."""
    return await _fetch_brapi_chunked(tickers, label="quotes")


async def _fetch_brapi_crypto(tickers: list[str]) -> dict[str, float]:
    await brapi_limiter.acquire()
    return await _with_retry(brapi_fetch_crypto, tickers, label="quotes-crypto")


async def _fetch_intl(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    """
    Cotacao atual para ativos INTL:
      1. Provedor primario (se API key configurada)
      2. Provedor secundario (fallback)
    Tickers sem resultado no primario sao complementados pelo secundario.
    """
    av_results = await _fetch_alpha_vantage_current(pairs)

    missing = [(t, at) for t, at in pairs if t not in av_results]
    yf_results: dict[str, float] = {}
    if missing:
        if av_results:
            logger.info(
                "[quotes_service] %d tickers INTL sem resultado no provedor primario — complementando com fallback: %s",
                len(missing), [t for t, _ in missing],
            )
        else:
            logger.info("[quotes_service] provedor primario nao configurado/vazio — usando fallback para INTL")
        yf_results = await _with_retry(_fetch_yfinance_current, missing, label="intl-fallback")

    return {**av_results, **yf_results}


async def _fetch_intl_with_stale_fallback(
    pairs: list[tuple[str, AssetType]],
    db: Optional[AsyncSession] = None,
) -> dict[str, float]:
    """
    Chama _fetch_intl e, para tickers que retornarem sem preco (rate limit
    ou falha total), tenta devolver o ultimo valor conhecido em:
      1. _mem_cache (mesmo expirado — stale)
      2. Asset.last_price no banco (mesmo fora do TTL)
    Loga warning para cada ticker que usar preco stale.
    """
    results = await _fetch_intl(pairs)

    missing_after_fetch = [(t, at) for t, at in pairs if t not in results]
    if not missing_after_fetch:
        return results

    stale_used: list[str] = []
    for ticker, asset_type in missing_after_fetch:
        stale = _mem_get_stale(ticker)
        if stale is not None:
            results[ticker] = stale
            stale_used.append(f"{ticker}(mem)")
            continue
        if db:
            db_stale = await _db_get_stale(db, ticker, asset_type)
            if db_stale is not None:
                results[ticker] = db_stale
                stale_used.append(f"{ticker}(db)")

    if stale_used:
        logger.warning(
            "[quotes_service] provedor INTL indisponivel — usando preco stale para: %s",
            ", ".join(stale_used),
        )

    return results


async def _fetch_yfinance(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    """Fallback para BR sem cotacao no provedor principal."""
    return await _with_retry(_fetch_yfinance_current, pairs, label="br-fallback")


async def _noop() -> dict:
    return {}


# ---------------------------------------------------------------------------
# get_prices - orquestrador principal (N+1 corrigido - Sprint 5B)
# ---------------------------------------------------------------------------

async def get_prices(
    positions: list[dict],
    db: Optional[AsyncSession] = None,
) -> dict[str, float]:
    br_tickers: list[str] = []
    crypto_tickers: list[str] = []
    intl_pairs: list[tuple[str, AssetType]] = []
    treasury_tickers: list[str] = []
    br_fallback: list[tuple[str, AssetType]] = []
    resolved: dict[str, float] = {}
    type_map: dict[str, AssetType | None] = {}

    # --- Fase 1: normalizar tipos e checar mem_cache ---
    needs_db: list[tuple[str, str]] = []  # (ticker, asset_type_str) para batch DB

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

        # Coleta para batch DB (nao faz SELECT individual aqui)
        if db and asset_type:
            needs_db.append((ticker, _asset_type_str(asset_type)))

    # --- Fase 2: batch DB lookup (UMA query para todos os tickers) ---
    if needs_db:
        db_batch = await _db_get_fresh_batch(db, needs_db)
        for ticker, at_str in needs_db:
            if ticker in db_batch:
                resolved[ticker] = db_batch[ticker]
                _mem_set(ticker, db_batch[ticker])

    # --- Fase 3: classificar o que ainda precisa de API externa ---
    for p in positions:
        ticker = p["ticker"]
        if ticker in resolved:
            continue
        asset_type = type_map.get(ticker)
        if asset_type in NO_QUOTE_TYPES:
            continue

        if asset_type in TREASURY_TYPES:
            treasury_tickers.append(ticker)
        elif asset_type == AssetType.CRIPTO:
            crypto_tickers.append(ticker)
        elif asset_type in BR_TYPES:
            br_tickers.append(ticker)
        elif asset_type in INTL_TYPES:
            intl_pairs.append((ticker, asset_type))
        else:
            logger.warning("[quotes_service] asset_type desconhecido para %s (%s)", ticker, p.get("asset_type"))
            br_tickers.append(ticker)

    # --- Fase 4: chamadas externas em paralelo ---
    br_results, crypto_results, intl_results, treasury_results = await asyncio.gather(
        _fetch_brapi(br_tickers) if br_tickers else _noop(),
        _fetch_brapi_crypto(crypto_tickers) if crypto_tickers else _noop(),
        _fetch_intl_with_stale_fallback(intl_pairs, db) if intl_pairs else _noop(),
        _fetch_treasury_prices(treasury_tickers) if treasury_tickers else _noop(),
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
        logger.info(
            "[quotes_service] sem cotacao BR para %d ativos - tentando fallback",
            len(br_fallback),
        )
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
        logger.warning("[quotes_service] get_current_price sem asset_type para %s", ticker)
        return None
    result = await get_prices([{"ticker": ticker, "asset_type": asset_type}], db)
    return result.get(ticker)


async def update_all_quotes(
    db: AsyncSession,
    asset_types: Optional[list[AssetType]] = None,
) -> int:
    """
    Atualiza cotacoes de todos os ativos (ou apenas dos tipos em asset_types).
    O scheduler chama esta funcao com asset_types filtrado por tipo para evitar
    mistura de ACAO + FII + BDR no mesmo request.
    """
    from app.models.transaction import Transaction

    filter_values = [at.value for at in asset_types] if asset_types else None

    asset_query = select(Asset.ticker, Asset.asset_type).where(
        Asset.asset_type.notin_([at.value for at in NO_QUOTE_TYPES])
    )
    if filter_values:
        asset_query = asset_query.where(Asset.asset_type.in_(filter_values))

    asset_result = await db.execute(asset_query)
    asset_rows = asset_result.all()

    tx_query = select(Transaction.ticker, Transaction.asset_type).distinct()
    if filter_values:
        tx_query = tx_query.where(Transaction.asset_type.in_(filter_values))

    tx_result = await db.execute(tx_query)
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

    type_label = "/".join(at.value for at in asset_types) if asset_types else "ALL"
    logger.info(
        "[quotes_service] update_all_quotes [%s]: %d ativos a atualizar",
        type_label, len(positions),
    )

    prices = await get_prices(positions, db)
    await db.commit()
    logger.info(
        "[quotes_service] update_all_quotes [%s]: %d precos atualizados",
        type_label, len(prices),
    )
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
