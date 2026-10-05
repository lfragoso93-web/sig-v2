from decimal import Decimal

from app.certification.portfolio_financial_reconciliation import (
    calculate_independent_class_distribution,
)


def test_independent_class_distribution_matches_cert303_fixture():
    assert calculate_independent_class_distribution() == {
        "ACAO": Decimal("2160.00"),
        "FII": Decimal("2100.00"),
        "ETF_NACIONAL": Decimal("560.00"),
        "BDR": Decimal("1140.00"),
        "CRIPTO": Decimal("21000.00"),
        "TESOURO_DIRETO": Decimal("6950.00"),
        "RENDA_FIXA": Decimal("5050.00"),
    }
