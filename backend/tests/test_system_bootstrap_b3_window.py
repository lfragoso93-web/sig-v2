from datetime import date
from types import SimpleNamespace

import pytest

from app.services.system_bootstrap_service import _resolve_b3_bootstrap_window


def test_b3_bootstrap_window_defaults_to_today_year_and_today_cutoff() -> None:
    window = _resolve_b3_bootstrap_window(
        SimpleNamespace(
            B3_BOOTSTRAP_START_YEAR=None,
        ),
        date(2026, 8, 29),
    )

    assert window.start_year == 2026
    assert window.end_year == 2026
    assert window.cutoff_date == date(2026, 8, 29)


def test_b3_bootstrap_window_uses_configured_start_year_only() -> None:
    window = _resolve_b3_bootstrap_window(
        SimpleNamespace(
            B3_BOOTSTRAP_START_YEAR=2020,
        ),
        date(2026, 8, 29),
    )

    assert window.start_year == 2020
    assert window.end_year == 2026
    assert window.cutoff_date == date(2026, 8, 29)


def test_b3_bootstrap_window_rejects_inverted_years() -> None:
    with pytest.raises(ValueError, match="START_YEAR"):
        _resolve_b3_bootstrap_window(
            SimpleNamespace(
                B3_BOOTSTRAP_START_YEAR=2027,
            ),
            date(2026, 8, 29),
        )
