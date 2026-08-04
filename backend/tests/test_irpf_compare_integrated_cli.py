"""Testes da CLI read-only de comparação integrada do IRPF."""

from argparse import Namespace
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from app.cli.irpf_compare_integrated import _main, comparison_to_dict
from app.services.irpf_integrated_legacy_comparison import (
    IntegratedFiscalAnnualComparison,
    IntegratedFiscalComparisonKind,
    IntegratedFiscalMonthlyComparison,
)


def _comparison(*, divergent: bool) -> IntegratedFiscalAnnualComparison:
    kinds = (
        (IntegratedFiscalComparisonKind.DAY_TRADE_TAX_DUE,)
        if divergent
        else (IntegratedFiscalComparisonKind.MATCH,)
    )
    return IntegratedFiscalAnnualComparison(
        portfolio_id=7,
        year=2024,
        monthly=(
            IntegratedFiscalMonthlyComparison(
                competence_month="2024-05",
                canonical_swing_result_brl=Decimal(10),
                legacy_swing_result_brl=Decimal(10),
                canonical_swing_taxable_base_brl=Decimal(10),
                legacy_swing_taxable_base_brl=Decimal(10),
                canonical_swing_tax_due_brl=Decimal("1.50"),
                legacy_swing_tax_due_brl=Decimal("1.50"),
                canonical_day_trade_result_brl=Decimal(20),
                legacy_day_trade_result_brl=Decimal(20),
                canonical_day_trade_taxable_base_brl=Decimal(20),
                legacy_day_trade_taxable_base_brl=Decimal(20),
                canonical_day_trade_tax_due_brl=Decimal(4),
                legacy_day_trade_tax_due_brl=Decimal(3 if divergent else 4),
                kinds=kinds,
            ),
        ),
    )


def test_comparison_to_dict_emits_versioned_contract() -> None:
    report = comparison_to_dict(_comparison(divergent=True))

    assert report["schema_version"] == (
        "irpf-integrated-canonical-legacy-comparison.v1"
    )
    assert report["has_divergences"] is True
    assert report["summary"] == {
        "months_compared": 1,
        "matching_months": 0,
        "divergent_months": 1,
        "classification_counts": {"day_trade_tax_due": 1},
    }
    assert report["monthly"][0]["kinds"] == ["day_trade_tax_due"]


@pytest.mark.asyncio
async def test_main_returns_two_when_requested_and_divergent() -> None:
    session = AsyncMock()
    session.rollback = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = session
    context.__aexit__.return_value = None

    with (
        patch("app.cli.irpf_compare_integrated.AsyncSessionLocal", return_value=context),
        patch(
            "app.cli.irpf_compare_integrated.compare_annual_integrated_with_legacy",
            new=AsyncMock(return_value=_comparison(divergent=True)),
        ),
        patch("builtins.print"),
    ):
        exit_code = await _main(
            Namespace(portfolio_id=7, year=2024, fail_on_divergence=True)
        )

    assert exit_code == 2
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_validates_arguments() -> None:
    with pytest.raises(ValueError, match="portfolio-id deve ser positivo"):
        await _main(Namespace(portfolio_id=0, year=2024, fail_on_divergence=False))

    with pytest.raises(ValueError, match="ano fiscal inválido"):
        await _main(Namespace(portfolio_id=7, year=1899, fail_on_divergence=False))
