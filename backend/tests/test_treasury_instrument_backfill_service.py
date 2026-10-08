from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.asset import Asset, AssetType
from app.services.treasury_instrument_backfill_service import (
    backfill_treasury_instruments,
)


class _Result:
    def __init__(self, *, scalar: object = None, rows: list[object] | None = None):
        self._scalar = scalar
        self._rows = rows or []

    def scalar_one_or_none(self) -> object:
        return self._scalar

    def scalars(self) -> MagicMock:
        scalars = MagicMock()
        scalars.all.return_value = self._rows
        return scalars


class _Session:
    def __init__(self, results: list[_Result]) -> None:
        self.execute = AsyncMock(side_effect=results)
        self.add_all = MagicMock()
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


def _asset(asset_id: int, name: str, *, ticker: str | None = None) -> Asset:
    return Asset(
        id=asset_id,
        ticker=ticker or f"tesouro-selic-{asset_id}",
        name=name,
        asset_type=AssetType.TESOURO_DIRETO.value,
    )


@pytest.mark.asyncio
async def test_backfill_fails_closed_when_schema_is_not_applied() -> None:
    db = _Session([_Result(scalar=None)])

    report = await backfill_treasury_instruments(db)  # type: ignore[arg-type]

    assert report["schema_ready"] is False
    assert report["database_writes_executed"] == 0
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_dry_run_reports_candidates_without_writes() -> None:
    assets = [_asset(10, "Tesouro Selic 01/03/2031")]
    db = _Session(
        [
            _Result(scalar="treasury_instruments"),
            _Result(rows=assets),
        ]
    )

    report = await backfill_treasury_instruments(db)  # type: ignore[arg-type]

    assert report["dry_run"] is True
    assert report["schema_ready"] is True
    assert report["candidate_count"] == 1
    assert report["candidate_asset_ids"] == [10]
    assert report["conflict_count"] == 0
    assert report["database_writes_executed"] == 0
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_execute_inserts_only_persisted_names() -> None:
    assets = [_asset(10, "Tesouro Selic 01/03/2031")]
    db = _Session(
        [
            _Result(scalar="treasury_instruments"),
            _Result(rows=assets),
        ]
    )

    report = await backfill_treasury_instruments(
        db,  # type: ignore[arg-type]
        dry_run=False,
    )

    instruments = db.add_all.call_args.args[0]
    assert len(instruments) == 1
    assert instruments[0].asset_id == 10
    assert instruments[0].commercial_name == "Tesouro Selic 01/03/2031"
    assert instruments[0].metadata_source == "assets.name"
    assert report["database_writes_executed"] == 1
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_blocks_case_insensitive_identity_conflicts() -> None:
    assets = [
        _asset(
            10,
            "Tesouro Selic 2031",
            ticker="tesouro-selic-01032031",
        ),
        _asset(
            11,
            "Tesouro Selic 2031",
            ticker="TESOURO-SELIC-01032031",
        ),
    ]
    db = _Session(
        [
            _Result(scalar="treasury_instruments"),
            _Result(rows=assets),
        ]
    )

    report = await backfill_treasury_instruments(
        db,  # type: ignore[arg-type]
        dry_run=False,
    )

    assert report["conflict_count"] == 1
    assert report["conflicts"] == [
        {
            "normalized_ticker": "tesouro-selic-01032031",
            "asset_ids": [10, 11],
        }
    ]
    assert report["database_writes_executed"] == 0
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_backfill_preserves_distinct_historical_maturities() -> None:
    assets = [
        _asset(
            20,
            "Tesouro Prefixado 01/04/2006",
            ticker="tesouro-prefixado-01042006",
        ),
        _asset(
            21,
            "Tesouro Prefixado 01/07/2006",
            ticker="tesouro-prefixado-01072006",
        ),
    ]
    db = _Session(
        [
            _Result(scalar="treasury_instruments"),
            _Result(rows=assets),
        ]
    )

    report = await backfill_treasury_instruments(
        db,  # type: ignore[arg-type]
        dry_run=False,
    )

    instruments = db.add_all.call_args.args[0]
    assert [item.asset_id for item in instruments] == [20, 21]
    assert [item.commercial_name for item in instruments] == [
        "Tesouro Prefixado 01/04/2006",
        "Tesouro Prefixado 01/07/2006",
    ]
    assert report["conflict_count"] == 0
    assert report["database_writes_executed"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name",
    [
        "Tesouro RendA+ Aposentadoria Extra 15/12/2079",
        "Tesouro Educa+ 2035",
        "Tesouro Selic 2031",
    ],
)
async def test_backfill_keeps_persisted_commercial_names_without_inventing_codes(
    name: str,
) -> None:
    db = _Session(
        [
            _Result(scalar="treasury_instruments"),
            _Result(rows=[_asset(30, name)]),
        ]
    )

    await backfill_treasury_instruments(
        db,  # type: ignore[arg-type]
        dry_run=False,
    )

    instrument = db.add_all.call_args.args[0][0]
    assert instrument.commercial_name == name
    assert instrument.official_code is None
    assert instrument.maturity_date is None
