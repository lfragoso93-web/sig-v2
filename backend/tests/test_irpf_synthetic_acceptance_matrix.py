"""Gate fiscal sintético e determinístico para a migração canônica do IRPF."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.irpf_common_loss_carryforward import compensate_common_losses
from app.services.irpf_day_trade_monthly_assessment import assess_day_trade_months
from app.services.irpf_day_trade_monthly_projection import DayTradeMonthlyProjection
from app.services.irpf_monthly_common_assessment import assess_common_monthly_groups
from app.services.irpf_realized_disposal_tax_adapter import (
    adapt_realized_disposals,
    group_common_entries_by_month,
)
from app.services.position_timeline_projection import CanonicalRealizedDisposal

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "irpf_synthetic_acceptance_v1.json"


def _load_corpus() -> dict[str, object]:
    corpus = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert corpus["schema_version"] == "irpf-synthetic-acceptance.v1"
    return corpus


def _disposal(
    *,
    transaction_id: int,
    asset_type: str,
    competence: str,
    gross_proceeds_brl: str,
    realized_pnl_brl: str,
) -> CanonicalRealizedDisposal:
    year, month = (int(part) for part in competence.split("-"))
    gross = Decimal(gross_proceeds_brl)
    pnl = Decimal(realized_pnl_brl)
    return CanonicalRealizedDisposal(
        transaction_id=transaction_id,
        ticker=f"SYNTH{transaction_id}",
        asset_type=asset_type,
        disposal_date=date(year, month, 15),
        quantity_requested=Decimal(1),
        quantity_disposed=Decimal(1),
        unit_proceeds_brl=gross,
        gross_proceeds_brl=gross,
        cost_basis_brl=gross - pnl,
        fees_brl=Decimal(0),
        realized_pnl_brl=pnl,
        currency="BRL",
        gross_proceeds_original_currency=gross,
        applied_event_ids=(),
    )


@pytest.mark.parametrize("scenario", _load_corpus()["common_scenarios"])
def test_common_synthetic_acceptance_scenarios(scenario: dict[str, object]) -> None:
    disposals = tuple(
        _disposal(
            transaction_id=index,
            asset_type=str(scenario["asset_type"]),
            competence=str(month["competence"]),
            gross_proceeds_brl=str(month["gross_proceeds_brl"]),
            realized_pnl_brl=str(month["realized_pnl_brl"]),
        )
        for index, month in enumerate(scenario["months"], start=1)
    )
    entries = adapt_realized_disposals(disposals)
    groups = group_common_entries_by_month(entries)
    assessments = assess_common_monthly_groups(groups)
    compensated = compensate_common_losses(assessments)

    assert len(compensated) == len(scenario["months"])
    for actual, expected in zip(compensated, scenario["months"], strict=True):
        assert actual.competence_month == expected["competence"]
        assert actual.exemption_applied is expected["expected_exemption"]
        assert actual.taxable_base_brl == Decimal(expected["expected_taxable_base_brl"])
        assert actual.tax_due_brl == Decimal(expected["expected_tax_due_brl"])
        assert actual.closing_loss_carryforward_brl == Decimal(
            expected["expected_closing_loss_brl"]
        )


@pytest.mark.parametrize("scenario", _load_corpus()["day_trade_scenarios"])
def test_day_trade_synthetic_acceptance_scenarios(
    scenario: dict[str, object],
) -> None:
    projections = tuple(
        DayTradeMonthlyProjection(
            competence_month=str(month["competence"]),
            matched_quantity=Decimal(1),
            day_trade_result_brl=Decimal(month["realized_pnl_brl"]),
            unmatched_buy_quantity=Decimal(0),
            unmatched_sell_quantity=Decimal(0),
            matches=(),
        )
        for month in scenario["months"]
    )
    assessments = assess_day_trade_months(projections)

    assert len(assessments) == len(scenario["months"])
    for actual, expected in zip(assessments, scenario["months"], strict=True):
        assert actual.competence_month == expected["competence"]
        assert actual.taxable_base_brl == Decimal(expected["expected_taxable_base_brl"])
        assert actual.tax_due_brl == Decimal(expected["expected_tax_due_brl"])
        assert actual.closing_loss_carryforward_brl == Decimal(
            expected["expected_closing_loss_brl"]
        )
