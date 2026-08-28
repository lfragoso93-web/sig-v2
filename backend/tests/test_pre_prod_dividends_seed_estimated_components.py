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
) -> ParsedDividendEvent:
    return ParsedDividendEvent(
        record_date=date(2025, 4, 16),
        ex_date=date(2025, 4, 17),
        payment_date=payment_date or date(2025, 5, 20),
        approved_on=None,
        value_per_unit=value,
        dividend_type="RENDIMENTO",
        raw_payload={
            "remarks": "csv:payment_date_estimated" if estimated else "",
        },
    )


def test_single_estimated_event_is_retained_without_false_conflict() -> None:
    event = _event(0.01706013, estimated=True, payment_date=date(2025, 4, 16))

    retained, collapsed = _collapse_estimated_payment_components((event,))

    assert retained == (event,)
    assert collapsed == ()


def test_estimated_and_canonical_pair_remains_blocking_when_not_equivalent() -> None:
    events = (
        _event(0.02152467),
        _event(0.01706013, estimated=True, payment_date=date(2025, 4, 16)),
    )

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante na mesma fonte",
    ):
        _collapse_estimated_payment_components(events)


def test_three_canonical_events_remain_blocking() -> None:
    events = (
        _event(1.8963242),
        _event(2.323063),
        _event(0.42673913),
    )

    with pytest.raises(
        DividendsSeedPersistenceError,
        match="evento global conflitante na mesma fonte",
    ):
        _collapse_estimated_payment_components(events)
