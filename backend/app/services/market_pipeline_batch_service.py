"""Serviço operacional para executar o pipeline único de mercado em lote."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction
from app.services.asset_market_pipeline_service import sync_asset_market_data

logger = logging.getLogger(__name__)

DEFAULT_PIPELINE_TYPES = {AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL, AssetType.BDR}
_MAIN_TICKER_RE = re.compile(r"^[A-Z0-9]{4,6}(3|4|5|6|11|31|32|33|34|35)$")


@dataclass
class MarketPipelineBatchResult:
    candidates: int = 0
    eligible: int = 0
    skipped: int = 0
    ok: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _asset_type_from_db(value) -> AssetType | None:
    raw = str(value or "").replace("AssetType.", "").upper()
    try:
        return AssetType(raw)
    except ValueError:
        return None


def is_market_pipeline_ticker(ticker: str) -> bool:
    t = ticker.upper()
    if t.endswith("F") or t[-1:] in {"B", "D", "R"} or t[-2:] in {"97", "98", "99"}:
        return False
    return bool(_MAIN_TICKER_RE.match(t))


async def load_market_pipeline_pairs(
    db: AsyncSession,
    *,
    asset_types: set[AssetType] | None = None,
    only_held: bool = True,
    tickers: list[str] | None = None,
) -> tuple[list[tuple[str, AssetType]], int]:
    wanted_types = asset_types or set(DEFAULT_PIPELINE_TYPES)
    wanted = sorted(at.value for at in wanted_types)
    ticker_filter = [t.upper() for t in (tickers or []) if t]

    if ticker_filter:
        stmt = select(Asset.ticker, Asset.asset_type).where(
            Asset.ticker.in_(ticker_filter),
            Asset.asset_type.in_(wanted),
        )
    elif only_held:
        stmt = select(Transaction.ticker, Transaction.asset_type).where(
            Transaction.asset_type.in_(wanted),
        ).distinct()
    else:
        stmt = select(Asset.ticker, Asset.asset_type).where(Asset.asset_type.in_(wanted))

    rows = await db.execute(stmt)
    raw_pairs: list[tuple[str, AssetType]] = []
    for ticker, raw_type in rows.all():
        at = _asset_type_from_db(raw_type)
        if ticker and at:
            raw_pairs.append((str(ticker).upper(), at))

    unique = sorted(set(raw_pairs), key=lambda item: (item[1].value, item[0]))
    eligible = [(ticker, at) for ticker, at in unique if is_market_pipeline_ticker(ticker)]
    return eligible, len(unique) - len(eligible)


async def _run_one(
    ticker: str,
    asset_type: AssetType,
    *,
    full: bool,
    sync_prices: bool,
    sync_logo: bool,
    sync_events: bool,
    materialize: bool,
) -> tuple[str, bool, str | None]:
    async with AsyncSessionLocal() as item_db:
        try:
            await sync_asset_market_data(
                db=item_db,
                ticker=ticker,
                asset_type=asset_type,
                full=full,
                sync_prices=sync_prices,
                sync_logo=sync_logo,
                sync_events=sync_events,
                materialize=materialize,
                commit=True,
            )
            return ticker, True, None
        except Exception as exc:
            logger.exception("[market_pipeline_batch] falha em %s/%s: %s", ticker, asset_type.value, exc)
            return ticker, False, f"{ticker}/{asset_type.value}: {exc}"


async def run_market_pipeline_batch(
    db: AsyncSession,
    *,
    asset_types: set[AssetType] | None = None,
    only_held: bool = True,
    tickers: list[str] | None = None,
    limit: int | None = None,
    concurrency: int = 1,
    delay: float = 0.0,
    full: bool = False,
    sync_prices: bool = True,
    sync_logo: bool = True,
    sync_events: bool = True,
    materialize: bool = True,
) -> MarketPipelineBatchResult:
    pairs, skipped = await load_market_pipeline_pairs(
        db,
        asset_types=asset_types,
        only_held=only_held,
        tickers=tickers,
    )
    candidates = len(pairs) + skipped
    if limit and limit > 0:
        pairs = pairs[:limit]

    result = MarketPipelineBatchResult(
        candidates=candidates,
        eligible=len(pairs),
        skipped=skipped,
    )

    logger.info(
        "[market_pipeline_batch] iniciando: candidates=%s eligible=%s skipped=%s only_held=%s full=%s concurrency=%s",
        result.candidates,
        result.eligible,
        result.skipped,
        only_held,
        full,
        concurrency,
    )

    concurrency = max(1, concurrency)
    for i in range(0, len(pairs), concurrency):
        batch = pairs[i:i + concurrency]
        batch_results = await asyncio.gather(
            *[
                _run_one(
                    ticker,
                    at,
                    full=full,
                    sync_prices=sync_prices,
                    sync_logo=sync_logo,
                    sync_events=sync_events,
                    materialize=materialize,
                )
                for ticker, at in batch
            ]
        )
        for _, ok, error in batch_results:
            if ok:
                result.ok += 1
            else:
                result.failed += 1
                if error:
                    result.errors.append(error)
        logger.info(
            "[market_pipeline_batch] progresso %s/%s | ok=%s failed=%s",
            min(i + concurrency, len(pairs)),
            len(pairs),
            result.ok,
            result.failed,
        )
        if delay > 0 and i + concurrency < len(pairs):
            await asyncio.sleep(delay)

    logger.info("[market_pipeline_batch] concluído: %s", result)
    return result
