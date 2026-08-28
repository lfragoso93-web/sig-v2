from datetime import date

import pytest

from app.services.dividend_event_normalizer import ParsedDividendEvent
from app.services.pre_prod_dividends_seed_persistence import (
    DividendsSeedPersistenceError,
    _collapse_estimated_payment_components,
)


def _event(
    value: float,
    *,
    estimated: bool = False,
    payment_date: date | None = None,
    approved_on: date | None = None,
    isin_code: str | None = None,
    ex_date: date = date(2025, 4, 17),
    record_date: date = date(2025, 4, 16),
    dividend_type: str = "RENDIMENTO",
) -> ParsedDividendEvent:
    return ParsedDividendEvent(
        record_date=record_date,
        ex_date=ex_date,
        payment_date=payment_date or date(2025, 5, 20),
        approved_on=approved_on,
        value_per_unit=value,
        dividend_type=dividend_type,
        isin_code=isin_code,
        raw_payload={
            "remarks": "csv:payment_date_estimated" if estimated else "",
        },
    )


def test_single_estimated_event_is_retained_without_false_conflict() -> None:
    event = _event(0.01706013, estimated=True, payment_date=date(2025, 4, 16))

    retained, collapsed = _collapse_estimated_payment_components((event,))

    assert retained == (event,)
    assert collapsed == ()


def test_distinct_estimated_and_canonical_pair_are_both_retained() -> None:
    canonical = _event(0.02152467)
    estimated = _event(
        0.01706013,
        estimated=True,
        payment_date=date(2025, 4, 16),
    )

    retained, collapsed = _collapse_estimated_payment_components(
        (canonical, estimated)
    )

    assert retained == (canonical, estimated)
    assert collapsed == ()


def test_equivalent_estimated_and_canonical_pair_remains_blocking() -> None:
    canonical = _event(0.02152467)
    estimated = _event(
        0.02152467,
        estimated=True,
        payment_date=date(2025, 4, 16),
    )

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante na mesma fonte",
    ):
        _collapse_estimated_payment_components((canonical, estimated))


def test_taee11_like_canonical_aggregate_is_collapsed_to_components() -> None:
    common = {
        "payment_date": date(2022, 5, 31),
        "isin_code": "BRTAEECDAM10",
        "ex_date": date(2022, 5, 10),
        "record_date": date(2022, 5, 9),
        "dividend_type": "DIVIDENDO",
    }
    component_a = _event(
        1.8963242,
        approved_on=date(2022, 5, 3),
        **common,
    )
    aggregate = _event(
        2.323063,
        approved_on=None,
        **common,
    )
    component_b = _event(
        0.42673913,
        approved_on=date(2022, 5, 3),
        **common,
    )

    retained, collapsed = _collapse_estimated_payment_components(
        (component_a, aggregate, component_b)
    )

    assert retained == (component_a, component_b)
    assert collapsed == (aggregate,)


def test_three_canonical_events_without_structural_aggregate_remain_blocking() -> None:
    events = (
        _event(1.8963242, approved_on=date(2022, 5, 3)),
        _event(2.323063, approved_on=date(2022, 5, 3)),
        _event(0.42673913, approved_on=date(2022, 5, 3)),
    )

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante na mesma fonte",
    ):
        _collapse_estimated_payment_components(events)


def test_three_canonical_events_with_wrong_sum_remain_blocking() -> None:
    common = {
        "payment_date": date(2022, 5, 31),
        "isin_code": "BRTAEECDAM10",
        "ex_date": date(2022, 5, 10),
        "record_date": date(2022, 5, 9),
        "dividend_type": "DIVIDENDO",
    }
    events = (
        _event(1.8963242, approved_on=date(2022, 5, 3), **common),
        _event(2.5, approved_on=None, **common),
        _event(0.42673913, approved_on=date(2022, 5, 3), **common),
    )

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante na mesma fonte",
    ):
        _collapse_estimated_payment_components(events)
