from app.core.config import Settings


def make_settings(**values):
    return Settings(_env_file=None, **values)


def test_generic_provider_variables_populate_legacy_attributes():
    settings = make_settings(
        QUOTES_PROVIDER_TOKEN="new-token",
        INTL_DATA_KEY="new-intl-key",
        MARKET_DATA_BASE_URL="https://market.example/api",
        MARKET_DATA_RATE_LIMIT=3.5,
        MARKET_DATA_RATE_BURST=8,
    )

    assert settings.QUOTES_PROVIDER_TOKEN == "new-token"
    assert settings.BRAPI_TOKEN == "new-token"
    assert settings.INTL_DATA_KEY == "new-intl-key"
    assert settings.ALPHA_VANTAGE_API_KEY == "new-intl-key"
    assert settings.MARKET_DATA_BASE_URL == "https://market.example/api"
    assert settings.BRAPI_BASE_URL == "https://market.example/api"
    assert settings.MARKET_DATA_RATE_LIMIT == 3.5
    assert settings.BRAPI_RATE_LIMIT == 3.5
    assert settings.MARKET_DATA_RATE_BURST == 8
    assert settings.BRAPI_RATE_BURST == 8


def test_legacy_provider_variables_remain_supported():
    settings = make_settings(
        BRAPI_TOKEN="legacy-token",
        ALPHA_VANTAGE_API_KEY="legacy-intl-key",
        BRAPI_BASE_URL="https://legacy.example/api",
        BRAPI_RATE_LIMIT=4.0,
        BRAPI_RATE_BURST=9,
    )

    assert settings.QUOTES_PROVIDER_TOKEN == "legacy-token"
    assert settings.BRAPI_TOKEN == "legacy-token"
    assert settings.INTL_DATA_KEY == "legacy-intl-key"
    assert settings.ALPHA_VANTAGE_API_KEY == "legacy-intl-key"
    assert settings.MARKET_DATA_BASE_URL == "https://legacy.example/api"
    assert settings.BRAPI_BASE_URL == "https://legacy.example/api"
    assert settings.MARKET_DATA_RATE_LIMIT == 4.0
    assert settings.BRAPI_RATE_LIMIT == 4.0
    assert settings.MARKET_DATA_RATE_BURST == 9
    assert settings.BRAPI_RATE_BURST == 9


def test_generic_variables_take_precedence_over_legacy_values():
    settings = make_settings(
        QUOTES_PROVIDER_TOKEN="new-token",
        BRAPI_TOKEN="legacy-token",
        INTL_DATA_KEY="new-intl-key",
        ALPHA_VANTAGE_API_KEY="legacy-intl-key",
        MARKET_DATA_BASE_URL="https://new.example/api",
        BRAPI_BASE_URL="https://legacy.example/api",
        MARKET_DATA_RATE_LIMIT=1.5,
        BRAPI_RATE_LIMIT=7.0,
        MARKET_DATA_RATE_BURST=4,
        BRAPI_RATE_BURST=12,
    )

    assert settings.QUOTES_PROVIDER_TOKEN == "new-token"
    assert settings.BRAPI_TOKEN == "new-token"
    assert settings.INTL_DATA_KEY == "new-intl-key"
    assert settings.ALPHA_VANTAGE_API_KEY == "new-intl-key"
    assert settings.MARKET_DATA_BASE_URL == "https://new.example/api"
    assert settings.BRAPI_BASE_URL == "https://new.example/api"
    assert settings.MARKET_DATA_RATE_LIMIT == 1.5
    assert settings.BRAPI_RATE_LIMIT == 1.5
    assert settings.MARKET_DATA_RATE_BURST == 4
    assert settings.BRAPI_RATE_BURST == 4


def test_provider_defaults_are_resolved_for_internal_consumers():
    settings = make_settings()

    assert settings.MARKET_DATA_BASE_URL == "https://brapi.dev/api"
    assert settings.BRAPI_BASE_URL == "https://brapi.dev/api"
    assert settings.MARKET_DATA_RATE_LIMIT == 2.0
    assert settings.BRAPI_RATE_LIMIT == 2.0
    assert settings.MARKET_DATA_RATE_BURST == 5
    assert settings.BRAPI_RATE_BURST == 5
