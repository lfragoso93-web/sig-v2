from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.dividend import DividendType
from app.services.dividend_backfill_service import ParsedDividendEvent, _parse_raw_dividend
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendAssetCollection,
    StrictDividendSourceCollection,
)
from app.services.pre_prod_dividends_seed_persistence import (
    DividendsSeedPersistenceError,
    persist_asset_dividends_strict,
)
from app.services.pre_prod_dividends_seed_providers import StrictYahooDividendProvider


def _result(rows):
    result = Mock()
    result.scalars.return_value.all.return_value = rows
    return result


def _db():
    asset = SimpleNamespace(id=11, ticker="AALR3", asset_type="ACAO")
    return SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(side_effect=[_result([asset]), _result([])]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )


def _source(
    source: str,
    *,
    value: float,
    payment_date: date | None,
    raw_payload: dict,
    ex_date: date = date(2019, 4, 26),
) -> StrictDividendSourceCollection:
    event = ParsedDividendEvent(
        record_date=None,
        ex_date=ex_date,
        payment_date=payment_date,
        approved_on=None,
        value_per_unit=value,
        dividend_type="DIVIDENDO",
        raw_payload=raw_payload,
    )
    return StrictDividendSourceCollection(
        source=source,
        raw_rows=1,
        normalized_rows=(event,),
        rejected_rows=0,
        empty_reason=None,
    )


@pytest.mark.asyncio
async def test_yahoo_history_date_is_normalized_as_ex_date_not_payment_date() -> None:
    async def fetcher(symbol: str):
        assert symbol == "AALR3.SA"
        return [(date(2019, 4, 26), 0.084538)]

    result = await StrictYahooDividendProvider(history_fetcher=fetcher)(
        "AALR3",
        "ACAO",
    )

    assert result.rows[0]["exDate"] == "2019-04-26"
    assert "paymentDate" not in result.rows[0]
    parsed = _parse_raw_dividend(result.rows[0])
    assert parsed is not None
    assert parsed.ex_date == date(2019, 4, 26)
    assert parsed.payment_date is None


@pytest.mark.asyncio
@pytest.mark.parametrize("reverse", [False, True])
async def test_aalr3_reconciles_declared_yahoo_truncation_deterministically(
    reverse: bool,
) -> None:
    brapi = _source(
        "brapi",
        value=0.08453883,
        payment_date=date(2019, 5, 7),
        raw_payload={"rate": 0.08453883, "paymentDate": "2019-05-07"},
    )
    yahoo = _source(
        "yfinance_history",
        value=0.084538,
        payment_date=None,
        raw_payload={
            "exDate": "2019-04-26",
            "rate": 0.084538,
            "canonicalComparison": {
                "value_per_unit": {"mode": "truncate", "scale": 6}
            },
        },
    )
    sources = (yahoo, brapi) if reverse else (brapi, yahoo)
    collection = StrictDividendAssetCollection(
        ticker="AALR3",
        asset_type="ACAO",
        sources=sources,
    )
    db = _db()

    result = await persist_asset_dividends_strict(db=db, collections=(collection,))

    assert result.created == 1
    assert result.unchanged == 1
    created = db.add.call_args.args[0]
    assert created.source == "brapi"
    assert created.payment_date == date(2019, 5, 7)
    assert created.value_per_unit == Decimal("0.08453883")
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_precision_contract_does_not_hide_material_value_conflict() -> None:
    brapi = _source(
        "brapi",
        value=0.08453983,
        payment_date=date(2019, 5, 7),
        raw_payload={"rate": 0.08453983},
    )
    yahoo = _source(
        "yfinance_history",
        value=0.084538,
        payment_date=None,
        raw_payload={
            "rate": 0.084538,
            "canonicalComparison": {
                "value_per_unit": {"mode": "truncate", "scale": 6}
            },
        },
    )
    collection = StrictDividendAssetCollection(
        ticker="AALR3",
        asset_type="ACAO",
        sources=(yahoo, brapi),
    )
    db = _db()

    with pytest.raises(
        DividendsSeedPersistenceError,
        match=r"valores divergentes: value_per_unit",
    ):
        await persist_asset_dividends_strict(db=db, collections=(collection,))

    db.flush.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_distinct_ex_dates_remain_distinct_events() -> None:
    brapi = _source(
        "brapi",
        value=0.08453883,
        payment_date=date(2019, 5, 7),
        raw_payload={"rate": 0.08453883},
    )
    yahoo = _source(
        "yfinance_history",
        value=0.084538,
        payment_date=None,
        ex_date=date(2019, 4, 29),
        raw_payload={
            "rate": 0.084538,
            "canonicalComparison": {
                "value_per_unit": {"mode": "truncate", "scale": 6}
            },
        },
    )
    collection = StrictDividendAssetCollection(
        ticker="AALR3",
        asset_type="ACAO",
        sources=(brapi, yahoo),
    )
    db = _db()

    result = await persist_asset_dividends_strict(db=db, collections=(collection,))

    assert result.created == 2
    assert db.add.call_count == 2


@pytest.mark.asyncio
async def test_declared_precision_below_six_decimals_remains_blocking() -> None:
    brapi = _source(
        "brapi",
        value=1.25,
        payment_date=date(2019, 5, 7),
        raw_payload={"rate": 1.25},
    )
    yahoo = _source(
        "yfinance_history",
        value=1.2,
        payment_date=None,
        raw_payload={
            "rate": 1.2,
            "canonicalComparison": {
                "value_per_unit": {"mode": "truncate", "scale": 1}
            },
        },
    )
    collection = StrictDividendAssetCollection(
        ticker="AALR3",
        asset_type="ACAO",
        sources=(brapi, yahoo),
    )
    db = _db()

    with pytest.raises(DividendsSeedPersistenceError):
        await persist_asset_dividends_strict(db=db, collections=(collection,))

    db.flush.assert_not_awaited()
