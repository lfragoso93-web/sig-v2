from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.services.dividend_backfill_service import (
    ParsedDividendEvent,
    _parse_raw_dividend,
)
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


@pytest.mark.asyncio
async def test_abev3_same_ex_date_jcps_from_brapi_remain_distinct() -> None:
    asset = SimpleNamespace(id=12, ticker="ABEV3", asset_type="ACAO")
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(side_effect=[_result([asset]), _result([])]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    events = (
        ParsedDividendEvent(
            record_date=date(2025, 12, 18),
            ex_date=date(2025, 12, 19),
            payment_date=date(2026, 12, 31),
            approved_on=None,
            value_per_unit=0.269,
            dividend_type="JCP",
            raw_payload={"paymentDate": "2026-12-31", "rate": 0.269},
        ),
        ParsedDividendEvent(
            record_date=date(2025, 12, 18),
            ex_date=date(2025, 12, 19),
            payment_date=date(2026, 4, 6),
            approved_on=None,
            value_per_unit=0.075,
            dividend_type="JCP",
            raw_payload={"paymentDate": "2026-04-06", "rate": 0.075},
        ),
    )
    collection = StrictDividendAssetCollection(
        ticker="ABEV3",
        asset_type="ACAO",
        sources=(
            StrictDividendSourceCollection(
                source="brapi",
                raw_rows=2,
                normalized_rows=events,
                rejected_rows=0,
                empty_reason=None,
            ),
        ),
    )

    result = await persist_asset_dividends_strict(db=db, collections=(collection,))

    assert result.created == 2
    assert result.updated == 0
    assert db.add.call_count == 2
    created = [item.args[0] for item in db.add.call_args_list]
    assert {item.payment_date for item in created} == {
        date(2026, 4, 6),
        date(2026, 12, 31),
    }
    assert {item.value_per_unit for item in created} == {
        Decimal("0.075"),
        Decimal("0.269"),
    }


@pytest.mark.asyncio
async def test_abev3_estimated_components_collapse_into_canonical_total() -> None:
    asset = SimpleNamespace(id=12, ticker="ABEV3", asset_type="ACAO")
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(side_effect=[_result([asset]), _result([])]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    def event(value: float, remarks: str) -> ParsedDividendEvent:
        return ParsedDividendEvent(
            record_date=date(2015, 2, 27),
            ex_date=date(2015, 3, 2),
            payment_date=date(2015, 3, 31),
            approved_on=date(2015, 2, 23) if remarks else None,
            value_per_unit=value,
            dividend_type="JCP",
            remarks=remarks,
            raw_payload={"rate": value, "remarks": remarks},
        )

    collection = StrictDividendAssetCollection(
        ticker="ABEV3",
        asset_type="ACAO",
        sources=(
            StrictDividendSourceCollection(
                source="brapi",
                raw_rows=3,
                normalized_rows=(
                    event(0.03, "csv:payment_date_estimated"),
                    event(0.09, ""),
                    event(0.06, "csv:payment_date_estimated"),
                ),
                rejected_rows=0,
                empty_reason=None,
            ),
        ),
    )

    result = await persist_asset_dividends_strict(db=db, collections=(collection,))

    assert result.created == 1
    assert result.unchanged == 2
    created = db.add.call_args.args[0]
    assert created.value_per_unit == Decimal("0.09")
    assert created.remarks == ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rows",
    [
        (
            (0.03, "csv:payment_date_estimated"),
            (0.10, ""),
            (0.06, "csv:payment_date_estimated"),
        ),
        ((0.03, "csv:payment_date_estimated"), (0.03, "")),
        ((0.03, ""), (0.09, ""), (0.06, "")),
    ],
)
async def test_estimated_component_policy_does_not_hide_other_conflicts(
    rows: tuple[tuple[float, str], ...],
) -> None:
    asset = SimpleNamespace(id=12, ticker="ABEV3", asset_type="ACAO")
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(side_effect=[_result([asset]), _result([])]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    events = tuple(
        ParsedDividendEvent(
            record_date=date(2015, 2, 27),
            ex_date=date(2015, 3, 2),
            payment_date=date(2015, 3, 31),
            approved_on=None,
            value_per_unit=value,
            dividend_type="JCP",
            remarks=remarks,
            raw_payload={"rate": value, "remarks": remarks},
        )
        for value, remarks in rows
    )
    collection = StrictDividendAssetCollection(
        ticker="ABEV3",
        asset_type="ACAO",
        sources=(
            StrictDividendSourceCollection(
                source="brapi",
                raw_rows=len(events),
                normalized_rows=events,
                rejected_rows=0,
                empty_reason=None,
            ),
        ),
    )

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante na mesma fonte",
    ):
        await persist_asset_dividends_strict(db=db, collections=(collection,))
