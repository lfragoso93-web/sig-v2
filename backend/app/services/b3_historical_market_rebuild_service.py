"""Carga histórica oficial da B3 via COTAHIST.

O serviço baixa cada arquivo anual uma única vez, filtra ativos brasileiros já
cadastrados, persiste fechamentos de forma idempotente e calcula o ciclo de vida
observado de cada ativo diretamente de asset_prices.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.integrations.b3_cotahist import (
    CotahistRecord,
    fetch_b3_cotahist_year_records,
)
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction
from app.services.asset_last_price_refresh_service import refresh_asset_last_prices

logger = logging.getLogger(__name__)

_IBOV_TICKER = "IBOV"
_B3_TYPES = {
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
}
_B3_BENCHMARK_TICKERS = {_IBOV_TICKER}
_BATCH_SIZE = 1000


@dataclass
class B3HistoricalAssetResult:
    ticker: str
    asset_id: int
    first_price_date: date | None = None
    last_price_date: date | None = None
    first_transaction_date: date | None = None
    lifecycle: str = "NO_HISTORY"
    inserted: int = 0


@dataclass
class B3HistoricalMarketRebuildResult:
    start_year: int
    end_year: int
    assets: int = 0
    years_processed: int = 0
    files_empty: int = 0
    rows_received: int = 0
    rows_inserted: int = 0
    refreshed: int = 0
    complete: int = 0
    pre_listing: int = 0
    delisted: int = 0
    real_gap: int = 0
    no_history: int = 0
    errors: int = 0
    items: list[B3HistoricalAssetResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _classify_lifecycle(
    *,
    first_price_date: date | None,
    last_price_date: date | None,
    first_transaction_date: date | None,
    today: date,
) -> str:
    if first_price_date is None or last_price_date is None:
        return "NO_HISTORY"
    if first_transaction_date is not None and first_transaction_date < first_price_date:
        return "PRE_LISTING"
    if (today - last_price_date).days > 45:
        return "DELISTED"
    return "COMPLETE"


def _canonical_records_by_ticker(
    records: list[CotahistRecord],
    requested: set[str],
) -> dict[str, list[CotahistRecord]]:
    rows_by_ticker: dict[str, dict[date, CotahistRecord]] = {}
    for record in records:
        ticker = record.ticker.upper()
        if ticker not in requested:
            continue
        ticker_rows = rows_by_ticker.setdefault(ticker, {})
        day = record.timestamp.date()
        previous = ticker_rows.get(day)
        if previous is None or (
            previous.market_type == "020" and record.market_type == "010"
        ):
            ticker_rows[day] = record

    return {
        ticker: sorted(values.values(), key=lambda record: record.timestamp)
        for ticker, values in rows_by_ticker.items()
    }


async def _ensure_ibov_benchmark_asset(db) -> Asset:
    result = await db.execute(
        select(Asset).where(func.upper(Asset.ticker) == _IBOV_TICKER).limit(1)
    )
    asset = result.scalar_one_or_none()
    if asset is not None:
        return asset

    asset = Asset(
        ticker=_IBOV_TICKER,
        name="Ibovespa",
        asset_type=AssetType.OUTRO.value,
        currency="BRL",
        provider="b3_cotahist",
        provider_symbol=_IBOV_TICKER,
        provider_status="persisted_benchmark",
    )
    db.add(asset)
    await db.flush()
    return asset


async def rebuild_b3_historical_market(
    start_year: int | None = None,
    end_year: int | None = None,
    cutoff_date: date | None = None,
) -> B3HistoricalMarketRebuildResult:
    today = date.today()
    async with AsyncSessionLocal() as db:
        tx_year_result = await db.execute(
            select(func.min(Transaction.date)).where(Transaction.asset_type.in_(_B3_TYPES))
        )
        first_tx_date = tx_year_result.scalar_one_or_none()
        resolved_start_year = start_year or (first_tx_date.year if first_tx_date else today.year)
        resolved_end_year = end_year or today.year
        result = B3HistoricalMarketRebuildResult(resolved_start_year, resolved_end_year)

        await _ensure_ibov_benchmark_asset(db)
        assets_result = await db.execute(
            select(Asset).where(
                (Asset.asset_type.in_(_B3_TYPES))
                | (func.upper(Asset.ticker).in_(_B3_BENCHMARK_TICKERS))
            )
        )
        assets = list(assets_result.scalars().all())
        result.assets = len(assets)
        assets_by_ticker = {str(asset.ticker).upper(): asset for asset in assets}
        tickers = set(assets_by_ticker)
        touched: set[int] = set()
        inserted_by_asset: dict[int, int] = {}

        covered_years: set[int] = set()
        if resolved_end_year > resolved_start_year:
            yr_col = func.extract("year", AssetPrice.timestamp)
            yr_rows = (
                await db.execute(
                    select(yr_col, func.count())
                    .where(AssetPrice.source == "b3_cotahist")
                    .group_by(yr_col)
                )
            ).all()
            covered_years = {
                int(yr)
                for yr, cnt in yr_rows
                if yr is not None
                and int(yr) < resolved_end_year
                and int(cnt or 0) >= 10_000
            }

        for year in range(resolved_start_year, resolved_end_year + 1):
            if year in covered_years:
                result.years_processed += 1
                continue
            try:
                records = await fetch_b3_cotahist_year_records(year)
                series_by_ticker = _canonical_records_by_ticker(records, tickers)
                result.years_processed += 1
                if not series_by_ticker:
                    result.files_empty += 1
                    continue

                batch_values: list[dict] = []
                batch_asset_ids: list[int] = []
                for ticker, ticker_records in series_by_ticker.items():
                    asset = assets_by_ticker.get(ticker)
                    if asset is None:
                        continue
                    result.rows_received += len(ticker_records)
                    asset_id = int(asset.id)
                    for record in ticker_records:
                        if cutoff_date is not None and record.timestamp.date() > cutoff_date:
                            continue
                        batch_values.append(
                            {
                                "asset_id": asset_id,
                                "timestamp": record.timestamp,
                                "open": record.open,
                                "high": record.high,
                                "low": record.low,
                                "close": record.close,
                                "volume": record.volume,
                                "source": "b3_cotahist",
                            }
                        )
                        batch_asset_ids.append(asset_id)

                for i in range(0, len(batch_values), _BATCH_SIZE):
                    chunk = batch_values[i : i + _BATCH_SIZE]
                    stmt = (
                        pg_insert(AssetPrice)
                        .values(chunk)
                        .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
                        .returning(AssetPrice.asset_id)
                    )
                    inserted_res = await db.execute(stmt)
                    for ins_asset_id in inserted_res.scalars().all():
                        if ins_asset_id is not None:
                            result.rows_inserted += 1
                            aid = int(ins_asset_id)
                            inserted_by_asset[aid] = inserted_by_asset.get(aid, 0) + 1
                            touched.add(aid)

                await db.commit()
            except Exception:
                await db.rollback()
                result.errors += 1
                logger.exception("[b3_historical_rebuild] falha ano=%s", year)

        if touched:
            result.refreshed = await refresh_asset_last_prices(db, touched)
            await db.commit()

        price_stats_rows = (
            await db.execute(
                select(
                    AssetPrice.asset_id,
                    func.min(AssetPrice.timestamp),
                    func.max(AssetPrice.timestamp),
                )
                .group_by(AssetPrice.asset_id)
            )
        ).all()
        price_stats = {int(aid): (mn, mx) for aid, mn, mx in price_stats_rows}

        tx_stats_rows = (
            await db.execute(
                select(
                    Transaction.asset_type,
                    func.upper(Transaction.ticker),
                    func.min(Transaction.date),
                )
                .group_by(Transaction.asset_type, func.upper(Transaction.ticker))
            )
        ).all()
        tx_stats = {(at, tk): dt for at, tk, dt in tx_stats_rows}

        for asset in assets:
            first_ts, last_ts = price_stats.get(int(asset.id), (None, None))
            first_transaction_date = tx_stats.get(
                (asset.asset_type, str(asset.ticker).upper())
            )
            first_price_date = first_ts.date() if first_ts else None
            last_price_date = last_ts.date() if last_ts else None
            lifecycle = _classify_lifecycle(
                first_price_date=first_price_date,
                last_price_date=last_price_date,
                first_transaction_date=first_transaction_date,
                today=today,
            )
            if lifecycle == "COMPLETE":
                result.complete += 1
            elif lifecycle == "PRE_LISTING":
                result.pre_listing += 1
            elif lifecycle == "DELISTED":
                result.delisted += 1
            elif lifecycle == "REAL_GAP":
                result.real_gap += 1
            else:
                result.no_history += 1
            result.items.append(
                B3HistoricalAssetResult(
                    ticker=str(asset.ticker),
                    asset_id=int(asset.id),
                    first_price_date=first_price_date,
                    last_price_date=last_price_date,
                    first_transaction_date=first_transaction_date,
                    lifecycle=lifecycle,
                    inserted=inserted_by_asset.get(int(asset.id), 0),
                )
            )

    logger.info(
        "[b3_historical_rebuild] years=%s..%s assets=%d received=%d inserted=%d errors=%d",
        result.start_year,
        result.end_year,
        result.assets,
        result.rows_received,
        result.rows_inserted,
        result.errors,
    )
    return result
