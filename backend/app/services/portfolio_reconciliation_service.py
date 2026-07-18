"""Reconciliação financeira dos consumidores do snapshot canônico.

O serviço compara valores com o snapshot apenas quando as bases temporais são
compatíveis. Valuations intradiários não são tratados como divergência do
fechamento.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from app.models.portfolio_snapshot import PortfolioSnapshot

MONEY_TOLERANCE = Decimal("0.01")
PERCENT_TOLERANCE = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class ReconciliationCheck:
    field: str
    expected: Decimal
    observed: Decimal
    tolerance: Decimal

    @property
    def difference(self) -> Decimal:
        return self.observed - self.expected

    @property
    def is_reconciled(self) -> bool:
        return abs(self.difference) <= self.tolerance

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "expected": float(self.expected),
            "observed": float(self.observed),
            "difference": float(self.difference),
            "tolerance": float(self.tolerance),
            "is_reconciled": self.is_reconciled,
        }


def _decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


def build_reconciliationbuild_reconciliation_check(
    field: str,
    expected: object,
    observed: object,
    tolerance: Decimal = MONEY_TOLERANCE,
) -> ReconciliationCheck:
    """Cria uma comparação determinística sem impor referência temporal."""
    return ReconciliationCheck(
        field=field,
        expected=_decimal(expected),
        observed=_decimal(observed),
        tolerance=tolerance,
    )


def reconcile_snapshot_summary(
    snapshot: PortfolioSnapshot,
    summary: Mapping[str, object],
    *,
    valuation_mode: str = "closed_snapshot",
    positions_market_value: object | None = None,
    positions_cost_basis: object | None = None,
    classes_market_value: object | None = None,
) -> dict:
    """Compara o contrato com o snapshot somente quando a base é comparável."""
    snapshot_unrealized = getattr(snapshot, "unrealized_pnl", None)
    if snapshot_unrealized is None:
        snapshot_unrealized = _decimal(snapshot.market_value) - _decimal(snapshot.cost_basis)
    expected_total_result = (
        _decimal(snapshot_unrealized)
        + _decimal(snapshot.realized_pnl)
        + _decimal(snapshot.dividends_accumulated)
    )

    checks = [
        build_reconciliation_check(
            "rentabilidade_total",
            snapshot.accumulated_return_pct,
            summary.get("rentabilidade_total"),
            PERCENT_TOLERANCE,
        )
    ]
    comparable_valuation = valuation_mode == "closed_snapshot"
    if comparable_valuation:
        checks.extend(
            [
                build_reconciliation_check("total_patrimonio", snapshot.market_value, summary.get("total_patrimonio")),
                build_reconciliation_check("total_investido", snapshot.cost_basis, summary.get("total_investido")),
                build_reconciliation_check("lucro_total", expected_total_result, summary.get("lucro_total")),
            ]
        )

    if comparable_valuation and positions_market_value is not None:
        checks.append(build_reconciliation_check("positions_market_value", snapshot.market_value, positions_market_value))
    if comparable_valuation and positions_cost_basis is not None:
        checks.append(build_reconciliation_check("positions_cost_basis", snapshot.cost_basis, positions_cost_basis))
    if comparable_valuation and classes_market_value is not None:
        checks.append(build_reconciliation_check("classes_market_value", snapshot.market_value, classes_market_value))

    serialized = [check.to_dict() for check in checks]
    failed_fields = [item["field"] for item in serialized if not item["is_reconciled"]]
    return {
        "is_reconciled": not failed_fields,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "valuation_mode": valuation_mode,
        "valuation_comparable_to_snapshot": comparable_valuation,
        "valuation_reconciliation_status": "evaluated" if comparable_valuation else "not_comparable_intraday",
        "money_tolerance": float(MONEY_TOLERANCE),
        "percent_tolerance": float(PERCENT_TOLERANCE),
        "failed_fields": failed_fields,
        "checks": serialized,
        "positions_evaluated": comparable_valuation and positions_market_value is not None,
        "classes_evaluated": comparable_valuation and classes_market_value is not None,
    }
