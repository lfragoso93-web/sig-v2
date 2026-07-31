from __future__ import annotations

from dataclasses import replace

from app.services.pre_prod_dividends_seed_contract import (
    DividendsSeedCounts,
    DividendsSeedCoverage,
    DividendsSeedIntegrity,
    DividendsSeedTransaction,
    DividendsSeedWindow,
    PreProdDividendsSeedResult,
)
from app.services.pre_prod_dividends_seed_idempotency import (
    DIVIDENDS_SEED_IDEMPOTENCY_SCHEMA_VERSION,
    compare_dividends_seed_runs,
)

COUNTS = DividendsSeedCounts(10, 30, 1)
COVERAGE = DividendsSeedCoverage(
    first_ex_date="2020-01-02",
    last_ex_date="2026-07-28",
    assets_with_events=8,
)
GROUPINGS = (
    {
        "asset_class": "ACAO",
        "event_type": "DIVIDENDO",
        "source": "brapi",
        "year": 2026,
        "ticker": "PETR4",
        "global_events": 2,
    },
)
SOURCES = (
    {
        "source": "brapi",
        "assets": 1,
        "raw_rows": 2,
        "normalized_rows": 2,
        "empty": 0,
    },
)


def _run(
    run_id: str,
    *,
    before: DividendsSeedCounts = COUNTS,
    created: int = 0,
) -> PreProdDividendsSeedResult:
    return PreProdDividendsSeedResult(
        run_id=run_id,
        branch="stable-15jun",
        commit_sha="a" * 40,
        generated_at="2026-07-28T21:00:00+00:00",
        ok=True,
        window=DividendsSeedWindow("2020-01-01", "2026-07-28"),
        before=before,
        after=COUNTS,
        coverage=COVERAGE,
        integrity=DividendsSeedIntegrity(),
        transaction=DividendsSeedTransaction("committed", True, False),
        groupings=GROUPINGS,
        sources=SOURCES,
        collection={"assets": 1, "normalized_rows": 2},
        global_persistence={"created": created, "updated": 0, "unchanged": 2},
    )


def test_accepts_stable_consecutive_runs() -> None:
    result = compare_dividends_seed_runs(
        _run("20260728-180000", created=2),
        _run("20260728-180200"),
    )

    assert result.ok is True
    assert result.errors == ()
    assert result.stable_groupings is True
    assert result.zero_physical_writes_on_second_run is True
    assert result.schema_version == DIVIDENDS_SEED_IDEMPOTENCY_SCHEMA_VERSION


def test_rejects_second_run_with_physical_writes() -> None:
    result = compare_dividends_seed_runs(
        _run("20260728-180000", created=2),
        _run("20260728-180200", created=1),
    )

    assert result.ok is False
    assert "linhas físicas" in result.errors[0]


def test_rejects_changed_groupings_and_sources() -> None:
    second = replace(
        _run("20260728-180200"),
        groupings=(),
        sources=(),
    )

    result = compare_dividends_seed_runs(
        _run("20260728-180000", created=2),
        second,
    )

    assert result.ok is False
    assert result.stable_groupings is False
    assert result.stable_sources is False


def test_rejects_contract_and_baseline_divergence() -> None:
    changed = DividendsSeedCounts(10, 31, 1)
    second = replace(
        _run("20260728-180200", before=changed),
        commit_sha="b" * 40,
    )

    result = compare_dividends_seed_runs(
        _run("20260728-180000", created=2),
        second,
    )

    assert result.ok is False
    assert result.same_contract is False
    assert result.chained_baseline is False


def test_rejects_same_run_id() -> None:
    first = _run("20260728-180000")

    result = compare_dividends_seed_runs(first, first)

    assert result.ok is False
    assert "run_id distintos" in result.errors[0]
