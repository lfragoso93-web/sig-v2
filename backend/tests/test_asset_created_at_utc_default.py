from datetime import datetime

from app.core.datetime_utils import utc_now_naive
from app.models.asset import Asset


def test_utc_now_naive_preserves_naive_utc_contract() -> None:
    value = utc_now_naive()

    assert isinstance(value, datetime)
    assert value.tzinfo is None


def test_asset_created_at_uses_shared_utc_naive_default() -> None:
    default_callable = Asset.__table__.c.created_at.default.arg

    assert default_callable is utc_now_naive
