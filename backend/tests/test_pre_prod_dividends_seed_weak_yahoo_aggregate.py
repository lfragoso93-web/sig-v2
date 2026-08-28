from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.dividend_event_normalizer import ParsedDividendEvent
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendAssetCollection,
    StrictDividendSourceCollection,
)
from app.services.pre_prod_dividends_seed_persistence import (
    DividendsSeedPersistenceError,
    persist_asset_dividends_strict,
)


def _result(rows):
    result = Mock()
    result.scalars.return_value.all.return_value = rows
    return result


def _db():
    asset = SimpleNamespace(id=31, ticker="ALOS3", asset_type="ACAO")
    return SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(side_effect=[_result([asset]), _result([])]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )


def _source(source: str, event: ParsedDividendEvent) -> StrictDividendSourceCollection:
    return StrictDividendSourceCollection(
        source=source,
        raw_rows=1,
        normalized_rows=(event,),
        rejected_rows=0,
        empty_reason=None,
    )


def _yahoo_event() -> ParsedDividendEvent:
    return ParsedDividendEvent(
        record_date=None,
        ex_date=date(2024, 10, 7),
        payment_date=None,
        approved_on=None,
        value_per_unit=0.190623,
        dividend_type="DIVIDENDO",
        isin_code=None,
        raw_payload={
            "exDate": "2024-10-07",
            "rate": 0.190623,
            "eventSemantics": "aggregate_cash_by_ex_date",
            "canonicalComparison": {
                "value_per_unit": {"mode": "provider_quantized", "scale": 6}
            },
        },
    )


@pytest.mark.asyncio
async def test_weak_yahoo_aggregate_does_not_override_strong_brapi_event() -> None:
    brapi = ParsedDividendEvent(
        record_date=date(2024, 10, 4),
        ex_date=date(2024, 10, 7),
        payment_date=date(2024, 10, 16),
        approved_on=date(2024, 10, 1),
        value_per_unit=0.09531157,
        dividend_type="DIVIDENDO",
        isin_code="BRALOSACNOR5",
        raw_payload={"rate": 0.09531157},
    )
    collection = StrictDividendAssetCollection(
        ticker="ALOS3",
        asset_type="ACAO",
        sources=(
            _source("brapi", brapi),
            _source("yfinance_history", _yahoo_event()),
        ),
    )
    db = _db()

    result = await persist_asset_dividends_strict(db=db, collections=(collection,))

    assert result.created == 1
    assert result.unchanged == 1
    created = db.add.call_args.args[0]
    assert created.source == "brapi"
    assert created.value_per_unit == Decimal("0.09531157")
    assert created.payment_date == date(2024, 10, 16)


@pytest.mark.asyncio
async def test_weak_yahoo_aggregate_still_blocks_when_primary_identity_is_weak() -> None:
    brapi = ParsedDividendEvent(
        record_date=None,
        ex_date=date(2024, 10, 7),
        payment_date=None,
        approved_on=None,
        value_per_unit=0.09531157,
        dividend_type="DIVIDENDO",
        isin_code=None,
        raw_payload={"rate": 0.09531157},
    )
    collection = StrictDividendAssetCollection(
        ticker="ALOS3",
        asset_type="ACAO",
        sources=(
            _source("brapi", brapi),
            _source("yfinance_history", _yahoo_event()),
        ),
    )
    db = _db()

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante entre fontes",
    ):
        await persist_asset_dividends_strict(db=db, collections=(collection,))

    db.flush.assert_not_awaited()
