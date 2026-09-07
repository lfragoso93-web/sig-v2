from decimal import Decimal

import pytest

from app.services.irpf_tax_policy import TaxAssessmentGroup, resolve_tax_policy


def test_canonical_national_etf_uses_existing_etf_tax_policy() -> None:
    policy = resolve_tax_policy("ETF_NACIONAL")

    assert policy.canonical_class == "ETF"
    assert policy.common_group == TaxAssessmentGroup.ETF
    assert policy.day_trade_group == TaxAssessmentGroup.ETF
    assert policy.common_rate == Decimal("0.15")
    assert policy.day_trade_rate == Decimal("0.20")
    assert policy.monthly_exemption_limit is None
    assert policy == resolve_tax_policy("ETF")


def test_unknown_tax_class_remains_fail_closed() -> None:
    with pytest.raises(ValueError, match="classe fiscal não suportada"):
        resolve_tax_policy("ETF_DESCONHECIDO")
