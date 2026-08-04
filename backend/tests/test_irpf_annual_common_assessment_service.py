"""Testes do serviço anual read-only de operações comuns."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.irpf_annual_common_assessment_service import (
    assess_annual_common_operations,
    build_annual_common_assessment,
)
from app.services.irpf_common_loss_carryforward import (
    FiscalMonthlyLossCompensation,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup
from app.services.position_timeline_projection import CanonicalRealizedDisposal


def _compensation(
    *,
    month: str,
    group: TaxAssessmentGroup,
    realized: str,
    taxable: str,
    tax: str,
    closing_loss: str = "0",
) -> FiscalMonthlyLossCompensation:
    return FiscalMonthlyLossCompensation(
        competence_month=month,
        group=group,
        realized_pnl_brl=Decimal(realized),
        exemption_applied=False,
        opening_loss_carryforward_brl=Decimal("0"),
        loss_used_brl=Decimal("0"),
        closing_loss_carryforward_brl=Decimal(closing_loss),
        taxable_base_brl=Decimal(taxable),
        tax_rate=Decimal("0.15"),
        tax_due_brl=Decimal(tax),
    )


def _disposal(
    *,
    transaction_id: int,
    ticker: str,
    asset_type: str,
    disposal_date: date,
    gross: str,
    cost: str,
) -> CanonicalRealizedDisposal:
    gross_value = Decimal(gross)
    cost_value = Decimal(cost)
    return CanonicalRealizedDisposal(
        transaction_id=transaction_id,
        ticker=ticker,
        asset_type=asset_type,
        disposal_date=disposal_date,
        quantity_requested=Decimal("10"),
        quantity_disposed=Decimal("10"),
        unit_proceeds_brl=gross_value / Decimal("10"),
        gross_proceeds_brl=gross_value,
        cost_basis_brl=cost_value,
        fees_brl=Decimal("0"),
        realized_pnl_brl=gross_value - cost_value,
        currency="BRL",
        gross_proceeds_original_currency=None,
        applied_event_ids=(),
    )


def test_build_annual_assessment_consolidates_totals_and_closing_losses() -> None:
    result = build_annual_common_assessment(
        portfolio_id=7,
        year=2024,
        monthly=[
            _compensation(
                month="2024-02",
                group=TaxAssessmentGroup.BDR,
                realized="500",
                taxable="500",
                tax="75",
            ),
            _compensation(
                month="2024-01",
                group=TaxAssessmentGroup.STOCKS,
                realized="-1000",
                taxable="0",
                tax="0",
                closing_loss="1000",
            ),
            _compensation(
                month="2024-03",
                group=TaxAssessmentGroup.STOCKS,
                realized="400",
                taxable="0",
                tax="0",
                closing_loss="600",
            ),
        ],
    )

    assert result.portfolio_id == 7
    assert result.start_date == date(2024, 1, 1)
    assert result.end_date == date(2024, 12, 31)
    assert [item.competence_month for item in result.monthly] == [
        "2024-01",
        "2024-02",
        "2024-03",
    ]
    assert result.total_realized_pnl_brl == Decimal("-100")
    assert result.total_taxable_base_brl == Decimal("500")
    assert result.total_tax_due_brl == Decimal("75")
    assert result.closing_loss_carryforward_by_group == {
        TaxAssessmentGroup.BDR: Decimal("0"),
        TaxAssessmentGroup.STOCKS: Decimal("600"),
    }


def test_build_annual_assessment_rejects_month_outside_year() -> None:
    with pytest.raises(ValueError, match="fora do ano fiscal"):
        build_annual_common_assessment(
            portfolio_id=1,
            year=2024,
            monthly=[
                _compensation(
                    month="2023-12",
                    group=TaxAssessmentGroup.ETF,
                    realized="100",
                    taxable="100",
                    tax="15",
                )
            ],
        )


@pytest.mark.asyncio
async def test_annual_service_uses_canonical_reader_and_full_pipeline(monkeypatch) -> None:
    calls = {}

    async def fake_load(db, portfolio_id, *, start_date, end_date):
        calls.update(
            db=db,
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
        )
        return (
            _disposal(
                transaction_id=1,
                ticker="VALE3",
                asset_type="ACAO",
                disposal_date=date(2024, 1, 10),
                gross="25000",
                cost="26000",
            ),
            _disposal(
                transaction_id=2,
                ticker="VALE3",
                asset_type="ACAO",
                disposal_date=date(2024, 2, 10),
                gross="26000",
                cost="24000",
            ),
            _disposal(
                transaction_id=3,
                ticker="AAPL34",
                asset_type="BDR",
                disposal_date=date(2024, 2, 12),
                gross="5000",
                cost="4000",
            ),
        )

    monkeypatch.setattr(
        "app.services.irpf_annual_common_assessment_service.load_realized_disposals",
        fake_load,
    )
    db = SimpleNamespace()

    result = await assess_annual_common_operations(db, portfolio_id=9, year=2024)

    assert calls == {
        "db": db,
        "portfolio_id": 9,
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
    }
    assert result.total_realized_pnl_brl == Decimal("2000.00")
    assert result.total_taxable_base_brl == Decimal("2000.00")
    assert result.total_tax_due_brl == Decimal("300.00")
    assert result.closing_loss_carryforward_by_group == {
        TaxAssessmentGroup.BDR: Decimal("0.00"),
        TaxAssessmentGroup.STOCKS: Decimal("0.00"),
    }


@pytest.mark.asyncio
async def test_annual_service_returns_empty_assessment_for_empty_portfolio(
    monkeypatch,
) -> None:
    async def fake_load(*args, **kwargs):
        return ()

    monkeypatch.setattr(
        "app.services.irpf_annual_common_assessment_service.load_realized_disposals",
        fake_load,
    )

    result = await assess_annual_common_operations(
        SimpleNamespace(),
        portfolio_id=3,
        year=2024,
    )

    assert result.monthly == ()
    assert result.total_realized_pnl_brl == Decimal("0")
    assert result.total_taxable_base_brl == Decimal("0")
    assert result.total_tax_due_brl == Decimal("0")
    assert result.closing_loss_carryforward_by_group == {}
