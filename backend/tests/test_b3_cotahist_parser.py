from decimal import Decimal

from app.integrations.b3_cotahist import parse_cotahist_record


def _record(**overrides: str) -> str:
    fields = {
        "record_type": "01",
        "date": "20260828",
        "bdi": "02",
        "ticker": "ALOS3",
        "market": "010",
        "name": "ALLOS",
        "specification": "ON      NM",
        "term": "   ",
        "currency": "R$  ",
        "open": "0000000012345",
        "high": "0000000012500",
        "low": "0000000012200",
        "average": "0000000012350",
        "close": "0000000012400",
        "bid": "0000000012390",
        "ask": "0000000012410",
        "trades": "00123",
        "quantity": "000000000001234567",
        "volume": "000000000987654321",
        "exercise": "0000000000000",
        "correction": "0",
        "expiration": "00000000",
        "quotation_factor": "0000001",
        "points": "0000000000000",
        "isin": "BRALOSACNOR5",
        "distribution": "001",
    }
    fields.update(overrides)
    line = (
        f"{fields['record_type']:<2.2}"
        f"{fields['date']:<8.8}"
        f"{fields['bdi']:<2.2}"
        f"{fields['ticker']:<12.12}"
        f"{fields['market']:<3.3}"
        f"{fields['name']:<12.12}"
        f"{fields['specification']:<10.10}"
        f"{fields['term']:<3.3}"
        f"{fields['currency']:<4.4}"
        f"{fields['open']:>13.13}"
        f"{fields['high']:>13.13}"
        f"{fields['low']:>13.13}"
        f"{fields['average']:>13.13}"
        f"{fields['close']:>13.13}"
        f"{fields['bid']:>13.13}"
        f"{fields['ask']:>13.13}"
        f"{fields['trades']:>5.5}"
        f"{fields['quantity']:>18.18}"
        f"{fields['volume']:>18.18}"
        f"{fields['exercise']:>13.13}"
        f"{fields['correction']:<1.1}"
        f"{fields['expiration']:<8.8}"
        f"{fields['quotation_factor']:>7.7}"
        f"{fields['points']:>13.13}"
        f"{fields['isin']:<12.12}"
        f"{fields['distribution']:<3.3}"
    )
    assert len(line) == 245
    return line


def test_parser_extracts_only_sgi_canonical_fields_with_decimal() -> None:
    record = parse_cotahist_record(_record())

    assert record is not None
    assert record.ticker == "ALOS3"
    assert record.market_type == "010"
    assert record.short_name == "ALLOS"
    assert record.specification == "ON      NM"
    assert record.currency == "R$"
    assert record.open == Decimal("123.45")
    assert record.high == Decimal("125.00")
    assert record.low == Decimal("122.00")
    assert record.close == Decimal("124.00")
    assert record.volume == Decimal("9876543.21")
    assert record.quotation_factor == 1
    assert record.isin == "BRALOSACNOR5"

    assert set(record.__dataclass_fields__) == {
        "timestamp",
        "ticker",
        "market_type",
        "short_name",
        "specification",
        "currency",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quotation_factor",
        "isin",
    }


def test_parser_rejects_non_spot_market_and_invalid_record() -> None:
    assert parse_cotahist_record(_record(market="030")) is None
    assert parse_cotahist_record(_record(record_type="99")) is None
    assert parse_cotahist_record("short") is None


def test_parser_rejects_missing_identity_or_non_positive_close() -> None:
    assert parse_cotahist_record(_record(ticker="")) is None
    assert parse_cotahist_record(_record(close="0000000000000")) is None
