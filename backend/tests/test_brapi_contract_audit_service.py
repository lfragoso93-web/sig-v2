from datetime import date

import pytest

from app.integrations.brapi_v2_client import TickerCoverage, TickerRename
from app.services.brapi_contract_audit_service import audit_brapi_pro_contract


class FakeBrapiClient:
    async def get_ticker_coverage(self, symbols):
        return [
            TickerCoverage(
                requested_symbol="ITSA4",
                symbol="ITSA4",
                changed=False,
                status="active",
                asset_type="stock",
                sub_type="stock",
                available_data={"stockDividends": True},
            ),
            TickerCoverage(
                requested_symbol="MXRF11",
                symbol="MXRF11",
                changed=False,
                status="active",
                asset_type="fund",
                sub_type="fii",
                available_data={"stockDividends": False, "fiiDividends": True},
            ),
        ]

    async def list_ticker_renames(self, **_kwargs):
        return [
            TickerRename(
                old_symbol="VVAR3",
                new_symbol="BHIA3",
                canonical_symbol="BHIA3",
                effective_date=date(2021, 8, 16),
            )
        ]


@pytest.mark.asyncio
async def test_contract_audit_builds_sanitized_corporate_evidence() -> None:
    calls = []

    async def fetcher(ticker: str, date_from: date, date_to: date):
        calls.append((ticker, date_from, date_to))
        return {
            "results": [
                {
                    "symbol": "ITSA4",
                    "data": {
                        "cashDividends": [
                            {
                                "rate": 0.15,
                                "lastDatePrior": "2025-01-02",
                                "authorizationToken": "must-not-leak",
                            }
                        ],
                        "stockDividends": [
                            {
                                "factor": 1.1,
                                "lastDatePrior": "2025-02-03",
                                "eventType": "stock bonus",
                            }
                        ],
                        "subscriptions": [
                            {
                                "lastDatePrior": "2025-03-04",
                                "type": "subscription",
                            }
                        ],
                    },
                }
            ]
        }

    report = await audit_brapi_pro_contract(
        tickers=[" itsa4 ", "MXRF11", "itsa4"],
        date_from=date(2000, 1, 1),
        date_to=date(2026, 7, 31),
        client=FakeBrapiClient(),  # type: ignore[arg-type]
        dividend_fetcher=fetcher,
    )

    assert len(calls) == 1
    assert report.requested_tickers == ("ITSA4", "MXRF11")
    assert report.rename_count == 1
    stock = report.evidence[0]
    assert stock.endpoint_called is True
    assert stock.event_counts == {
        "cashDividends": 1,
        "stockDividends": 1,
        "subscriptions": 1,
    }
    assert "stockDividends.factor" in stock.observed_field_paths
    assert (
        stock.sanitized_samples["cashDividends"]["authorizationToken"] == "[REDACTED]"
    )
    assert stock.split_evidence == ()

    fii = report.evidence[1]
    assert fii.endpoint_called is False
    assert fii.error == "coverage_without_stock_dividends"


@pytest.mark.asyncio
async def test_contract_audit_flags_explicit_split_evidence() -> None:
    class Client:
        async def get_ticker_coverage(self, _symbols):
            return [
                TickerCoverage(
                    requested_symbol="TEST3",
                    symbol="TEST3",
                    changed=False,
                    status="active",
                    asset_type="stock",
                    sub_type="stock",
                    available_data={"stockDividends": True},
                )
            ]

        async def list_ticker_renames(self, **_kwargs):
            return []

    async def fetcher(_ticker: str, _date_from: date, _date_to: date):
        return {
            "results": [
                {
                    "symbol": "TEST3",
                    "data": {
                        "cashDividends": [],
                        "stockDividends": [
                            {
                                "eventType": "DESDOBRAMENTO",
                                "factor": 2,
                                "lastDatePrior": "2024-01-01",
                            }
                        ],
                        "subscriptions": [],
                    },
                }
            ]
        }

    report = await audit_brapi_pro_contract(
        tickers=["TEST3"],
        date_from=date(2000, 1, 1),
        date_to=date(2026, 7, 31),
        client=Client(),  # type: ignore[arg-type]
        dividend_fetcher=fetcher,
    )

    assert report.evidence[0].split_evidence == ("stockDividends:desdobramento",)


@pytest.mark.asyncio
async def test_contract_audit_rejects_inverted_window() -> None:
    with pytest.raises(ValueError, match="date_from"):
        await audit_brapi_pro_contract(
            tickers=["PETR4"],
            date_from=date(2026, 1, 1),
            date_to=date(2000, 1, 1),
            client=FakeBrapiClient(),  # type: ignore[arg-type]
            dividend_fetcher=lambda *_args: None,  # type: ignore[arg-type]
        )
