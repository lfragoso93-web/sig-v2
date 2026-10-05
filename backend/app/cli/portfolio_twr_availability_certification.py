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
    "RENDA_FIXA": (True, "available"),
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

    print(
        "CERT303-TWR-AVAILABILITY",
        " ".join(
            f"{asset_type}={'available' if available else status}"
            for asset_type, (available, status) in sorted(actual.items())
        ),
        "scope=availability-only",
        "rf_daily_twr=true",
        "issue149=closed",
        f"status={'PASS' if not failures else 'FAIL'}",
    )
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    main()
