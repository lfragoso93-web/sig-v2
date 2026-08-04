"""Testes da apuração anual integrada read-only de IRPF."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.irpf_annual_integrated_assessment_service import (
    assess_annual_integrated_operations,
)
from app.services.irpf_day_trade_matcher import DayTradeMatch
from app.services.irpf_day_trade_monthly_projection import DayTradeMonthlyProjection
from app.services.position_timeline_projection import CanonicalRealizedDisposal


@pytest.mark.asyncio
async def test_integrated_assessment_orchestrates_day_trade_and_swing_once() -> None:
    session = AsyncMock()
    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]
    session.execute.return_value = query_result
    operations = (SimpleNamespace(),)
    match = DayTradeMatch(
        ticker="BOVA11",
        trade_date=date(2024, 5, 2),
        buy_transaction_id=1,
        sell_transaction_id=2,
        quantity=Decimal(5),
        buy_unit_price_brl=Decimal(10),
        sell_unit_price_brl=Decimal(12),
        allocated_buy_fees_brl=Decimal(0),
        allocated_sell_fees_brl=Decimal(0),
    )
    day_trade = (
        DayTradeMonthlyProjection(
            competence_month="2024-05",
            matched_quantity=Decimal(5),
            day_trade_result_brl=Decimal(10),
            unmatched_buy_quantity=Decimal(15),
            unmatched_sell_quantity=Decimal(0),
            matches=(match,),
        ),
    )
    disposal = CanonicalRealizedDisposal(
        transaction_id=2,
        ticker="BOVA11",
        asset_type="ETF",
        disposal_date=date(2024, 5, 2),
        quantity_requested=Decimal(10),
        quantity_disposed=Decimal(10),
        unit_proceeds_brl=Decimal(12),
        gross_proceeds_brl=Decimal(120),
        cost_basis_brl=Decimal(100),
        fees_brl=Decimal(0),
        realized_pnl_brl=Decimal(20),
        currency="BRL",
        gross_proceeds_original_currency=Decimal(120),
        applied_event_ids=(),
    )

    with (
        patch(
            "app.services.irpf_annual_integrated_assessment_service.adapt_ordered_transactions",
            return_value=operations,
        ) as adapt,
        patch(
            "app.services.irpf_annual_integrated_assessment_service.project_day_trades_by_month",
            return_value=day_trade,
        ) as project_day_trade,
        patch(
            "app.services.irpf_annual_integrated_assessment_service.load_realized_disposals",
            new=AsyncMock(return_value=(disposal,)),
        ) as load_disposals,
    ):
        result = await assess_annual_integrated_operations(session, 7, 2024)

    adapt.assert_called_once()
    project_day_trade.assert_called_once_with(operations)
    load_disposals.assert_awaited_once()
    assert result.total_day_trade_result_brl == Decimal("10.00")
    assert result.total_day_trade_taxable_base_brl == Decimal("10.00")
    assert result.total_day_trade_tax_due_brl == Decimal("2.00")
    assert result.total_day_trade_net_tax_due_brl == Decimal("1.90")
    assert result.closing_day_trade_loss_carryforward_brl == Decimal("0.00")
    assert result.closing_day_trade_withholding_balance_brl == Decimal("0.00")
    assert result.total_swing_realized_pnl_brl == Decimal(10)
    assert result.total_swing_taxable_base_brl == Decimal(10)
    assert result.total_swing_tax_due_brl == Decimal("1.50")
    assert result.total_swing_net_tax_due_brl == Decimal("1.49")
    assert result.closing_common_withholding_balance_brl == Decimal("0.00")
    assert result.total_tax_due_brl == Decimal("3.50")
    assert result.total_net_tax_due_brl == Decimal("3.39")
    assert result.day_trade_monthly[0].tax_rate == Decimal("0.20")
    assert result.swing.monthly[0].realized_pnl_brl == Decimal("10.00")
    assert result.common_withholding_monthly[0].current_withholding_brl == Decimal(
        "0.01"
    )
    assert result.day_trade_withholding_monthly[0].current_withholding_brl == Decimal(
        "0.10"
    )


@pytest.mark.asyncio
async def test_integrated_assessment_rejects_invalid_year() -> None:
    with pytest.raises(ValueError, match="ano fiscal inválido"):
        await assess_annual_integrated_operations(AsyncMock(), 7, 1899)
