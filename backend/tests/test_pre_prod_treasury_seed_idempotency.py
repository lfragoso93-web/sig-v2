from __future__ import annotations

from dataclasses import replace

from app.services.pre_prod_treasury_seed_contract import (
    PreProdTreasurySeedResult,
    TreasurySeedCounts,
    TreasurySeedCoverage,
)
from app.services.pre_prod_treasury_seed_idempotency import (
    TREASURY_SEED_IDEMPOTENCY_SCHEMA_VERSION,
    compare_treasury_seed_runs,
)

BRANCH = "stable-15jun"
COMMIT_SHA = "a" * 40
COUNTS = TreasurySeedCounts(assets=24, aliases=10, prices=1488)
COVERAGE = TreasurySeedCoverage(
    first_price_date="2023-08-01",
    last_price_date="2026-07-25",
    priced_assets=24,
)


def _run(*, run_id: str, before: TreasurySeedCounts = COUNTS) -> PreProdTreasurySeedResult:
    return PreProdTreasurySeedResult(
        run_id=run_id,
        branch=BRANCH,
        commit_sha=COMMIT_SHA,
        started_at="2026-07-25T20:00:00+00:00",
        finished_at="2026-07-25T20:01:00+00:00",
        duration_seconds=60.0,
        ok=True,
        before=before,
        after=COUNTS,
        coverage=COVERAGE,
    )


def test_compare_accepts_stable_consecutive_runs() -> None:
    result = compare_treasury_seed_runs(
        _run(run_id="20260725-200000"),
        _run(run_id="20260725-200200"),
    )

    assert result.ok is True
    assert result.errors == ()
    assert result.same_state is True
    assert result.same_coverage is True
    assert result.chained_baseline is True
    assert result.to_dict()["schema_version"] == TREASURY_SEED_IDEMPOTENCY_SCHEMA_VERSION


def test_compare_rejects_same_run_id() -> None:
    first = _run(run_id="20260725-200000")
    result = compare_treasury_seed_runs(first, first)

    assert result.ok is False
    assert "run_id distintos" in result.errors[0]


def test_compare_rejects_different_commit() -> None:
    first = _run(run_id="20260725-200000")
    second = replace(
        _run(run_id="20260725-200200"),
        commit_sha="b" * 40,
    )

    result = compare_treasury_seed_runs(first, second)

    assert result.ok is False
    assert "mesmo commit_sha" in result.errors[0]


def test_compare_rejects_unstable_state_and_baseline() -> None:
    first = _run(run_id="20260725-200000")
    changed = TreasurySeedCounts(assets=24, aliases=10, prices=1489)
    second = replace(
        _run(run_id="20260725-200200", before=changed),
        after=changed,
    )

    result = compare_treasury_seed_runs(first, second)

    assert result.ok is False
    assert result.chained_baseline is False
    assert result.same_state is False
    assert len(result.errors) == 2


def test_compare_rejects_failed_run() -> None:
    first = _run(run_id="20260725-200000")
    second = replace(
        _run(run_id="20260725-200200"),
        ok=False,
        errors=("falha operacional",),
    )

    result = compare_treasury_seed_runs(first, second)

    assert result.ok is False
    assert "segunda execução" in result.errors[0]
