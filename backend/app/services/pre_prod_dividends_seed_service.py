"""Orquestração transacional do estágio isolado de proventos."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.services.pre_prod_dividends_seed_collector import (
    STRICT_DIVIDENDS_ELIGIBLE_TYPES,
    StrictDividendAsset,
    StrictDividendAssetCollection,
    StrictDividendProvider,
    collect_dividends_strict,
)
from app.services.pre_prod_dividends_seed_contract import (
    DividendsSeedTransaction,
    DividendsSeedWindow,
    PreProdDividendsSeedResult,
)
from app.services.pre_prod_dividends_seed_inspection import (
    inspect_dividends_seed_state,
)
from app.services.pre_prod_dividends_seed_materialization import (
    materialize_portfolio_dividends_strict,
)
from app.services.pre_prod_dividends_seed_persistence import (
    persist_asset_dividends_strict,
)

AssetLoader = Callable[[AsyncSession], Awaitable[tuple[StrictDividendAsset, ...]]]
CollectionRunner = Callable[..., Awaitable[tuple[StrictDividendAssetCollection, ...]]]
InspectionRunner = Callable[[AsyncSession], Awaitable[Any]]
PersistenceRunner = Callable[..., Awaitable[Any]]
MaterializationRunner = Callable[..., Awaitable[Any]]


async def load_dividends_seed_assets(
    db: AsyncSession,
) -> tuple[StrictDividendAsset, ...]:
    """Carrega somente ativos globais cobertos pelo contrato operacional."""

    rows = (
        await db.execute(
            select(Asset.ticker, Asset.asset_type)
            .where(Asset.asset_type.in_(sorted(STRICT_DIVIDENDS_ELIGIBLE_TYPES)))
            .order_by(Asset.ticker, Asset.asset_type)
        )
    ).all()
    return tuple(
        StrictDividendAsset(ticker=ticker, asset_type=asset_type)
        for ticker, asset_type in rows
    )


def _restrict_to_window(
    collections: tuple[StrictDividendAssetCollection, ...],
    *,
    start_date: date,
    end_date: date,
) -> tuple[StrictDividendAssetCollection, ...]:
    restricted: list[StrictDividendAssetCollection] = []
    for collection in collections:
        sources = tuple(
            replace(
                source,
                normalized_rows=tuple(
                    event
                    for event in source.normalized_rows
                    if start_date <= event.ex_date <= end_date
                ),
            )
            for source in collection.sources
        )
        restricted.append(replace(collection, sources=sources))
    return tuple(restricted)


def _source_summary(
    collections: tuple[StrictDividendAssetCollection, ...],
) -> tuple[dict, ...]:
    summaries: dict[str, dict[str, int]] = {}
    for collection in collections:
        for source in collection.sources:
            summary = summaries.setdefault(
                source.source,
                {"assets": 0, "raw_rows": 0, "normalized_rows": 0, "empty": 0},
            )
            summary["assets"] += 1
            summary["raw_rows"] += source.raw_rows
            summary["normalized_rows"] += len(source.normalized_rows)
            summary["empty"] += int(source.empty_reason is not None)
    return tuple(
        {"source": source, **summary}
        for source, summary in sorted(summaries.items())
    )


async def run_pre_prod_dividends_seed(
    *,
    run_id: str,
    branch: str,
    commit_sha: str,
    start_date: date,
    end_date: date,
    db: AsyncSession,
    providers: tuple[StrictDividendProvider, ...],
    asset_loader: AssetLoader = load_dividends_seed_assets,
    collection_runner: CollectionRunner = collect_dividends_strict,
    inspection_runner: InspectionRunner = inspect_dividends_seed_state,
    persistence_runner: PersistenceRunner = persist_asset_dividends_strict,
    materialization_runner: MaterializationRunner = (
        materialize_portfolio_dividends_strict
    ),
) -> PreProdDividendsSeedResult:
    """Executa o estágio inteiro em uma única transação controlada."""

    window = DividendsSeedWindow(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    try:
        before, _, _ = await inspection_runner(db)
        assets = await asset_loader(db)
        collected = await collection_runner(assets=assets, providers=providers)
        restricted = _restrict_to_window(
            collected,
            start_date=start_date,
            end_date=end_date,
        )
        persistence = await persistence_runner(db=db, collections=restricted)
        materialization = await materialization_runner(db=db, as_of=end_date)
        after, coverage, integrity = await inspection_runner(db)
        errors = (
            (f"integridade contém {integrity.blocking_findings} achado(s)",)
            if integrity.blocking_findings
            else ()
        )
        if errors:
            await db.rollback()
            transaction = DividendsSeedTransaction(
                final_state="rolled_back",
                committed=False,
                rollback_performed=True,
            )
        else:
            await db.commit()
            transaction = DividendsSeedTransaction(
                final_state="committed",
                committed=True,
                rollback_performed=False,
            )
    except BaseException:
        await db.rollback()
        raise

    return PreProdDividendsSeedResult(
        run_id=run_id,
        branch=branch,
        commit_sha=commit_sha,
        generated_at=datetime.now(UTC).isoformat(),
        ok=not errors,
        window=window,
        before=before,
        after=after,
        coverage=coverage,
        integrity=integrity,
        transaction=transaction,
        sources=_source_summary(restricted),
        collection={
            "assets": len(restricted),
            "normalized_rows": sum(item.normalized_rows for item in restricted),
        },
        global_persistence=asdict(persistence),
        materialization=asdict(materialization),
        errors=errors,
    )
