"""Reconciliação financeira dos consumidores do snapshot canônico.

O serviço não corrige valores e não escolhe uma nova fonte de verdade. Ele apenas
compara valores observados com o snapshot e devolve um diagnóstico estruturado.
Posições e classes podem ser informadas pelos respectivos consumidores quando
forem calculadas para a mesma ``snapshot_date``.
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


def _check(
    field: str,
    expected: object,
    observed: object,
    tolerance: Decimal = MONEY_TOLERANCE,
) -> ReconciliationCheck:
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
    positions_market_value: object | None = None,
    positions_cost_basis: object | None = None,
    classes_market_value: object | None = None,
) -> dict:
    """Compara o contrato do Resumo e totais opcionais com o mesmo snapshot."""
    expected_total_result = (
        _decimal(snapshot.unrealized_pnl)
        + _decimal(snapshot.realized_pnl)
        + _decimal(snapshot.dividends_accumulated)
    )

    checks = [
        _check("total_patrimonio", snapshot.market_value, summary.get("total_patrimonio")),
        _check("total_investido", snapshot.cost_basis, summary.get("total_investido")),
        _check(
            "rentabilidade_total",
            snapshot.accumulated_return_pct,
            summary.get("rentabilidade_total"),
            PERCENT_TOLERANCE,
        ),
        _check("lucro_total", expected_total_result, summary.get("lucro_total")),
    ]

    if positions_market_value is not None:
        checks.append(
            _check("positions_market_value", snapshot.market_value, positions_market_value)
        )
    if positions_cost_basis is not None:
        checks.append(
            _check("positions_cost_basis", snapshot.cost_basis, positions_cost_basis)
        )
    if classes_market_value is not None:
        checks.append(
            _check("classes_market_value", snapshot.market_value, classes_market_value)
        )

    serialized = [check.to_dict() for check in checks]
    failed_fields = [item["field"] for item in serialized if not item["is_reconciled"]]

    return {
        "is_reconciled": not failed_fields,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "money_tolerance": float(MONEY_TOLERANCE),
        "percent_tolerance": float(PERCENT_TOLERANCE),
        "failed_fields": failed_fields,
        "checks": serialized,
        "positions_evaluated": positions_market_value is not None,
        "classes_evaluated": classes_market_value is not None,
    }
