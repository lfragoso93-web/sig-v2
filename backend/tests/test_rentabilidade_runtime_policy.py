from datetime import date

from app.services.rentabilidade_runtime_policy import utc_today


def test_utc_today_returns_calendar_date():
    result = utc_today()

    assert isinstance(result, date)
