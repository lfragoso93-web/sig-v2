from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.asset import Asset, AssetType
from app.services import asset_seed_service
from app.services.fx_service import persist_usd_brl_rate
from app.services.pre_prod_dividends_seed_persistence import (
    persist_asset_dividends_strict,
)


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Scalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class _Result:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _Scalars(self._values)


@pytest.mark.asyncio
async def test_asset_catalog_second_run_skips_existing_asset(monkeypatch):
    db = MagicMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    stored = Asset(
        id=1,
        ticker="PETR4",
        name="Petrobras PN",
        asset_type=AssetType.ACAO.value,
        currency="BRL",
        sector="Petróleo",
        logo_url="https://example.test/petr4.png",
    )
    db.execute = AsyncMock(return_value=_ScalarResult(stored))

    status = await asset_seed_service._upsert_asset(
        db,
        ticker="PETR4",
        name="Petrobras PN",
        asset_type=AssetType.ACAO,
        sector="Petróleo",
        logo_url="https://example.test/petr4.png",
    )

    assert status == "skipped"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_fx_persistence_reuses_pair_date_identity_on_repeated_write():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    await persist_usd_brl_rate(db, "2026-08-08", 5.4321, commit=False)
    await persist_usd_brl_rate(db, "2026-08-08", 5.4321, commit=False)

    assert db.execute.await_count == 2
    for call in db.execute.await_args_list:
        sql = str(call.args[0])
        assert "ON CONFLICT (pair, rate_date)" in sql
        assert "DO UPDATE SET" in sql
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_dividend_persistence_second_run_marks_existing_event_unchanged(monkeypatch):
    db = MagicMock()
    db.scalar = AsyncMock(return_value=True)
    db.add = MagicMock()

    asset = SimpleNamespace(id=7, ticker="PETR4", asset_type="ACAO")
    existing = SimpleNamespace(
        asset_id=7,
        ex_date=__import__("datetime").date(2026, 1, 2),
        dividend_type="DIVIDENDO",
        payment_date=__import__("datetime").date(2026, 1, 15),
        record_date=None,
        approved_on=None,
        value_per_unit=__import__("decimal").Decimal("1.25"),
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
        raw_payload={"provider":"fixture"},
        source="brapi",
    )

    asset_result = MagicMock()
    asset_result.scalars.return_value.all.return_value = [asset]
    dividend_result = MagicMock()
    dividend_result.scalars.return_value.all.return_value = [existing]
    db.execute = AsyncMock(side_effect=[asset_result, dividend_result])

    event = SimpleNamespace(
        ex_date=existing.ex_date,
        dividend_type="DIVIDENDO",
        payment_date=existing.payment_date,
        record_date=None,
        approved_on=None,
        value_per_unit=1.25,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
        raw_payload={"provider":"fixture"},
    )
    source = SimpleNamespace(source="brapi", normalized_rows=(event,))
    collection = SimpleNamespace(ticker="PETR4", asset_type="ACAO", sources=(source,))

    result = await persist_asset_dividends_strict(db=db, collections=(collection,))

    assert result.created == 0
    assert result.updated == 0
    assert result.unchanged == 1
    db.add.assert_not_called()
