"""Testes da CLI read-only de comparação Day Trade."""

from argparse import Namespace
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.cli.irpf_compare_day_trade import _main, comparison_to_dict
from app.services.irpf_day_trade_comparison_service import DayTradeAnnualComparison
from app.services.irpf_day_trade_legacy_comparison import (
    DayTradeDivergenceKind,
    DayTradeMonthComparison,
)


def _comparison(*, divergent: bool) -> DayTradeAnnualComparison:
    kinds = (
        (DayTradeDivergenceKind.RESULT,)
        if divergent
        else (DayTradeDivergenceKind.MATCH,)
    )
    return DayTradeAnnualComparison(
        portfolio_id=7,
        year=2024,
        monthly=(
            DayTradeMonthComparison(
                competence_month="2024-05",
                canonical_matched_quantity=Decimal(5),
                legacy_matched_quantity=Decimal(5),
                canonical_result_brl=Decimal(10),
                legacy_result_brl=Decimal(9 if divergent else 10),
                quantity_delta=Decimal(0),
                result_delta_brl=Decimal(1 if divergent else 0),
                kinds=kinds,
            ),
        ),
    )


def test_comparison_to_dict_emits_versioned_contract() -> None:
    report = comparison_to_dict(_comparison(divergent=True))

    assert report["schema_version"] == (
        "irpf-day-trade-canonical-legacy-comparison.v1"
    )
    assert report["has_divergences"] is True
    assert report["summary"] == {
        "months_compared": 1,
        "matching_months": 0,
        "divergent_months": 1,
    }
    assert report["monthly"][0]["kinds"] == ["day_trade_result"]


@pytest.mark.asyncio
async def test_main_returns_two_when_requested_and_divergent() -> None:
    session = AsyncMock()
    session.rollback = AsyncMock()
    context = AsyncMock()
    context.__aenter__.return_value = session
    context.__aexit__.return_value = None

    with (
        patch("app.cli.irpf_compare_day_trade.AsyncSessionLocal", return_value=context),
        patch(
            "app.cli.irpf_compare_day_trade.compare_annual_day_trade_with_legacy",
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
