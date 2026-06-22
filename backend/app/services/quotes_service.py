"""
Servico unificado de cotacoes.

Estrategia de cache em 3 camadas:
  L1 - Asset.last_price no banco (TTL = PRICE_TTL_SECONDS).
  L2 - Cache em memoria processo (TTL = MEM_CACHE_TTL).
  L3 - API externa: BRAPI Pro ou yfinance.

Resiliencia:
  Cada chamada externa e envolta em _with_retry() - 3 tentativas com
  backoff exponencial (1s, 2s). Falha total retorna {} sem propagar excecao,
  mantendo degradacao graciosa (posicao fica sem preco corrente mas nao quebra).

Rate limiting (BRAPI):
  _fetch_brapi e _fetch_brapi_crypto adquirem um token do brapi_limiter antes
  de cada chamada. O limiter e um token bucket in-memory (asyncio-safe) com
  rate e burst configurados via BRAPI_RATE_LIMIT / BRAPI_RATE_BURST no .env.
  Defaults: 2 req/s, burst 5 - conservador para o plano gratuito BRAPI.
  Para o plano Pro, elevar para BRAPI_RATE_LIMIT=10, BRAPI_RATE_BURST=20.

Tesouro Direto:
  Usa fetch_treasury_list() para obter buyPrice atual de cada titulo.
  O ticker no banco corresponde ao slug BRAPI (ex: "tesouro-ipca-2029").
  O buyPrice e o preco unitario do titulo hoje (PU atual).

L1 populate:
  _db_set usa begin_nested() (savepoint) para commitar o last_price
  imediatamente apos busca L3, independente da transacao do chamador.
  Isso garante que a proxima chamada ja encontre L1 populado, sem depender
  exclusivamente do scheduler (update_all_quotes).

Funcoes de portfolio (migradas de quote_service.py em 2026-06-22):
  update_quotes_for_portfolio() - atualiza cotacoes de todos os ativos de
    uma carteira especifica. Usa Transaction como fonte de verdade.
  get_price_for_transaction() - preco historico de um ativo em data especifica.
    Delegado para price_history_service.get_price_at_date().
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
from app.core.rate_limiter import brapi_limiter
from app.integrations.brapi import (
    fetch_quotes as brapi_fetch_quotes,
    fetch_crypto_quote as brapi_fetch_crypto,
    fetch_treasury_list as brapi_fetch_treasury_list,
)
from app.models.asset import Asset, AssetType
from app.services.price_history_service import _YF_EXECUTOR  # pool global compartilhado

logger = logging.getLogger(__name__)

PRICE_TTL_SECONDS = 900
MEM_CACHE_TTL = 60

_RETRY_ATTEMPTS = 3
_RETRY_BASE_DELAY = 1.0  # segundos; duplica a cada tentativa

_mem_cache: dict[str, tuple[float, float]] = {}


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

async def _with_retry(coro_fn, *args, label: str = "") -> dict[str, float]:
    """
    Executa coro_fn(*args) com ate _RETRY_ATTEMPTS tentativas.
    Backoff exponencial: 1s, 2s entre tentativas.
    Retorna {} se todas as tentativas falharem (degradacao graciosa).
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            return await coro_fn(*args)
        except Exception as e:
            if attempt < _RETRY_ATTEMPTS:
                logger.warning(
                    "[quotes_service] %s tentativa %d/%d falhou: %s - retry em %.0fs",
                    label, attempt, _RETRY_ATTEMPTS, e, delay,
                )
                await asyncio.sleep(delay)
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
    """Retorna o valor string do asset_type, seja enum ou string pura."""
    if isinstance(asset_type, AssetType):
        return asset_type.value
    return str(asset_type)


async def _db_get_fresh(
    db: AsyncSession,
    ticker: str,
    asset_type,
) -> Optional[float]:
    """
    Busca last_price em Asset por (ticker, asset_type).
    Compara asset_type como string - evita problemas de cast() no SQLite.
    Retorna None se ausente ou expirado (> PRICE_TTL_SECONDS).
    """
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
    """
    Upsert de last_price na tabela assets por (ticker, asset_type).
    Cria o registro se ainda nao existir - garante que L1 seja populado
    mesmo para ativos cadastrados somente via Transaction.
    Usa a constraint uq_assets_ticker_asset_type (migration 008).

    Usa begin_nested() (SAVEPOINT) para commitar o preco imediatamente,
    independente da transacao principal do chamador. Isso garante que a
    proxima requisicao ja encontre L1 populado sem depender do scheduler.
    Se o savepoint falhar (ex: conflito de constraint), faz rollback apenas
    do savepoint - a transacao principal nao e afetada.
    """
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
        # begin_nested() commita o savepoint aqui - last_price persistido
        # independente do commit da transacao principal do chamador.
    except Exception as e:
        logger.warning(
            "[quotes_service] _db_set savepoint falhou para %s (%s): %s - L1 nao atualizado",
            ticker, at_str, e,
        )


# ---------------------------------------------------------------------------
# Fetch L3 - chamadas externas
# ---------------------------------------------------------------------------

def _fetch_yf_current_sync(ticker_map: dict[str, str]) -> dict[str, float]:
    if not ticker_map:
        return {}
    yf_syms = list(ticker_map.values())
    results: dict[str, float] = {}
    try:
        data = yf.download(
            tickers=yf_syms,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            return {}
        close = data["Close"] if "Close" in data.columns else data
        for internal, sym in ticker_map.items():
            try:
                price = float(
                    close.iloc[-1] if len(yf_syms) == 1
                    else close[sym].dropna().iloc[-1]
                )
                results[internal] = price
            except Exception as e:
                logger.warning(f"yfinance preco nao encontrado para {sym}: {e}")
    except Exception as e:
        logger.error(f"yfinance download error: {e}")
    return results


async def _fetch_yfinance_current(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    ticker_map = {t: yf_ticker(t, at) for t, at in pairs}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_YF_EXECUTOR, _fetch_yf_current_sync, ticker_map)


# ---------------------------------------------------------------------------
# Fetch Tesouro Direto - buyPrice via fetch_treasury_list
# ---------------------------------------------------------------------------

async def _fetch_treasury_prices(slugs: list[str]) -> dict[str, float]:
    """
    Busca o buyPrice atual de titulos do Tesouro Direto via BRAPI treasury list.
    O slug (ticker no banco) e comparado contra os campos slug/bondType/name da API.
    Retorna {slug: buyPrice}.
    """
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
# Aliases mockaveis pelos testes - rate limiting embutido + retry
# ---------------------------------------------------------------------------

async def _fetch_brapi(tickers: list[str]) -> dict[str, float]:
    """Adquire token do rate limiter antes de chamar BRAPI quotes."""
    await brapi_limiter.acquire()
    return await _with_retry(brapi_fetch_quotes, tickers, label="BRAPI")


async def _fetch_brapi_crypto(tickers: list[str]) -> dict[str, float]:
    """Adquire token do rate limiter antes de chamar BRAPI crypto."""
    await brapi_limiter.acquire()
    return await _with_retry(brapi_fetch_crypto, tickers, label="BRAPI-crypto")


async def _fetch_yfinance(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    """Wrapper com retry sobre _fetch_yfinance_current (sem rate limit - yfinance e local)."""
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

    # Mapa ticker -> asset_type para reuso na fase de persistencia
    type_map: dict[str, AssetType | None] = {}

    for p in positions:
        ticker = p["ticker"]
        raw_type = p.get("asset_type", "")
        try:
            asset_type = AssetType(raw_type) if isinstance(raw_type, str) else raw_type
        except ValueError:
            asset_type = None
            logger.warning(
                "[quotes_service] asset_type invalido '%s' para %s - pulando L1 e tentando BRAPI",
                raw_type, ticker,
            )

        type_map[ticker] = asset_type

        if asset_type in NO_QUOTE_TYPES:
            logger.debug(f"[quotes_service] {ticker} ({raw_type}) sem cotacao de mercado - ignorado")
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

        # Roteamento por tipo
        if asset_type in TREASURY_TYPES:
            treasury_slugs.append(ticker)
        elif asset_type == AssetType.CRIPTO:
            crypto_tickers.append(ticker)
        elif asset_type in BR_TYPES:
            br_tickers.append(ticker)
        elif asset_type in INTL_TYPES:
            intl_pairs.append((ticker, asset_type))
        else:
            logger.warning(f"[quotes_service] asset_type desconhecido para {ticker} ({raw_type}) - tentando BRAPI")
            br_tickers.append(ticker)

    # Chamadas externas em paralelo - cada uma ja tem rate limit + retry embutido
    br_results, crypto_results, intl_results, treasury_results = await asyncio.gather(
        _fetch_brapi(br_tickers) if br_tickers else _noop(),
        _fetch_brapi_crypto(crypto_tickers) if crypto_tickers else _noop(),
        _fetch_yfinance(intl_pairs) if intl_pairs else _noop(),
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

    # Persiste precos frescos no L1 via savepoint (commit independente da
    # transacao principal). Garante que a proxima requisicao encontre L1
    # populado sem depender do scheduler (update_all_quotes).
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
                logger.warning(
                    "[quotes_service] asset_type invalido para %s - L1 nao atualizado",
                    ticker,
                )

    return {**resolved, **fresh}


async def get_current_price(
    ticker: str,
    asset_type: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Optional[float]:
    """
    Conveniencia: busca preco de um unico ticker.
    asset_type deve ser sempre passado para garantir o provedor correto.
    """
    if asset_type is None:
        logger.warning(f"[quotes_service] get_current_price chamado sem asset_type para {ticker} - retornando None")
        return None
    result = await get_prices([{"ticker": ticker, "asset_type": asset_type}], db)
    return result.get(ticker)


async def update_all_quotes(db: AsyncSession) -> int:
    """
    Atualiza last_price de todos os ativos com cotacao de mercado.

    Sempre combina duas fontes para montar a lista de posicoes:
      1. Assets existentes na tabela (excluindo NO_QUOTE_TYPES).
      2. Tickers distintos de Transaction que ainda nao tenham Asset.
    Isso garante que ativos cadastrados apenas via Transaction (sem registro
    manual em Asset) sempre entrem no ciclo do scheduler - resolvendo o
    problema de L1 vazio persistente.
    """
    from app.models.transaction import Transaction

    # Fonte 1: assets ja registrados
    asset_result = await db.execute(
        select(Asset.ticker, Asset.asset_type).where(
            Asset.asset_type.notin_([at.value for at in NO_QUOTE_TYPES])
        )
    )
    asset_rows = asset_result.all()

    # Fonte 2: tickers distintos de Transaction
    tx_result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type).distinct()
    )
    tx_rows = tx_result.all()

    # Union: mantem known + adiciona tickers de Transaction ausentes em known
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
            logger.info(
                "[quotes_service] update_all_quotes: ticker %s (%s) so em Transaction - incluido no ciclo",
                row.ticker, row.asset_type,
            )

    positions = list(positions_map.values())

    if not positions:
        logger.info("[quotes_service] update_all_quotes: nenhuma posicao para atualizar")
        return 0

    prices = await get_prices(positions, db)
    await db.commit()
    logger.info("[quotes_service] update_all_quotes: %d precos atualizados", len(prices))
    return len(prices)


# ---------------------------------------------------------------------------
# Funcoes de portfolio (migradas de quote_service.py — 2026-06-22)
# ---------------------------------------------------------------------------

async def update_quotes_for_portfolio(
    portfolio_id: int,
    db: AsyncSession,
) -> int:
    """
    Atualiza Asset.last_price para todos os ativos de uma carteira especifica.
    Retorna o numero de ativos atualizados.

    Usa Transaction como fonte de verdade (substitui PortfolioPosition legada).
    Fluxo:
      1. Busca tickers e asset_types distintos das transacoes da carteira.
      2. Monta lista de {ticker, asset_type} para get_prices().
      3. get_prices() consulta L1/L2 do cache e so vai a API para o que expirou.
      4. Persiste last_price em Asset via _db_set() interno (savepoint).
      5. Commit unico ao final.
    """
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
        for r in rows
        if r.ticker
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
    """
    Retorna o preco de fechamento de um ativo em uma data especifica (YYYY-MM-DD).
    Usado pelo transaction_service ao registrar operacoes retroativas.

    Fluxo (via get_price_at_date do price_history_service):
      1. Consulta asset_prices no banco - janela de 5 dias antes de date_str.
      2. Se nao encontrar, dispara persist_daily_prices() - BRAPI Pro ou yfinance.
      3. Retorna o fechamento mais recente disponivel na janela.
      4. Retorna None se nenhuma fonte tiver o dado (sem lancar excecao).
    """
    from app.services.price_history_service import get_price_at_date
    try:
        return await get_price_at_date(db, ticker, asset_type, date_str)
    except Exception as e:
        logger.warning(
            "[quotes_service] get_price_for_transaction falhou para %s em %s: %s",
            ticker, date_str, e,
        )
        return None
