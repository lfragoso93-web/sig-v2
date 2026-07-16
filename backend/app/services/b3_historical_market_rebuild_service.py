"""Carga histórica oficial da B3 via COTAHIST.

O serviço baixa cada arquivo anual uma única vez, filtra ativos brasileiros já
cadastrados, persiste fechamentos de forma idempotente e calcula o ciclo de vida
observado de cada ativo diretamente de asset_prices.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.integrations.b3_cotahist import fetch_b3_cotahist_year_bulk
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction
from app.services.asset_last_price_refresh_service import refresh_asset_last_prices

logger = logging.getLogger(__name__)

_B3_TYPES = {
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
}


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


async def rebuild_b3_historical_market(
    start_year: int | None = None,
    end_year: int | None = None,
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

        assets_result = await db.execute(
            select(Asset).where(Asset.asset_type.in_(_B3_TYPES))
        )
        assets = list(assets_result.scalars().all())
        result.assets = len(assets)
        assets_by_ticker = {str(asset.ticker).upper(): asset for asset in assets}
        tickers = set(assets_by_ticker)
        touched: set[int] = set()
        inserted_by_asset: dict[int, int] = {}

        for year in range(resolved_start_year, resolved_end_year + 1):
            try:
                series_by_ticker = await fetch_b3_cotahist_year_bulk(year, tickers)
                result.years_processed += 1
                if not series_by_ticker:
                    result.files_empty += 1
                    continue
                for ticker, rows in series_by_ticker.items():
                    asset = assets_by_ticker.get(ticker)
                    if asset is None:
                        continue
                    result.rows_received += len(rows)
                    for timestamp, close in rows:
                        stmt = (
                            pg_insert(AssetPrice)
                            .values(
                                asset_id=int(asset.id),
                                timestamp=timestamp,
                                close=Decimal(str(round(close, 8))),
                                source="b3_cotahist",
                            )
                            .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
                            .returning(AssetPrice.id)
                        )
                        inserted = await db.execute(stmt)
                        if inserted.scalar_one_or_none() is not None:
                            result.rows_inserted += 1
                            inserted_by_asset[int(asset.id)] = inserted_by_asset.get(int(asset.id), 0) + 1
                            touched.add(int(asset.id))
                await db.commit()
            except Exception:
                await db.rollback()
                result.errors += 1
                logger.exception("[b3_historical_rebuild] falha ano=%s", year)

        if touched:
            result.refreshed = await refresh_asset_last_prices(db, touched)
            await db.commit()

        for asset in assets:
            price_result = await db.execute(
                select(func.min(AssetPrice.timestamp), func.max(AssetPrice.timestamp)).where(
                    AssetPrice.asset_id == asset.id
                )
            )
            first_ts, last_ts = price_result.one()
            tx_result = await db.execute(
                select(func.min(Transaction.date)).where(
                    Transaction.asset_type == asset.asset_type,
                    func.upper(Transaction.ticker) == str(asset.ticker).upper(),
                )
            )
            first_transaction_date = tx_result.scalar_one_or_none()
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
