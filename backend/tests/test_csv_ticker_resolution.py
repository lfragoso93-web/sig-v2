from datetime import date
from typing import cast

import pytest

from app.services.csv_ticker_resolution import enrich_csv_dry_run_with_ticker_resolution
from app.services.ticker_resolution_service import ResolvedTicker, TickerResolutionService


class FakeResolutionService:
    def __init__(self, resolutions: dict[str, ResolvedTicker]) -> None:
        self.resolutions = resolutions
        self.received: list[str] = []

    async def resolve_many(self, tickers: list[str]) -> dict[str, ResolvedTicker]:
        self.received = tickers
        return self.resolutions


def _result(ticker: str, operation_date: str | None = None) -> dict:
    row = {
        "row_num": 2,
        "errors": [],
        "warnings": [],
        "status": "valid",
        "ticker": ticker,
    }
    if operation_date is not None:
        row["date"] = operation_date
    return {
        "success": True,
        "imported_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "global_errors": [],
        "rows": [row],
    }


def _renamed_resolution() -> dict[str, ResolvedTicker]:
    return {
        "VVAR3": ResolvedTicker(
            requested_ticker="VVAR3",
            current_ticker="BHIA3",
            changed=True,
            status="renamed",
            effective_date=date(2023, 9, 20),
        )
    }


@pytest.mark.asyncio
async def test_dry_run_bloqueia_ticker_renomeado_sem_data_da_operacao() -> None:
    fake = FakeResolutionService(_renamed_resolution())

    enriched = await enrich_csv_dry_run_with_ticker_resolution(
        _result("VVAR3"),
        service=cast(TickerResolutionService, fake),
    )

    assert enriched["success"] is False
    assert enriched["skipped_count"] == 1
    assert enriched["rows"][0]["status"] == "warning"
    assert enriched["rows"][0]["resolved_ticker"] == "BHIA3"
    assert "Atualize o CSV" in enriched["rows"][0]["warnings"][0]


@pytest.mark.asyncio
async def test_dry_run_aceita_ticker_antigo_antes_da_data_efetiva() -> None:
    fake = FakeResolutionService(_renamed_resolution())

    enriched = await enrich_csv_dry_run_with_ticker_resolution(
        _result("VVAR3", "2023-09-19"),
        service=cast(TickerResolutionService, fake),
    )

    assert enriched["success"] is True
    assert enriched["skipped_count"] == 0
    assert enriched["rows"][0]["status"] == "valid"
    assert enriched["rows"][0]["warnings"] == []
    assert enriched["rows"][0]["resolved_ticker"] == "BHIA3"
    assert enriched["rows"][0]["ticker_resolution_status"] == "historical_alias"


@pytest.mark.asyncio
@pytest.mark.parametrize("operation_date", ["2023-09-20", "2023-09-21"])
async def test_dry_run_bloqueia_ticker_antigo_na_data_efetiva_ou_depois(
    operation_date: str,
) -> None:
    fake = FakeResolutionService(_renamed_resolution())

    enriched = await enrich_csv_dry_run_with_ticker_resolution(
        _result("VVAR3", operation_date),
        service=cast(TickerResolutionService, fake),
    )

    assert enriched["success"] is False
    assert enriched["skipped_count"] == 1
    assert enriched["rows"][0]["status"] == "warning"


@pytest.mark.asyncio
async def test_dry_run_preserva_ticker_atual() -> None:
    result = _result("PETR4")
    fake = FakeResolutionService({
        "PETR4": ResolvedTicker(
            requested_ticker="PETR4",
            current_ticker="PETR4",
            changed=False,
            status="active",
        )
    })

    enriched = await enrich_csv_dry_run_with_ticker_resolution(
        result,
        service=cast(TickerResolutionService, fake),
    )

    assert enriched["success"] is True
    assert enriched["skipped_count"] == 0
    assert "resolved_ticker" not in enriched["rows"][0]


def test_service_normaliza_tickers_sem_duplicar() -> None:
    values = TickerResolutionService._normalize([" petr4 ", "PETR4", "vale3", ""])
    assert values == ["PETR4", "VALE3"]
