import logging
from unittest.mock import patch

import pytest

from app.core.log_safety import sanitize_log_value
from app.integrations import yfinance_client


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("PETR4", "PETR4"),
        ("PETR4\r\nforged", "PETR4\\r\\nforged"),
        ("line\nnext", "line\\nnext"),
        ("line\rnext", "line\\rnext"),
        ("line\u2028next\u2029last", "line\\u2028next\\u2029last"),
    ],
)
def test_sanitize_log_value_keeps_external_values_on_one_line(
    value: str,
    expected: str,
) -> None:
    assert sanitize_log_value(value) == expected


def test_sanitize_log_value_limits_untrusted_payload_size() -> None:
    assert sanitize_log_value("x" * 600) == "x" * 500


@pytest.mark.parametrize(
    "operation",
    [
        yfinance_client.get_ticker_info,
        yfinance_client.get_current_price,
        yfinance_client.get_price_history,
        yfinance_client.get_dividends,
    ],
)
def test_yfinance_errors_escape_ticker_and_provider_lines(
    operation,
    caplog: pytest.LogCaptureFixture,
) -> None:
    malicious_ticker = "PETR4\r\nforged-entry"
    with (
        patch.object(yfinance_client, "_YF_MIN_INTERVAL", 0.0),
        patch.object(
            yfinance_client.yf,
            "Ticker",
            side_effect=RuntimeError("provider\r\nforged-error"),
        ),
        caplog.at_level(logging.ERROR, logger=yfinance_client.__name__),
    ):
        operation(malicious_ticker)

    message = caplog.records[-1].getMessage()
    assert "\r" not in message
    assert "\n" not in message
    assert "PETR4\\r\\nforged-entry" in message
    assert "provider\\r\\nforged-error" in message
