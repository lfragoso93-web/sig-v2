from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.services.dividend_backfill_service import ParsedDividendEvent
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendAsset,
    StrictDividendAssetCollection,
    StrictDividendSourceCollection,
)
from app.services.pre_prod_dividends_seed_contract import (
    DividendsSeedCounts,
    DividendsSeedCoverage,
    DividendsSeedIntegrity,
)
from app.services.pre_prod_dividends_seed_materialization import (
    DividendsSeedMaterializationResult,
)
from app.services.pre_prod_dividends_seed_persistence import (
    DividendsSeedPersistenceError,
    DividendsSeedPersistenceResult,
)
from app.services.pre_prod_dividends_seed_service import (
    DividendsSeedUnexpectedStageError,
    run_pre_prod_dividends_seed,
)

RUN_ID = "20260728-180000"
BRANCH = "stable-15jun"
COMMIT_SHA = "a" * 40


def _counts(asset_dividends: int = 0, dividends: int = 0) -> DividendsSeedCounts:
    return DividendsSeedCounts(1, 1, 1, asset_dividends, dividends, 0)


def _event(ex_date: date) -> ParsedDividendEvent:
    return ParsedDividendEvent(
        record_date=ex_date,
        ex_date=ex_date,
        payment_date=ex_date,
        approved_on=None,
        value_per_unit=1.0,
        dividend_type="DIVIDENDO",
    )


def _collection() -> tuple[StrictDividendAssetCollection, ...]:
    return (
        StrictDividendAssetCollection(
            ticker="PETR4",
            asset_type="ACAO",
            sources=(
                StrictDividendSourceCollection(
                    source="brapi",
                    raw_rows=3,
                    normalized_rows=(
                        _event(date(2025, 12, 31)),
                        _event(date(2026, 1, 1)),
                        _event(date(2026, 12, 31)),
                    ),
                    rejected_rows=0,
                    empty_reason=None,
                ),
            ),
        ),
    )


@pytest.mark.asyncio
async def test_runs_single_transaction_and_restricts_window() -> None:
    db = AsyncMock()
    inspections = AsyncMock(
        side_effect=[
            (_counts(), DividendsSeedCoverage(), DividendsSeedIntegrity()),
            (
                _counts(2, 1),
                DividendsSeedCoverage(
                    first_ex_date="2026-01-01",
                    last_ex_date="2026-12-31",
                ),
                DividendsSeedIntegrity(),
            ),
        ]
    )
    asset_loader = AsyncMock(
        return_value=(StrictDividendAsset("PETR4", "ACAO"),)
    )
    collector = AsyncMock(return_value=_collection())
    persistence = AsyncMock(
        return_value=DividendsSeedPersistenceResult(
            created=2,
            updated=0,
            unchanged=0,
        )
    )
    materialization = AsyncMock(
        return_value=DividendsSeedMaterializationResult(
            created=1,
            updated=0,
            unchanged=0,
            skipped_non_cash=0,
        )
    )
    grouping_runner = AsyncMock(
        return_value=(
            {
                "asset_class": "ACAO",
                "event_type": "DIVIDENDO",
                "source": "brapi",
                "year": 2026,
                "ticker": "PETR4",
                "global_events": 2,
                "materialized_rights": 1,
            },
        )
    )

    result = await run_pre_prod_dividends_seed(
        run_id=RUN_ID,
        branch=BRANCH,
        commit_sha=COMMIT_SHA,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        db=db,
        providers=(AsyncMock(),),
        asset_loader=asset_loader,
        collection_runner=collector,
        inspection_runner=inspections,
        grouping_runner=grouping_runner,
        persistence_runner=persistence,
        materialization_runner=materialization,
    )

    restricted = persistence.await_args.kwargs["collections"]
    assert len(restricted[0].sources[0].normalized_rows) == 2
    assert result.ok is True
    assert result.collection == {"assets": 1, "normalized_rows": 2}
    assert result.sources[0]["raw_rows"] == 3
    assert result.groupings[0]["ticker"] == "PETR4"
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_rolls_back_when_post_inspection_has_findings() -> None:
    db = AsyncMock()
    inspections = AsyncMock(
        side_effect=[
            (_counts(), DividendsSeedCoverage(), DividendsSeedIntegrity()),
            (
                _counts(),
                DividendsSeedCoverage(),
                DividendsSeedIntegrity(duplicate_global_events=1),
            ),
        ]
    )

    result = await run_pre_prod_dividends_seed(
        run_id=RUN_ID,
        branch=BRANCH,
        commit_sha=COMMIT_SHA,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        db=db,
        providers=(AsyncMock(),),
        asset_loader=AsyncMock(return_value=()),
        collection_runner=AsyncMock(return_value=()),
        inspection_runner=inspections,
        grouping_runner=AsyncMock(return_value=()),
        persistence_runner=AsyncMock(
            return_value=DividendsSeedPersistenceResult(
                created=0,
                updated=0,
                unchanged=0,
            )
        ),
        materialization_runner=AsyncMock(
            return_value=DividendsSeedMaterializationResult(
                created=0,
                updated=0,
                unchanged=0,
                skipped_non_cash=0,
            )
        ),
    )

    assert result.ok is False
    assert result.transaction.final_state == "rolled_back"
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_rolls_back_and_reraises_on_failure() -> None:
    db = AsyncMock()
    inspections = AsyncMock(
        return_value=(_counts(), DividendsSeedCoverage(), DividendsSeedIntegrity())
    )

    with pytest.raises(
        DividendsSeedUnexpectedStageError,
        match="collection",
    ) as exc_info:
        await run_pre_prod_dividends_seed(
            run_id=RUN_ID,
            branch=BRANCH,
            commit_sha=COMMIT_SHA,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            db=db,
            providers=(AsyncMock(),),
            asset_loader=AsyncMock(
                return_value=(StrictDividendAsset("PETR4", "ACAO"),)
            ),
            collection_runner=AsyncMock(side_effect=RuntimeError("provider")),
            inspection_runner=inspections,
        )

    assert exc_info.value.stage == "collection"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_rolls_back_on_blocking_multisource_conflict() -> None:
    db = AsyncMock()
    inspections = AsyncMock(
        return_value=(_counts(), DividendsSeedCoverage(), DividendsSeedIntegrity())
    )
    conflict = DividendsSeedPersistenceError(
        "evento global conflitante entre fontes"
    )

    with pytest.raises(DividendsSeedPersistenceError) as exc_info:
        await run_pre_prod_dividends_seed(
            run_id=RUN_ID,
            branch=BRANCH,
            commit_sha=COMMIT_SHA,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            db=db,
            providers=(AsyncMock(),),
            asset_loader=AsyncMock(
                return_value=(StrictDividendAsset("PETR4", "ACAO"),)
            ),
            collection_runner=AsyncMock(return_value=_collection()),
            inspection_runner=inspections,
            persistence_runner=AsyncMock(side_effect=conflict),
        )

    assert exc_info.value is conflict
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
