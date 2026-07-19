"""Matriz de normalização dos tipos canônicos de Proventos."""

import pytest

from app.models.dividend import DividendType
from app.services.dividend_type_service import normalize_dividend_type


@pytest.mark.parametrize(
    "label,category,expected",
    [
        pytest.param("Dividendos", "cash", DividendType.DIVIDENDO, id="dividendo"),
        pytest.param(
            "Juros Sobre Capital Próprio",
            "cash",
            DividendType.JCP,
            id="jcp",
        ),
        pytest.param("Rendimentos", "cash", DividendType.RENDIMENTO, id="rendimento"),
        pytest.param("Amortização", "cash", DividendType.AMORTIZACAO, id="amortizacao"),
        pytest.param("Bonificação", "stock", DividendType.BONIFICACAO, id="bonificacao"),
        pytest.param("Subscrição", "subscription", DividendType.SUBSCRICAO, id="subscricao"),
    ],
)
def test_normalizes_provider_labels_to_canonical_types(
    label: str,
    category: str,
    expected: DividendType,
):
    assert normalize_dividend_type(label, category) == expected
