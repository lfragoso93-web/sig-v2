import pytest

from app.services.dividend_ticker_policy import is_event_ticker


@pytest.mark.parametrize(
    "ticker",
    ["ABEV3", "PETR4", "MXRF11", "AAPL34", "TAEE11"],
)
def test_accepts_main_event_tickers(ticker: str) -> None:
    assert is_event_ticker(ticker)


@pytest.mark.parametrize(
    "ticker",
    ["ONCO11F", "PETR4F", "ABEV3R", "ABEV3D", "ABEV97"],
)
def test_rejects_fractions_rights_and_receipts(ticker: str) -> None:
    assert not is_event_ticker(ticker)
