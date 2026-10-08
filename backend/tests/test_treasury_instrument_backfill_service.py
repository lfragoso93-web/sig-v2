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


def _asset(asset_id: int, name: str) -> Asset:
    return Asset(
        id=asset_id,
        ticker=f"tesouro-selic-{asset_id}",
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
