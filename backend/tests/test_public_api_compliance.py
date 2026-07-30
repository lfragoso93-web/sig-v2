import json

from app.main import (
    _PUBLIC_MARKET_DATA_SOURCE,
    _sanitize_provider_text,
    _sanitize_public_payload,
    app,
)


FORBIDDEN_TERMS = (
    "brapi",
    "yfinance",
    "yahoo finance",
    "alpha vantage",
    "tesouro transparente",
)


def _assert_no_provider_terms(value: object) -> None:
    serialized = json.dumps(value, ensure_ascii=False).lower()
    leaked = [term for term in FORBIDDEN_TERMS if term in serialized]
    assert not leaked, f"Metadados públicos expõem provedores: {leaked}"


def test_provider_text_is_genericized() -> None:
    value = "Falha no BRAPI; fallback yfinance indisponível"

    sanitized = _sanitize_provider_text(value)

    assert _PUBLIC_MARKET_DATA_SOURCE in sanitized
    _assert_no_provider_terms(sanitized)


def test_public_payload_sanitizes_provider_text_recursively() -> None:
    payload = {
        "ticker": "TEST3",
        "detail": "Resposta recebida do Alpha Vantage",
        "nested": {
            "message": "Fallback yfinance indisponível",
        },
    }

    sanitized = _sanitize_public_payload(payload)

    assert isinstance(sanitized, dict)
    _assert_no_provider_terms(sanitized)


def test_openapi_schema_does_not_expose_provider_names() -> None:
    app.openapi_schema = None
    schema = app.openapi()

    assert isinstance(schema, dict)
    _assert_no_provider_terms(schema)


def test_legacy_portfolio_dividends_sync_route_is_not_exposed() -> None:
    paths = {
        route.path
        for route in app.routes
        if hasattr(route, "path")
    }

    assert "/api/v1/sync/proventos/{portfolio_id}" not in paths
