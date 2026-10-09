from unittest.mock import AsyncMock

import pytest

import app.services.b3_market_calendar_audit_service as audit_service


@pytest.mark.asyncio
async def test_monthly_audit_fetches_source_and_returns_dry_run_report(
    monkeypatch,
) -> None:
    fetch = AsyncMock(
        return_value="01 de janeiro - Confraternização Universal"
    )
    monkeypatch.setattr(audit_service, "fetch_b3_annual_calendar_page", fetch)

    result = await audit_service.run_b3_market_calendar_monthly_audit(
        source_url="https://www.b3.com.br/pt_br/noticias/calendario-2026.htm",
        source_year=2026,
    )

    fetch.assert_awaited_once()
    assert result.report.dry_run is True
    assert result.report.database_writes_executed == 0
    assert result.report.explicitly_closed_dates == ("2026-01-01",)
    assert len(result.source_sha256) == 64
