import pytest

from app.services.config_service import validate_system_config_value


def test_accepts_blank_calendar_overrides_for_environment_fallback() -> None:
    validate_system_config_value("market_calendar.b3_source_url", "")
    validate_system_config_value("market_calendar.b3_source_year", "")


def test_rejects_non_b3_calendar_source_url() -> None:
    with pytest.raises(ValueError, match="official HTTPS host"):
        validate_system_config_value(
            "market_calendar.b3_source_url",
            "https://example.test/calendar",
        )


@pytest.mark.parametrize("value", ("202", "20260", "next-year"))
def test_rejects_invalid_b3_calendar_source_year(value: str) -> None:
    with pytest.raises(ValueError, match="four-digit year"):
        validate_system_config_value("market_calendar.b3_source_year", value)
