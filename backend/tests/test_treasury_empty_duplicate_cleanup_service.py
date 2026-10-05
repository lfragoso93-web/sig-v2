from unittest.mock import AsyncMock

import pytest

from app.models.asset import Asset, AssetType
from app.services.treasury_empty_duplicate_cleanup_service import (
    audit_empty_treasury_duplicate_cleanup,
    cleanup_empty_treasury_duplicate_assets,
)


class _ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _Result:
    def __init__(self, rows: list[object] | None = None, scalar: int = 0) -> None:
        self._rows = rows or []
        self._scalar = scalar
        self.rowcount = scalar

    def scalars(self) -> _ScalarRows:
        return _ScalarRows(self._rows)

    def scalar_one(self) -> int:
        return self._scalar


class _CleanupSession:
    def __init__(self, assets: list[Asset], counts: list[int]) -> None:
        self.execute = AsyncMock(
            side_effect=[_Result(rows=assets), *[_Result(scalar=count) for count in counts]]
        )
        self.commit = AsyncMock()


def _asset(asset_id: int, ticker: str) -> Asset:
    return Asset(
        id=asset_id,
        ticker=ticker,
        asset_type=AssetType.TESOURO_DIRETO.value,
    )


@pytest.mark.asyncio
async def test_empty_duplicate_cleanup_dry_run_is_read_only() -> None:
    db = _CleanupSession([_asset(3720, "TESOURO-SELIC-01032031")], [0] * 8)

    result = await cleanup_empty_treasury_duplicate_assets(db)  # type: ignore[arg-type]

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["deleted"] == 0
    assert len(result["deletable"]) == 1
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_duplicate_cleanup_blocks_referenced_asset() -> None:
    db = _CleanupSession([_asset(3720, "TESOURO-SELIC-01032031")], [0, 1, 0, 0, 0, 0, 0, 0])

    result = await audit_empty_treasury_duplicate_cleanup(db)  # type: ignore[arg-type]

    assert result["ok"] is False
    assert result["deletable"] == []
    assert result["blocked"][0]["reference_counts"]["transactions_exact"] == 1


@pytest.mark.asyncio
async def test_empty_duplicate_cleanup_executes_when_all_guards_pass() -> None:
    db = _CleanupSession([_asset(3720, "TESOURO-SELIC-01032031")], [0] * 8)
    db.execute.side_effect = [
        _Result(rows=[_asset(3720, "TESOURO-SELIC-01032031")]),
        *[_Result(scalar=0) for _ in range(8)],
        _Result(scalar=1),
    ]

    result = await cleanup_empty_treasury_duplicate_assets(
        db,  # type: ignore[arg-type]
        dry_run=False,
    )

    assert result["ok"] is True
    assert result["dry_run"] is False
    assert result["deleted"] == 1
    db.commit.assert_awaited_once()
