"""Orquestra o primeiro estágio isolado do rebuild real: catálogo B3 + COTAHIST."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from time import monotonic

from sqlalchemy import func, select, text

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.asset_seed_service import run_asset_seed
from app.services.b3_historical_market_rebuild_service import (
    rebuild_b3_historical_market,
)

_LOCK_KEY = 7_317_202_607_24
_B3_TYPES = (
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
)


class B3SeedAlreadyRunningError(RuntimeError):
    """Indica que outra execução do estágio B3 mantém o lock operacional."""


@dataclass(frozen=True)
class B3SeedCounts:
    assets: int
    prices: int


@dataclass
class PreProdB3SeedResult:
    started_at: str
    finished_at: str
    duration_seconds: float
    start_year: int
    end_year: int
    cutoff_date: str
    ok: bool
    before: B3SeedCounts
    after: B3SeedCounts
    catalog: dict
    cotahist: dict

    def to_dict(self) -> dict:
        return asdict(self)


async def _counts() -> B3SeedCounts:
    async with AsyncSessionLocal() as db:
        assets = await db.scalar(
            select(func.count()).select_from(Asset).where(Asset.asset_type.in_(_B3_TYPES))
        )
        prices = await db.scalar(
            select(func.count())
            .select_from(AssetPrice)
            .join(Asset, Asset.id == AssetPrice.asset_id)
            .where(Asset.asset_type.in_(_B3_TYPES))
        )
    return B3SeedCounts(assets=int(assets or 0), prices=int(prices or 0))


async def run_pre_prod_b3_seed(
    *,
    start_year: int,
    end_year: int,
    cutoff_date: date,
) -> PreProdB3SeedResult:
    if start_year > end_year:
        raise ValueError("start_year não pode ser posterior a end_year")
    if cutoff_date.year != end_year:
        raise ValueError("cutoff_date deve pertencer ao end_year")

    started = datetime.now(timezone.utc)
    started_clock = monotonic()
    async with AsyncSessionLocal() as lock_db:
        acquired = await lock_db.scalar(
            text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": _LOCK_KEY},
        )
        if not acquired:
            raise B3SeedAlreadyRunningError("estágio B3 já está em execução")
        try:
            before = await _counts()
            async with AsyncSessionLocal() as db:
                catalog_result = await run_asset_seed(
                    db,
                    run_backfill=False,
                    include_crypto=False,
                )
            cotahist_result = await rebuild_b3_historical_market(
                start_year,
                end_year,
                cutoff_date=cutoff_date,
            )
            after = await _counts()
        finally:
            await lock_db.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": _LOCK_KEY},
            )

    finished = datetime.now(timezone.utc)
    catalog = asdict(catalog_result)
    cotahist = cotahist_result.to_dict()
    ok = catalog_result.errors == 0 and cotahist_result.errors == 0
    return PreProdB3SeedResult(
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_seconds=round(monotonic() - started_clock, 3),
        start_year=start_year,
        end_year=end_year,
        cutoff_date=cutoff_date.isoformat(),
        ok=ok,
        before=before,
        after=after,
        catalog=catalog,
        cotahist=cotahist,
    )
