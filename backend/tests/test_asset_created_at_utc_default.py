from datetime import datetime

from app.core.datetime_utils import utc_now_naive
from app.models.asset import Asset


def test_utc_now_naive_preserves_naive_utc_contract() -> None:
    value = utc_now_naive()

    assert isinstance(value, datetime)
    assert value.tzinfo is None


def test_asset_created_at_default_preserves_naive_utc_contract() -> None:
    default_callable = Asset.__table__.c.created_at.default.arg
    value = default_callable(None)

    assert isinstance(value, datetime)
    assert value.tzinfo is None
