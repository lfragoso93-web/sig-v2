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


def test_source_field_is_genericized_recursively() -> None:
    payload = {
        "ticker": "TEST3",
        "source": "brapi",
        "nested": {
            "source": "yfinance",
            "detail": "Resposta recebida do Alpha Vantage",
        },
    }

    sanitized = _sanitize_public_payload(payload)

    assert sanitized["source"] == _PUBLIC_MARKET_DATA_SOURCE
    assert sanitized["nested"]["source"] == _PUBLIC_MARKET_DATA_SOURCE
    _assert_no_provider_terms(sanitized)


def test_openapi_schema_does_not_expose_provider_names() -> None:
    app.openapi_schema = None
    schema = app.openapi()

    _assert_no_provider_terms(schema)
