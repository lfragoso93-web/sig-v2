from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.canonical_dividend_entitlement import EntitlementReason
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)


class Result:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values

    def scalars(self):
        return self


class Session:
    def __init__(self, *results):
        self.results = iter(results)
        self.calls = 0

    async def execute(self, _statement):
        self.calls += 1
        return Result(next(self.results))


def asset(**overrides):
    values = {"ticker": "ABCD3", "asset_type": "ACAO", "currency": "BRL"}
    values.update(overrides)
    return SimpleNamespace(**values)


def event(**overrides):
    values = {
        "id": 7,
        "record_date": date(2026, 1, 9),
        "ex_date": date(2026, 1, 12),
        "payment_date": date(2026, 1, 20),
        "dividend_type": "DIVIDENDO",
        "value_per_unit": Decimal("1.25"),
        "approved_on": None,
        "gross_value_per_unit": None,
        "factor": None,
        "complete_factor": None,
        "isin_code": None,
        "asset_issued": None,
        "related_to": None,
        "remarks": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def transaction(**overrides):
    values = {
        "id": 1,
        "ticker": "ABCD3",
        "asset_type": "ACAO",
        "operation": "buy",
        "quantity": 10,
        "date": date(2026, 1, 2),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_loads_global_event_and_derives_historical_right_read_only():
    db = Session([(event(), asset())], [transaction()])

    results = await load_portfolio_dividend_entitlements(db, 3)

    assert db.calls == 2
    assert len(results) == 1
    assert results[0].ticker == "ABCD3"
    assert results[0].entitlement.eligible_quantity == Decimal("10")
    assert results[0].entitlement.net_amount == Decimal("12.50")


@pytest.mark.asyncio
async def test_uses_ticker_and_asset_type_to_separate_movements():
    db = Session(
        [(event(), asset())],
        [
            transaction(asset_type="FII", quantity=99),
            transaction(asset_type="ACAO", quantity=4),
        ],
    )

    results = await load_portfolio_dividend_entitlements(db, 3)

    assert results[0].entitlement.eligible_quantity == Decimal("4")


@pytest.mark.asyncio
async def test_returns_empty_without_loading_movements_when_no_event_matches():
    db = Session([])

    assert await load_portfolio_dividend_entitlements(db, 3) == []
    assert db.calls == 1


@pytest.mark.asyncio
async def test_keeps_event_without_record_date_non_materializable():
    db = Session(
        [(event(record_date=None), asset())],
        [transaction(date=date(2026, 1, 12))],
    )

    results = await load_portfolio_dividend_entitlements(db, 3)

    assert (
        results[0].entitlement.reason
        is EntitlementReason.AMBIGUOUS_ENTITLEMENT_DATE
    )


@pytest.mark.asyncio
async def test_rejects_asset_without_explicit_currency():
    db = Session([(event(), asset(currency=None))], [transaction()])

    with pytest.raises(ValueError, match="has no currency"):
        await load_portfolio_dividend_entitlements(db, 3)
