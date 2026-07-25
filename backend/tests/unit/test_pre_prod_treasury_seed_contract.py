from __future__ import annotations

from dataclasses import replace

import pytest

from app.services.pre_prod_treasury_seed_contract import (
    TREASURY_SEED_SCHEMA_VERSION,
    PreProdTreasurySeedResult,
    TreasurySeedContractError,
    TreasurySeedCounts,
    TreasurySeedCoverage,
)


def _result(*, ok: bool = True) -> PreProdTreasurySeedResult:
    return PreProdTreasurySeedResult(
        started_at="2026-07-25T17:00:00+00:00",
        finished_at="2026-07-25T17:01:00+00:00",
        duration_seconds=60.0,
        ok=ok,
        before=TreasurySeedCounts(assets=24, aliases=10, prices=1488),
        after=TreasurySeedCounts(assets=24, aliases=10, prices=1488),
        coverage=TreasurySeedCoverage(
            first_price_date="2023-08-01",
            last_price_date="2026-07-25",
            priced_assets=24,
        ),
        catalog={"created": 0, "updated": 0},
        history={"inserted": 0, "updated": 0},
    )


def test_contract_serializes_versioned_auditable_result() -> None:
    payload = _result().to_dict()

    assert payload["schema_version"] == TREASURY_SEED_SCHEMA_VERSION
    assert payload["ok"] is True
    assert payload["after"]["orphan_prices"] == 0
    assert payload["coverage"]["priced_assets"] == 24


@pytest.mark.parametrize(
    "field",
    (
        "orphan_prices",
        "duplicate_prices",
        "legacy_assets",
        "legacy_prices",
    ),
)
def test_success_rejects_nonzero_integrity_findings(field: str) -> None:
    result = _result()
    invalid_after = replace(result.after, **{field: 1})

    with pytest.raises(TreasurySeedContractError, match=field):
        replace(result, after=invalid_after)


def test_failed_result_may_report_errors_and_integrity_findings() -> None:
    result = _result(ok=False)
    failed = replace(
        result,
        after=replace(result.after, orphan_prices=2),
        errors=("history rebuild failed",),
    )

    assert failed.ok is False
    assert failed.errors == ("history rebuild failed",)


def test_success_rejects_errors() -> None:
    with pytest.raises(TreasurySeedContractError, match="errors"):
        replace(_result(), errors=("unexpected",))


def test_coverage_requires_complete_ordered_interval() -> None:
    with pytest.raises(TreasurySeedContractError, match="informadas juntas"):
        TreasurySeedCoverage(first_price_date="2023-08-01")

    with pytest.raises(TreasurySeedContractError, match="posterior"):
        TreasurySeedCoverage(
            first_price_date="2026-07-25",
            last_price_date="2023-08-01",
        )


def test_counts_reject_negative_values() -> None:
    with pytest.raises(TreasurySeedContractError, match="prices"):
        TreasurySeedCounts(assets=1, aliases=0, prices=-1)
