"""CLI sem escrita para certificar a fronteira TWR da carteira sintética #303."""

from __future__ import annotations

from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.models.asset import AssetType
from app.services.portfolio_class_snapshot_service import class_twr_availability

_EXPECTED = {
    "ACAO": (True, "available"),
    "BDR": (True, "available"),
    "CRIPTO": (True, "available"),
    "ETF_NACIONAL": (True, "available"),
    "FII": (True, "available"),
    "RENDA_FIXA": (False, "dedicated_history_not_available"),
    "TESOURO_DIRETO": (True, "available"),
}


def main() -> None:
    fixture = load_portfolio_synthetic_certification_fixture()
    asset_types = {
        AssetType(str(transaction["asset_type"]))
        for transaction in fixture["transactions"]
    }
    rows = class_twr_availability(asset_types)
    actual = {
        row["asset_type"]: (bool(row["available"]), str(row["status"]))
        for row in rows
    }

    failures: list[str] = []
    if actual != _EXPECTED:
        failures.append(f"availability:actual={actual}:expected={_EXPECTED}")

    renda_fixa = next(row for row in rows if row["asset_type"] == "RENDA_FIXA")
    if not renda_fixa["reason"]:
        failures.append("renda-fixa:missing-unavailability-reason")

    print(
        "CERT303-TWR-AVAILABILITY",
        " ".join(
            f"{asset_type}={'available' if available else status}"
            for asset_type, (available, status) in sorted(actual.items())
        ),
        "scope=availability-only",
        "rf_daily_twr=false",
        "issue149=open",
        f"status={'PASS' if not failures else 'FAIL'}",
    )
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    main()
