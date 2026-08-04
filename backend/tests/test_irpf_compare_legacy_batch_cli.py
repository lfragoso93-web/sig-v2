"""Testes da CLI read-only de comparação fiscal em lote."""

import argparse
from datetime import date
from types import SimpleNamespace

import pytest
from app.cli.irpf_compare_legacy_batch import _main, batch_report_to_dict
from app.services.irpf_comparison_batch_service import (
    FiscalComparisonBatchReport,
    FiscalComparisonTarget,
)
from app.services.irpf_legacy_comparison_service import (
    FiscalAnnualComparison,
    FiscalComparisonKind,
    FiscalMonthlyComparison,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup


def _report(*, divergent: bool) -> FiscalComparisonBatchReport:
    target = FiscalComparisonTarget(
        portfolio_id=7,
        year=2024,
        sale_count=2,
        first_sale_date=date(2024, 1, 10),
        last_sale_date=date(2024, 8, 20),
    )
    kinds = (
        (FiscalComparisonKind.CLASS_SEGREGATION,)
        if divergent
        else (FiscalComparisonKind.MATCH,)
    )
    comparison = FiscalAnnualComparison(
        portfolio_id=7,
        year=2024,
        monthly=(
            FiscalMonthlyComparison(
                competence_month="2024-01",
                canonical_realized_pnl_brl=0,
                legacy_realized_pnl_brl=0,
                canonical_taxable_base_brl=0,
                legacy_taxable_base_brl=0,
                canonical_tax_due_brl=0,
                legacy_tax_due_brl=0,
                kinds=kinds,
                canonical_groups=(TaxAssessmentGroup.STOCKS,),
            ),
        ),
    )
    return FiscalComparisonBatchReport(
        targets=(target,),
        comparisons=(comparison,),
        months_compared=1,
        matching_months=0 if divergent else 1,
        divergent_months=1 if divergent else 0,
        divergence_counts=(
            {FiscalComparisonKind.CLASS_SEGREGATION: 1} if divergent else {}
        ),
    )


def test_batch_report_to_dict_exposes_versioned_contract() -> None:
    payload = batch_report_to_dict(_report(divergent=True))

    assert payload["schema_version"] == "irpf-canonical-legacy-batch-comparison.v1"
    assert payload["summary"] == {
        "targets_discovered": 1,
        "comparisons_executed": 1,
        "months_compared": 1,
        "matching_months": 0,
        "divergent_months": 1,
    }
    assert payload["divergence_counts"] == {"class_segregation": 1}
    assert payload["targets"][0]["sale_count"] == 2
    assert payload["comparisons"][0]["monthly"][0]["kinds"] == [
        "class_segregation"
    ]


@pytest.mark.asyncio
async def test_main_executes_batch_and_rolls_back(monkeypatch, capsys) -> None:
    report = _report(divergent=False)
    session = SimpleNamespace(rollback_calls=0)

    async def rollback() -> None:
        session.rollback_calls += 1

    session.rollback = rollback

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_compare(db, *, start_year, end_year):
        assert db is session
        assert start_year == 2023
        assert end_year == 2024
        return report

    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy_batch.AsyncSessionLocal",
        lambda: SessionContext(),
    )
    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy_batch.compare_discovered_targets",
        fake_compare,
    )

    exit_code = await _main(
        argparse.Namespace(
            start_year=2023,
            end_year=2024,
            fail_on_divergence=False,
        )
    )

    assert exit_code == 0
    assert session.rollback_calls == 1
    assert "irpf-canonical-legacy-batch-comparison.v1" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_main_returns_two_when_requested_and_divergent(monkeypatch) -> None:
    report = _report(divergent=True)
    session = SimpleNamespace()

    async def rollback() -> None:
        return None

    session.rollback = rollback

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_compare(*args, **kwargs):
        return report

    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy_batch.AsyncSessionLocal",
        lambda: SessionContext(),
    )
    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy_batch.compare_discovered_targets",
        fake_compare,
    )

    assert (
        await _main(
            argparse.Namespace(
                start_year=None,
                end_year=None,
                fail_on_divergence=True,
            )
        )
        == 2
    )
