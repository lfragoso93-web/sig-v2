"""Regras canônicas de normalização dos eventos globais de Proventos."""

from datetime import date

from app.services.dividend_event_normalizer import parse_dividend_event


def test_parse_cash_dividend_brapi_with_record_date() -> None:
    result = parse_dividend_event(
        {
            "lastDatePrior": "2024-03-01",
            "paymentDate": "2024-03-15",
            "rate": 1.25,
            "label": "Dividendos",
            "eventCategory": "cash",
        }
    )

    assert result is not None
    assert result.record_date == date(2024, 3, 1)
    assert result.ex_date == date(2024, 3, 4)
    assert result.payment_date == date(2024, 3, 15)
    assert result.value_per_unit == 1.25
    assert result.dividend_type == "DIVIDENDO"


def test_parse_cash_dividend_brapi_with_explicit_ex_date() -> None:
    result = parse_dividend_event(
        {
            "lastDatePrior": "2024-03-01",
            "exDate": "2024-03-04",
            "paymentDate": "2024-03-15",
            "rate": 1.25,
            "label": "Dividendos",
            "eventCategory": "cash",
        }
    )

    assert result is not None
    assert result.record_date == date(2024, 3, 1)
    assert result.ex_date == date(2024, 3, 4)


def test_parse_jcp_by_label() -> None:
    result = parse_dividend_event(
        {
            "lastDatePrior": "2024-05-01",
            "paymentDate": "2024-05-15",
            "rate": 2.0,
            "label": "Juros Sobre Capital Próprio",
            "eventCategory": "cash",
        }
    )

    assert result is not None
    assert result.dividend_type == "JCP"


def test_parse_stock_dividend_without_cash_value() -> None:
    result = parse_dividend_event(
        {
            "lastDatePrior": "2024-06-10",
            "approvedOn": "2024-06-01",
            "label": "Bonificação",
            "factor": 0.10,
            "completeFactor": 1.10,
            "eventCategory": "stock",
        }
    )

    assert result is not None
    assert result.dividend_type == "BONIFICACAO"
    assert result.value_per_unit == 0.0
    assert result.factor == 0.10
    assert result.complete_factor == 1.10
    assert result.approved_on == date(2024, 6, 1)


def test_parse_subscription() -> None:
    result = parse_dividend_event(
        {
            "lastDatePrior": "2024-07-01",
            "approvedOn": "2024-06-20",
            "label": "Subscrição",
            "eventCategory": "subscription",
        }
    )

    assert result is not None
    assert result.dividend_type == "SUBSCRICAO"


def test_parse_yfinance_format() -> None:
    result = parse_dividend_event(
        {"paymentDate": "2024-04-10", "rate": 0.75, "type": "DIVIDENDO"}
    )

    assert result is not None
    assert result.record_date is None
    assert result.ex_date == date(2024, 4, 10)
    assert result.payment_date == date(2024, 4, 10)


def test_rejects_event_without_date() -> None:
    assert parse_dividend_event({"rate": 1.0, "type": "DIVIDENDO"}) is None


def test_rejects_zero_cash_value() -> None:
    raw = {"paymentDate": "2024-01-01", "rate": 0.0, "type": "DIVIDENDO"}
    assert parse_dividend_event(raw) is None


def test_rejects_invalid_date() -> None:
    raw = {
        "paymentDate": "data-invalida",
        "rate": 1.0,
        "type": "DIVIDENDO",
    }
    assert parse_dividend_event(raw) is None
