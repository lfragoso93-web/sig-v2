"""Testes da CLI read-only de comparação fiscal."""

import argparse
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.cli.irpf_compare_legacy import _main, comparison_to_dict
from app.services.irpf_legacy_comparison_service import (
    FiscalAnnualComparison,
    FiscalComparisonKind,
    FiscalMonthlyComparison,
)
from app.services.irpf_tax_policy import TaxAssessmentGroup


def _comparison(*, divergent: bool) -> FiscalAnnualComparison:
    kinds = (
        (FiscalComparisonKind.CLASS_SEGREGATION,)
        if divergent
        else (FiscalComparisonKind.MATCH,)
    )
    return FiscalAnnualComparison(
        portfolio_id=7,
        year=2024,
        monthly=(
            FiscalMonthlyComparison(
                competence_month="2024-01",
                canonical_realized_pnl_brl=Decimal(100),
                legacy_realized_pnl_brl=Decimal(100),
                canonical_taxable_base_brl=Decimal(100),
                legacy_taxable_base_brl=Decimal(100),
                canonical_tax_due_brl=Decimal(15),
                legacy_tax_due_brl=Decimal(15),
                kinds=kinds,
                canonical_groups=(TaxAssessmentGroup.STOCKS,),
            ),
        ),
    )


def test_comparison_to_dict_exposes_stable_audit_contract() -> None:
    report = comparison_to_dict(_comparison(divergent=True))

    assert report["schema_version"] == "irpf-canonical-legacy-comparison.v1"
    assert report["portfolio_id"] == 7
    assert report["year"] == 2024
    assert report["has_divergences"] is True
    assert report["summary"] == {
        "months_compared": 1,
        "matching_months": 0,
        "divergent_months": 1,
    }
    assert report["monthly"][0]["kinds"] == ["class_segregation"]
    assert report["monthly"][0]["canonical_groups"] == ["stocks"]


@pytest.mark.asyncio
async def test_main_executes_comparison_and_rolls_back(monkeypatch, capsys) -> None:
    comparison = _comparison(divergent=False)
    session = SimpleNamespace(rollback_calls=0)

    async def rollback() -> None:
        session.rollback_calls += 1

    session.rollback = rollback

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def fake_compare(db, portfolio_id, year):
        assert db is session
        assert portfolio_id == 7
        assert year == 2024
        return comparison

    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy.AsyncSessionLocal",
        lambda: SessionContext(),
    )
    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy.compare_annual_common_with_legacy",
        fake_compare,
    )

    exit_code = await _main(
        argparse.Namespace(
            portfolio_id=7,
            year=2024,
            fail_on_divergence=False,
        )
    )

    assert exit_code == 0
    assert session.rollback_calls == 1
    assert '"schema_version": "irpf-canonical-legacy-comparison.v1"' in capsys.readouterr().out


@pytest.mark.asyncio
async def test_main_returns_two_only_when_requested_for_divergence(monkeypatch) -> None:
    comparison = _comparison(divergent=True)
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
        return comparison

    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy.AsyncSessionLocal",
        lambda: SessionContext(),
    )
    monkeypatch.setattr(
        "app.cli.irpf_compare_legacy.compare_annual_common_with_legacy",
        fake_compare,
    )

    assert (
        await _main(
            argparse.Namespace(
                portfolio_id=7,
                year=2024,
                fail_on_divergence=True,
            )
        )
        == 2
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("portfolio_id", "year", "message"),
    [
        (0, 2024, "portfolio-id deve ser positivo"),
        (1, 1899, "ano fiscal inválido"),
    ],
)
async def test_main_rejects_invalid_arguments(portfolio_id, year, message) -> None:
    with pytest.raises(ValueError, match=message):
        await _main(
            argparse.Namespace(
                portfolio_id=portfolio_id,
                year=year,
                fail_on_divergence=False,
            )
        )
