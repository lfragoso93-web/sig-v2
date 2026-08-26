from datetime import date
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


def _db(asset):
    return SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(side_effect=[_result([asset]), _result([])]),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        delete=AsyncMock(),
    )


def _collection(*, canonical: float, yahoo: float):
    brapi = ParsedDividendEvent(
        record_date=date(2019, 4, 25),
        ex_date=date(2019, 4, 26),
        payment_date=None,
        approved_on=None,
        value_per_unit=canonical,
        dividend_type="DIVIDENDO",
        raw_payload={"rate": canonical},
    )
    yahoo_event = ParsedDividendEvent(
        record_date=None,
        ex_date=date(2019, 4, 26),
        payment_date=None,
        approved_on=None,
        value_per_unit=yahoo,
        dividend_type="DIVIDENDO",
        raw_payload={
            "rate": yahoo,
            "eventSemantics": "aggregate_cash_by_ex_date",
            "canonicalComparison": {
                "value_per_unit": {
                    "mode": "provider_quantized",
                    "scale": 6,
                }
            },
        },
    )
    return StrictDividendAssetCollection(
        ticker="TEST3",
        asset_type="ACAO",
        sources=(
            StrictDividendSourceCollection(
                source="brapi",
                raw_rows=1,
                normalized_rows=(brapi,),
                rejected_rows=0,
                empty_reason=None,
            ),
            StrictDividendSourceCollection(
                source="yfinance_history",
                raw_rows=1,
                normalized_rows=(yahoo_event,),
                rejected_rows=0,
                empty_reason=None,
            ),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("canonical", "yahoo"),
    [
        (0.24956495, 0.249565),  # AFLT3/2011
        (0.08453883, 0.084538),  # AALR3/2019
        (0.19024149, 0.190242),  # AFLT3/2016
    ],
)
async def test_provider_quantized_accepts_values_within_declared_resolution(
    canonical: float,
    yahoo: float,
) -> None:
    asset = SimpleNamespace(id=7, ticker="TEST3", asset_type="ACAO")
    db = _db(asset)

    result = await persist_asset_dividends_strict(
        db=db,
        collections=(_collection(canonical=canonical, yahoo=yahoo),),
    )

    assert result.created == 1
    assert result.unchanged == 1
    db.add.assert_called_once()
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("canonical", "yahoo"),
    [
        (0.08453900, 0.084538),  # limite exato de 1e-6 continua bloqueante
        (0.08453983, 0.084538),  # acima da resolução declarada
    ],
)
async def test_provider_quantized_rejects_value_outside_declared_resolution(
    canonical: float,
    yahoo: float,
) -> None:
    asset = SimpleNamespace(id=7, ticker="TEST3", asset_type="ACAO")
    db = _db(asset)

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante entre fontes",
    ):
        await persist_asset_dividends_strict(
            db=db,
            collections=(_collection(canonical=canonical, yahoo=yahoo),),
        )

    db.flush.assert_not_awaited()
