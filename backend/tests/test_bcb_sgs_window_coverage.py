from datetime import date

import httpx
import pytest

from app.integrations import bcb_sgs


@pytest.mark.asyncio
async def test_windowed_series_aborts_on_any_failed_window(monkeypatch) -> None:
    calls = 0

    async def fake_fetch_window(client, meta, start_date=None, end_date=None, limit_last=None):
        nonlocal calls
        calls += 1
        if calls == 2:
            request = httpx.Request("GET", "https://example.invalid/sgs")
            response = httpx.Response(500, request=request)
            raise httpx.HTTPStatusError(
                "synthetic window failure",
                request=request,
                response=response,
            )
        return [
            {
                "indicator": meta.indicator,
                "date": start_date,
                "value": "0.04",
                "frequency": meta.frequency,
                "value_field": meta.value_field,
                "source": "BCB_SGS",
                "sgs_code": meta.sgs_code,
            }
        ]

    monkeypatch.setattr(bcb_sgs, "_fetch_sgs_window", fake_fetch_window)

    with pytest.raises(httpx.HTTPStatusError, match="synthetic window failure"):
        await bcb_sgs.fetch_sgs_series(
            "CDI",
            start_date=date(2020, 1, 1),
            end_date=date(2022, 1, 1),
        )

    assert calls == 2


@pytest.mark.asyncio
async def test_windowed_series_deduplicates_successful_rows(monkeypatch) -> None:
    row_date = date(2026, 1, 8)

    async def fake_fetch_window(client, meta, start_date=None, end_date=None, limit_last=None):
        return [
            {
                "indicator": meta.indicator,
                "date": row_date,
                "value": "0.04",
                "frequency": meta.frequency,
                "value_field": meta.value_field,
                "source": "BCB_SGS",
                "sgs_code": meta.sgs_code,
            }
        ]

    monkeypatch.setattr(bcb_sgs, "_fetch_sgs_window", fake_fetch_window)

    rows = await bcb_sgs.fetch_sgs_series(
        "CDI",
        start_date=date(2020, 1, 1),
        end_date=date(2022, 1, 1),
    )

    assert len(rows) == 1
    assert rows[0]["date"] == row_date
