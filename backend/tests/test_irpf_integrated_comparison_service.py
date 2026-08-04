"""Testes do orquestrador de comparação integrada do IRPF."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.services.irpf_integrated_comparison_service import (
    compare_annual_integrated_with_legacy,
)


@pytest.mark.asyncio
async def test_integrated_comparison_orchestrates_both_paths_once() -> None:
    session = AsyncMock()
    canonical = SimpleNamespace(swing=SimpleNamespace(monthly=()), day_trade_monthly=())
    legacy = []

    with (
        patch(
            "app.services.irpf_integrated_comparison_service.assess_annual_integrated_operations",
            new=AsyncMock(return_value=canonical),
        ) as assess,
        patch(
            "app.services.irpf_integrated_comparison_service.calc_ganhos_capital",
            new=AsyncMock(return_value=legacy),
        ) as calculate_legacy,
    ):
        result = await compare_annual_integrated_with_legacy(session, 7, 2024)

    assess.assert_awaited_once_with(session, 7, 2024)
    calculate_legacy.assert_awaited_once_with(session, 7, 2024)
    assert result.portfolio_id == 7
    assert result.year == 2024
    assert result.monthly == ()
    assert result.has_divergences is False
