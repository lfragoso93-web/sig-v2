"""Testes do serviço anual de comparação Day Trade."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.services.irpf_day_trade_comparison_service import (
    build_legacy_day_trade_months,
    compare_annual_day_trade_with_legacy,
)
from app.services.irpf_day_trade_legacy_comparison import DayTradeDivergenceKind
from app.services.irpf_day_trade_monthly_projection import DayTradeMonthlyProjection


def _legacy_month(*, month: str, profit: float, sales: list[SimpleNamespace]):
    return SimpleNamespace(mes=month, lucro_day_trade=profit, vendas=sales)


def test_build_legacy_day_trade_months_sums_only_intraday_sales() -> None:
    months = build_legacy_day_trade_months(
        [
            _legacy_month(
                month="2024-05",
                profit=10.0,
                sales=[
                    SimpleNamespace(quantidade=5.0, is_day_trade=True),
                    SimpleNamespace(quantidade=15.0, is_day_trade=False),
                ],
            )
        ]
    )

    assert months[0].matched_quantity == Decimal(5)
    assert months[0].day_trade_result_brl == Decimal("10.0")


def test_build_legacy_day_trade_months_skips_empty_month() -> None:
    assert build_legacy_day_trade_months(
        [_legacy_month(month="2024-05", profit=0.0, sales=[])]
    ) == ()


@pytest.mark.asyncio
async def test_compare_annual_day_trade_with_legacy_orchestrates_both_paths() -> None:
    canonical = (
        DayTradeMonthlyProjection(
            competence_month="2024-05",
            matched_quantity=Decimal(5),
            day_trade_result_brl=Decimal(10),
            unmatched_buy_quantity=Decimal(15),
            unmatched_sell_quantity=Decimal(0),
            matches=(),
        ),
    )
    legacy = [
        _legacy_month(
            month="2024-05",
            profit=10.0,
            sales=[SimpleNamespace(quantidade=5.0, is_day_trade=True)],
        )
    ]

    with (
        patch(
            "app.services.irpf_day_trade_comparison_service.load_day_trade_projection",
            new=AsyncMock(return_value=canonical),
        ),
        patch(
            "app.services.irpf_day_trade_comparison_service.calc_ganhos_capital",
            new=AsyncMock(return_value=legacy),
        ),
    ):
        result = await compare_annual_day_trade_with_legacy(
            AsyncMock(),
            portfolio_id=7,
            year=2024,
        )

    assert result.portfolio_id == 7
    assert result.year == 2024
    assert not result.has_divergences
    assert result.monthly[0].kinds == (DayTradeDivergenceKind.MATCH,)
