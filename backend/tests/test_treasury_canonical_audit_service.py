from unittest.mock import AsyncMock

import pytest

from app.models.asset import Asset, AssetType
from app.services import treasury_canonical_audit_service as service


class _ScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _ExecuteResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._rows)

    def all(self) -> list[object]:
        return self._rows


class _AuditSession:
    def __init__(self, assets: list[Asset]) -> None:
        self._results = [
            _ExecuteResult(assets),
            _ExecuteResult([]),
            _ExecuteResult([]),
        ]
        self.execute = AsyncMock(side_effect=self._results)
        self.add = AsyncMock()
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.delete = AsyncMock()


def _treasury_asset(
    asset_id: int,
    ticker: str,
    *,
    provider: str | None = None,
) -> Asset:
    return Asset(
        id=asset_id,
        ticker=ticker,
        name=ticker,
        asset_type=AssetType.TESOURO_DIRETO.value,
        provider=provider,
    )


@pytest.mark.asyncio
async def test_audit_detects_productive_duplicate_and_skips_synthetic_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve_symbol(_db: object, ticker: str) -> str | None:
        symbols = {
            "tesouro-selic-01032029": "tesouro-selic-01032029",
            "TESOURO-SELIC-01032029": "tesouro-selic-01032029",
            "CERT303-TESOURO-SELIC-2029": "tesouro-selic-01032029",
        }
        return symbols.get(ticker)

    monkeypatch.setattr(service, "resolve_treasury_symbol", resolve_symbol)
    db = _AuditSession(
        [
            _treasury_asset(17, "tesouro-selic-01032029"),
            _treasury_asset(3720, "TESOURO-SELIC-01032029"),
            _treasury_asset(
                2867,
                "CERT303-TESOURO-SELIC-2029",
                provider="synthetic-certification",
            ),
        ]
    )

    result = await service.audit_treasury_canonical_assets(db)  # type: ignore[arg-type]

    assert result["assets"] == 3
    assert result["canonical_groups"] == 1
    assert result["duplicate_groups"] == 1
    assert result["migration_candidates"] == 1
    assert result["unresolved"] == []
    assert result["destructive_changes"] is False
    duplicate_entries = result["duplicates"]["tesouro-selic-01032029"]
    assert [entry["asset_id"] for entry in duplicate_entries] == [17, 3720]


@pytest.mark.asyncio
async def test_audit_keeps_synthetic_certification_out_of_migration_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve_symbol = AsyncMock(return_value="tesouro-selic-01032029")
    monkeypatch.setattr(service, "resolve_treasury_symbol", resolve_symbol)
    db = _AuditSession(
        [
            _treasury_asset(17, "tesouro-selic-01032029"),
            _treasury_asset(
                2867,
                "CERT303-TESOURO-SELIC-2029",
                provider="synthetic-certification",
            ),
        ]
    )

    result = await service.audit_treasury_canonical_assets(db)  # type: ignore[arg-type]

    assert result["assets"] == 2
    assert result["canonical_groups"] == 1
    assert result["duplicate_groups"] == 0
    assert result["migration_candidates"] == 0
    assert result["duplicates"] == {}
    resolve_symbol.assert_awaited_once()
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.flush.assert_not_called()
    db.delete.assert_not_called()
