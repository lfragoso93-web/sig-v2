"""
Serviço unificado de cotações.

Pontos importantes:
- RENDA_FIXA e OUTRO não usam APIs de cotação.
- TESOURO_DIRETO usa o catálogo persistido em assets para resolver o `symbol`
  canônico da BRAPI e consulta /api/v2/treasury/indicators.
- Ativos internacionais mantêm fallback stale para evitar zerar tela em rate limit.
- Quando provedores entram em rate limit, aplica cooldown em memória para evitar
  martelar Alpha Vantage/yfinance a cada refresh da UI.
"""
from __future__ import annotations

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
from app.integrations.brapi import fetch_quotes as brapi_fetch_quotes, fetch_crypto_quote as brapi_fetch_crypto
from app.integrations.brapi_treasury import fetch_treasury_prices as brapi_fetch_treasury_prices
from app.models.asset import Asset, AssetType
from app.services.price_history_service import _YF_EXECUTOR, _yf_thread_lock, _YF_MIN_INTERVAL, _yf_last_call
from app.services.treasury_catalog_service import resolve_treasury_symbol

logger = logging.getLogger(__name__)

PRICE_TTL_SECONDS = 900
MEM_CACHE_TTL = 300
BRAPI_CHUNK_SIZE = 20
BRAPI_CHUNK_DELAY = 1.0
PROVIDER_COOLDOWN_SECONDS = 1800

_mem_cache: dict[str, tuple[float, float]] = {}
_provider_cooldown_until: dict[str, float] = {}


def _provider_in_cooldown(name: str) -> bool:
    return time.time() < _provider_cooldown_until.get(name, 0.0)


def _set_provider_cooldown(name: str, seconds: int = PROVIDER_COOLDOWN_SECONDS) -> None:
    _provider_cooldown_until[name] = time.time() + seconds


def _asset_type_str(asset_type) -> str:
    if isinstance(asset_type, AssetType):
        return asset_type.value
    return str(asset_type)


def _asset_type_from_any(asset_type) -> Optional[AssetType]:
    if isinstance(asset_type, AssetType):
        return asset_type
    try:
        return AssetType(str(asset_type))
    except Exception:
        return None


def _mem_get(ticker: str) -> Optional[float]:
    entry = _mem_cache.get(ticker)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _mem_get_stale(ticker: str) -> Optional[float]:
    entry = _mem_cache.get(ticker)
    return entry[0] if entry else None


def _mem_set(ticker: str, price: float) -> None:
    _mem_cache[ticker] = (price, time.time() + MEM_CACHE_TTL)


async def _db_get_fresh_batch(db: AsyncSession, pairs: list[tuple[str, str]]) -> dict[str, float]:
    if not pairs:
        return {}
    pair_set = {(t, at) for t, at in pairs}
    result = await db.execute(
        select(Asset.ticker, Asset.asset_type, Asset.last_price, Asset.last_price_updated_at)
        .where(Asset.ticker.in_([p[0] for p in pairs]))
    )
    now = datetime.now(timezone.utc)
    fresh: dict[str, float] = {}
    for row in result.all():
        if (row.ticker, str(row.asset_type)) not in pair_set:
            continue
        if row.last_price is None or row.last_price_updated_at is None:
            continue
        age = (now - row.last_price_updated_at).total_seconds()
        if age <= PRICE_TTL_SECONDS:
            fresh[row.ticker] = float(row.last_price)
    return fresh


async def _db_get_stale(db: AsyncSession, ticker: str, asset_type) -> Optional[float]:
    result = await db.execute(
        select(Asset.last_price).where(Asset.ticker == ticker, Asset.asset_type == _asset_type_str(asset_type))
    )
    row = result.first()
    if row and row.last_price is not None:
        return float(row.last_price)
    return None


async def _db_set(db: AsyncSession, ticker: str, asset_type, price: float) -> None:
    at_str = _asset_type_str(asset_type)
    try:
        async with db.begin_nested():
            result = await db.execute(select(Asset).where(Asset.ticker == ticker, Asset.asset_type == at_str))
            asset = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            price_decimal = Decimal(str(round(price, 8)))
            if asset:
                asset.last_price = price_decimal
                asset.last_price_updated_at = now
            else:
                db.add(Asset(ticker=ticker, name=ticker, asset_type=at_str, last_price=price_decimal, last_price_updated_at=now))
    except Exception as exc:
        logger.warning("[quotes_service] _db_set falhou para %s/%s: %s", ticker, at_str, exc)


def _filter_brapi_tickers(tickers: list[str]) -> list[str]:
    return [t for t in tickers if not t.endswith("F")]


async def _with_retry(coro_fn, *args, label: str = "") -> dict[str, float]:
    for attempt in range(1, 4):
        try:
            return await coro_fn(*args)
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = any(token in msg.lower() for token in ("rate limit", "too many requests", "ratelimit"))
            if is_rate_limit:
                _set_provider_cooldown(label.split("[")[0])
            if attempt == 3:
                logger.error("[quotes_service] %s todas as tentativas esgotadas: %s", label, msg[:180])
                return {}
            delay = (20.0 * attempt) if is_rate_limit else float(attempt)
            logger.warning("[quotes_service] %s tentativa %d falhou: %s", label, attempt, msg[:180])
            await asyncio.sleep(delay)
    return {}


async def _fetch_brapi_chunked(tickers: list[str], label: str = "quotes") -> dict[str, float]:
    filtered = _filter_brapi_tickers(tickers)
    if not filtered:
        return {}
    results: dict[str, float] = {}
    for i in range(0, len(filtered), BRAPI_CHUNK_SIZE):
        chunk = filtered[i:i + BRAPI_CHUNK_SIZE]
        await brapi_limiter.acquire()
        results.update(await _with_retry(brapi_fetch_quotes, chunk, label=f"{label}[{i//BRAPI_CHUNK_SIZE + 1}]"))
        if i + BRAPI_CHUNK_SIZE < len(filtered):
            await asyncio.sleep(BRAPI_CHUNK_DELAY)
    return results


async def _fetch_brapi(tickers: list[str]) -> dict[str, float]:
    return await _fetch_brapi_chunked(tickers, label="quotes")


async def _fetch_brapi_crypto(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}
    await brapi_limiter.acquire()
    return await _with_retry(brapi_fetch_crypto, tickers, label="quotes-crypto")


def _fetch_yf_current_sync(ticker_map: dict[str, str]) -> dict[str, float]:
    import time as _time
    if not ticker_map:
        return {}
    with _yf_thread_lock:
        elapsed = _time.monotonic() - _yf_last_call[0]
        if elapsed < _YF_MIN_INTERVAL:
            _time.sleep(_YF_MIN_INTERVAL - elapsed)
        try:
            data = yf.download(tickers=list(ticker_map.values()), period="1d", interval="1m", progress=False, auto_adjust=True)
        finally:
            _yf_last_call[0] = _time.monotonic()

    results: dict[str, float] = {}
    if data.empty:
        return results
    is_multi = hasattr(data.columns, "levels")
    for internal, sym in ticker_map.items():
        try:
            series = data[("Close", sym)].dropna() if is_multi else data["Close"].dropna()
            if not series.empty:
                results[internal] = float(series.iloc[-1])
        except Exception:
            continue
    return results


async def _fetch_yfinance_current(pairs: list[tuple[str, AssetType]]) -> dict[str, float]:
    if _provider_in_cooldown("yfinance"):
        logger.info("[quotes_service] yfinance em cooldown — pulando chamada externa")
        return {}
    loop = asyncio.get_event_loop()
    ticker_map = {ticker: yf_ticker(ticker, at) for ticker, at in pairs}
    results = await loop.run_in_executor(_YF_EXECUTOR, _fetch_yf_current_sync, ticker_map)
    if pairs and not results:
        _set_provider_cooldown("yfinance")
    return results


async def _fetch_alpha_vantage_current(pairs: list[tuple[str, AssetType]]) -> dict[str, float]:
    if _provider_in_cooldown("alpha_vantage"):
        logger.info("[quotes_service] Alpha Vantage em cooldown — pulando chamada externa")
        return {}
    from app.integrations.alpha_vantage import fetch_global_quote, _is_configured
    if not _is_configured():
        return {}
    results: dict[str, float] = {}
    for ticker, _ in pairs:
        await alpha_vantage_limiter.acquire()
        price = await fetch_global_quote(ticker)
        if price is not None:
            results[ticker] = price
    if pairs and not results:
        _set_provider_cooldown("alpha_vantage")
    return results


async def _fetch_intl(pairs: list[tuple[str, AssetType]]) -> dict[str, float]:
    av = await _fetch_alpha_vantage_current(pairs)
    missing = [(ticker, at) for ticker, at in pairs if ticker not in av]
    yf_results = await _with_retry(_fetch_yfinance_current, missing, label="yfinance") if missing else {}
    if pairs and len(av) + len(yf_results) == 0:
        _set_provider_cooldown("intl")
    return {**av, **yf_results}


async def _fetch_stale_for_pairs(pairs: list[tuple[str, AssetType]], db: Optional[AsyncSession] = None, label: str = "ativos") -> dict[str, float]:
    results: dict[str, float] = {}
    stale_used: list[str] = []
    for ticker, at in pairs:
        stale = _mem_get_stale(ticker)
        if stale is not None:
            results[ticker] = stale
            stale_used.append(f"{ticker}(mem)")
            continue
        if db:
            db_stale = await _db_get_stale(db, ticker, at)
            if db_stale is not None:
                results[ticker] = db_stale
                stale_used.append(f"{ticker}(db)")
    if stale_used:
        logger.warning("[quotes_service] usando preço stale para %s: %s", label, ", ".join(stale_used[:20]) + ("..." if len(stale_used) > 20 else ""))
    return results


async def _fetch_intl_with_stale_fallback(pairs: list[tuple[str, AssetType]], db: Optional[AsyncSession] = None) -> dict[str, float]:
    if _provider_in_cooldown("intl") or (_provider_in_cooldown("alpha_vantage") and _provider_in_cooldown("yfinance")):
        return await _fetch_stale_for_pairs(pairs, db, label="INTL")
    results = await _fetch_intl(pairs)
    missing = [(ticker, at) for ticker, at in pairs if ticker not in results]
    results.update(await _fetch_stale_for_pairs(missing, db, label="INTL"))
    return results


async def _fetch_treasury_prices(tickers: list[str], db: Optional[AsyncSession] = None) -> dict[str, float]:
    if not tickers:
        return {}
    symbol_by_ticker: dict[str, str] = {}
    for ticker in tickers:
        symbol = await resolve_treasury_symbol(db, ticker) if db else None
        symbol_by_ticker[ticker] = (symbol or ticker).lower()

    prices_by_symbol = await brapi_fetch_treasury_prices(symbol_by_ticker.values())
    results: dict[str, float] = {}
    for ticker, symbol in symbol_by_ticker.items():
        price = prices_by_symbol.get(symbol)
        if price is not None:
            results[ticker] = price
            _mem_set(symbol, price)
            if db and symbol != ticker:
                await _db_set(db, symbol, AssetType.TESOURO_DIRETO, price)
    return results


async def _noop() -> dict[str, float]:
    return {}


async def get_prices(positions: list[dict], db: Optional[AsyncSession] = None) -> dict[str, float]:
    br_tickers: list[str] = []
    crypto_tickers: list[str] = []
    intl_pairs: list[tuple[str, AssetType]] = []
    treasury_tickers: list[str] = []
    type_map: dict[str, AssetType | None] = {}
    resolved: dict[str, float] = {}
    needs_db: list[tuple[str, str]] = []

    for p in positions:
        ticker = str(p.get("ticker") or "").strip()
        if not ticker:
            continue
        raw_type = p.get("asset_type", "")
        asset_type = _asset_type_from_any(raw_type)
        if asset_type is None:
            logger.warning("[quotes_service] asset_type invalido '%s' para %s", raw_type, ticker)
        type_map[ticker] = asset_type

        if asset_type in NO_QUOTE_TYPES:
            continue
        mem_val = _mem_get(ticker)
        if mem_val is not None:
            resolved[ticker] = mem_val
            continue
        if db and asset_type:
            needs_db.append((ticker, _asset_type_str(asset_type)))

    if db and needs_db:
        db_batch = await _db_get_fresh_batch(db, needs_db)
        for ticker, _ in needs_db:
            if ticker in db_batch:
                resolved[ticker] = db_batch[ticker]
                _mem_set(ticker, db_batch[ticker])

    for ticker, asset_type in type_map.items():
        if ticker in resolved or asset_type in NO_QUOTE_TYPES:
            continue
        if asset_type in TREASURY_TYPES:
            treasury_tickers.append(ticker)
        elif asset_type == AssetType.CRIPTO:
            crypto_tickers.append(ticker)
        elif asset_type in BR_TYPES:
            br_tickers.append(ticker)
        elif asset_type in INTL_TYPES:
            intl_pairs.append((ticker, asset_type))
        elif asset_type is not None:
            br_tickers.append(ticker)

    br_results, crypto_results, intl_results, treasury_results = await asyncio.gather(
        _fetch_brapi(br_tickers) if br_tickers else _noop(),
        _fetch_brapi_crypto(crypto_tickers) if crypto_tickers else _noop(),
        _fetch_intl_with_stale_fallback(intl_pairs, db) if intl_pairs else _noop(),
        _fetch_treasury_prices(treasury_tickers, db) if treasury_tickers else _noop(),
    )

    # Não faz fallback yfinance em massa para ativos BR. Quando a BRAPI falha,
    # usa stale se existir; caso contrário deixa sem preço para evitar 429 em cascata.
    br_missing_pairs = [(ticker, type_map[ticker]) for ticker in br_tickers if ticker not in br_results and type_map.get(ticker) is not None]
    br_stale = await _fetch_stale_for_pairs(br_missing_pairs, db, label="BR") if br_missing_pairs else {}

    fresh = {**br_results, **crypto_results, **intl_results, **treasury_results, **br_stale}
    for ticker, price in fresh.items():
        _mem_set(ticker, price)
        if db:
            asset_type = type_map.get(ticker)
            if asset_type is not None:
                await _db_set(db, ticker, asset_type, price)

    return {**resolved, **fresh}


async def get_current_price(ticker: str, asset_type: Optional[str] = None, db: Optional[AsyncSession] = None) -> Optional[float]:
    if asset_type is None:
        logger.warning("[quotes_service] get_current_price sem asset_type para %s", ticker)
        return None
    result = await get_prices([{"ticker": ticker, "asset_type": asset_type}], db)
    return result.get(ticker)


async def get_price_for_transaction(ticker: str, asset_type, db: Optional[AsyncSession] = None) -> Optional[float]:
    at = _asset_type_from_any(asset_type)
    if at is None:
        logger.warning("[quotes_service] get_price_for_transaction asset_type inválido para %s: %s", ticker, asset_type)
        return None
    return await get_current_price(ticker, at.value, db)


async def update_quotes_for_portfolio(portfolio_id: int, db: AsyncSession) -> int:
    from app.models.transaction import Transaction

    result = await db.execute(select(Transaction.ticker, Transaction.asset_type).where(Transaction.portfolio_id == portfolio_id).distinct())
    positions: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in result.all():
        if not row.ticker or not row.asset_type:
            continue
        asset_type_str = str(row.asset_type)
        at = _asset_type_from_any(asset_type_str)
        if at in NO_QUOTE_TYPES:
            continue
        key = (str(row.ticker), asset_type_str)
        if key in seen:
            continue
        seen.add(key)
        positions.append({"ticker": str(row.ticker), "asset_type": asset_type_str})

    prices = await get_prices(positions, db)
    await db.commit()
    logger.info("[quotes_service] update_quotes_for_portfolio(%s): %d/%d preços atualizados", portfolio_id, len(prices), len(positions))
    return len(prices)


async def update_all_quotes(db: AsyncSession, asset_types: Optional[list[AssetType]] = None) -> int:
    from app.models.transaction import Transaction

    filter_values = [at.value for at in asset_types] if asset_types else None
    asset_query = select(Asset.ticker, Asset.asset_type).where(Asset.asset_type.notin_([at.value for at in NO_QUOTE_TYPES]))
    if filter_values:
        asset_query = asset_query.where(Asset.asset_type.in_(filter_values))
    asset_rows = (await db.execute(asset_query)).all()

    tx_query = select(Transaction.ticker, Transaction.asset_type).distinct()
    if filter_values:
        tx_query = tx_query.where(Transaction.asset_type.in_(filter_values))
    tx_rows = (await db.execute(tx_query)).all()

    positions_map: dict[tuple[str, str], dict] = {
        (r.ticker, str(r.asset_type)): {"ticker": r.ticker, "asset_type": str(r.asset_type)}
        for r in asset_rows
        if r.ticker and r.asset_type
    }
    for row in tx_rows:
        if not row.ticker or not row.asset_type:
            continue
        at = _asset_type_from_any(str(row.asset_type))
        if at in NO_QUOTE_TYPES:
            continue
        positions_map.setdefault((row.ticker, str(row.asset_type)), {"ticker": row.ticker, "asset_type": str(row.asset_type)})

    positions = list(positions_map.values())
    prices = await get_prices(positions, db)
    await db.commit()
    logger.info("[quotes_service] update_all_quotes: %d/%d preços atualizados", len(prices), len(positions))
    return len(prices)
