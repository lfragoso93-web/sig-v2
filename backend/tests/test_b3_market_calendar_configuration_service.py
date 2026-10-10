from types import SimpleNamespace

import pytest

import app.services.b3_market_calendar_configuration_service as config_service


@pytest.mark.asyncio
async def test_uses_superadmin_override_before_environment(
    monkeypatch,
) -> None:
    values = {
        config_service.B3_CALENDAR_SOURCE_URL_KEY: (
            "https://www.b3.com.br/pt_br/noticias/calendar-2027.htm"
        ),
        config_service.B3_CALENDAR_SOURCE_YEAR_KEY: "2027",
    }

    async def get_config(_, key: str) -> str | None:
        return values.get(key)

    monkeypatch.setattr(config_service, "get_config", get_config)
    result = await (
        config_service.resolve_b3_market_calendar_audit_configuration(
            object(),
            runtime_settings=SimpleNamespace(
                B3_MARKET_CALENDAR_SOURCE_URL="https://www.b3.com.br/env.htm",
                B3_MARKET_CALENDAR_SOURCE_YEAR=2026,
            ),
        )
    )

    assert result.source_year == 2027
    assert result.source_origin == "system_config"


@pytest.mark.asyncio
async def test_uses_environment_when_superadmin_override_is_empty(
    monkeypatch,
) -> None:
    async def get_config(_, __: str) -> str:
        return ""

    monkeypatch.setattr(config_service, "get_config", get_config)
    result = await (
        config_service.resolve_b3_market_calendar_audit_configuration(
            object(),
            runtime_settings=SimpleNamespace(
                B3_MARKET_CALENDAR_SOURCE_URL="https://www.b3.com.br/env.htm",
                B3_MARKET_CALENDAR_SOURCE_YEAR=2026,
            ),
        )
    )

    assert result.source_year == 2026
    assert result.source_origin == "environment"
