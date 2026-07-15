from datetime import date, datetime, timezone

from app.models.asset import AssetType
from app.services.asset_price_coverage_service import CoverageStatus, build_missing_ranges
from app.services.asset_price_gap_sync_service import MissingPriceRange, _empty_status, normalize_provider_symbol
from app.services.treasury_history_rebuild_service import extract_treasury_history


def test_extract_treasury_history_from_symbol_map():
    payload = {
        "results": {
            "tesouro-selic-01032031": {
                "prices": [
                    {"date": "2026-07-14", "buyPrice": 15234.56},
                    {"date": "2026-07-15", "buyPrice": 15240.12},
                ]
            }
        }
    }

    rows = extract_treasury_history(payload, ["tesouro-selic-01032031"])

    assert [value for _, value in rows["tesouro-selic-01032031"]] == [15234.56, 15240.12]


def test_extract_treasury_history_from_nested_items():
    payload = {
        "data": [
            {
                "symbol": "tesouro-prefixado-01012028",
                "historicalData": [
                    {"referenceDate": "15/07/2026", "unitPrice": "1.234,56"}
                ],
            }
        ]
    }

    rows = extract_treasury_history(payload, ["tesouro-prefixado-01012028"])

    assert len(rows["tesouro-prefixado-01012028"]) == 1
    assert rows["tesouro-prefixado-01012028"][0][1] == 1234.56


def test_crypto_provider_symbol_is_yahoo_symbol():
    assert normalize_provider_symbol("BITCOIN", AssetType.CRIPTO) == "BTC-USD"
    assert normalize_provider_symbol("CARDANO", AssetType.CRIPTO) == "ADA-USD"


def test_empty_range_status_distinguishes_edges():
    assert _empty_status(MissingPriceRange(date(1900, 1, 1), date(2020, 1, 1), "missing_start")) == "HISTORY_START_EXHAUSTED"
    assert _empty_status(MissingPriceRange(date(2026, 7, 1), date(2026, 7, 15), "stale_end")) == "HISTORY_END_UNAVAILABLE"
    assert _empty_status(MissingPriceRange(date(1900, 1, 1), date(2026, 7, 15), "missing_all")) == "HISTORY_UNAVAILABLE"


def test_end_unavailable_suppresses_stale_range():
    ranges = build_missing_ranges(
        status=CoverageStatus.STALE,
        required_from=date(2020, 1, 1),
        required_to=date(2026, 7, 15),
        first_price_date=date(2020, 1, 1),
        last_price_date=date(2026, 6, 30),
        provider_status="HISTORY_END_UNAVAILABLE",
    )

    assert ranges == ()


def test_history_unavailable_suppresses_both_edges():
    ranges = build_missing_ranges(
        status=CoverageStatus.PARTIAL_BOTH,
        required_from=date(1900, 1, 1),
        required_to=date(2026, 7, 15),
        first_price_date=date(2020, 1, 1),
        last_price_date=date(2026, 6, 30),
        provider_status="HISTORY_UNAVAILABLE",
    )

    assert ranges == ()
