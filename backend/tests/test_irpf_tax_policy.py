"""Contrato do catálogo fiscal explícito por classe."""

from decimal import Decimal

import pytest

from app.services.irpf_tax_policy import TaxAssessmentGroup, resolve_tax_policy


def test_stocks_keep_the_monthly_exemption_contract():
    policy = resolve_tax_policy("ACAO")

    assert policy.common_group is TaxAssessmentGroup.STOCKS
    assert policy.common_rate == Decimal("0.15")
    assert policy.day_trade_rate == Decimal("0.20")
    assert policy.monthly_exemption_limit == Decimal("20000")
    assert policy.has_monthly_exemption is True


def test_bdr_is_taxable_without_the_stock_monthly_exemption():
    policy = resolve_tax_policy("BDR")

    assert policy.common_group is TaxAssessmentGroup.BDR
    assert policy.common_rate == Decimal("0.15")
    assert policy.day_trade_rate == Decimal("0.20")
    assert policy.monthly_exemption_limit is None
    assert policy.has_monthly_exemption is False


def test_etf_does_not_share_the_stock_assessment_group():
    stock_policy = resolve_tax_policy("ACAO")
    etf_policy = resolve_tax_policy("ETF")

    assert etf_policy.common_group is TaxAssessmentGroup.ETF
    assert etf_policy.common_group is not stock_policy.common_group
    assert etf_policy.monthly_exemption_limit is None


@pytest.mark.parametrize("asset_type", ["FII", "FIAGRO"])
def test_real_estate_fund_classes_use_their_own_twenty_percent_policy(
    asset_type: str,
):
    policy = resolve_tax_policy(asset_type)

    assert policy.common_group is TaxAssessmentGroup.REAL_ESTATE_FUNDS
    assert policy.common_rate == Decimal("0.20")
    assert policy.day_trade_rate == Decimal("0.20")
    assert policy.monthly_exemption_limit is None


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("AÇÃO", "ACAO"),
        ("acoes", "ACAO"),
        ("fundo imobiliário", "FII"),
    ],
)
def test_known_aliases_resolve_to_the_canonical_class(alias: str, canonical: str):
    assert resolve_tax_policy(alias).canonical_class == canonical


def test_unknown_class_is_rejected_instead_of_receiving_a_fallback_policy():
    with pytest.raises(ValueError, match="classe fiscal não suportada"):
        resolve_tax_policy("CRIPTO")
