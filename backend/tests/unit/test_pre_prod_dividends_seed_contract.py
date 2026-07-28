import pytest
from app.services.pre_prod_dividends_seed_contract import (
    DIVIDENDS_SEED_BRANCH,
    DIVIDENDS_SEED_READ_TABLES,
    DIVIDENDS_SEED_SCHEMA_VERSION,
    DIVIDENDS_SEED_WRITE_TABLES,
    DividendsSeedContractError,
    DividendsSeedCounts,
    DividendsSeedCoverage,
    DividendsSeedIntegrity,
    DividendsSeedTableBoundary,
    DividendsSeedTransaction,
    DividendsSeedWindow,
    PreProdDividendsSeedResult,
    validate_dividends_seed_identity,
)

_VALID_SHA = "a" * 40


def _counts() -> DividendsSeedCounts:
    return DividendsSeedCounts(
        assets=10,
        transactions=20,
        portfolios=2,
        asset_dividends=30,
        dividends=12,
        sync_jobs=1,
    )


def _result(**overrides) -> PreProdDividendsSeedResult:
    values = {
        "run_id": "20260728-180000",
        "branch": DIVIDENDS_SEED_BRANCH,
        "commit_sha": _VALID_SHA,
        "generated_at": "2026-07-28T21:00:00+00:00",
        "ok": True,
        "window": DividendsSeedWindow(
            start_date="2020-01-01",
            end_date="2026-07-28",
        ),
        "before": _counts(),
        "after": _counts(),
        "coverage": DividendsSeedCoverage(
            first_ex_date="2020-01-02",
            last_ex_date="2026-07-28",
            assets_with_events=8,
            portfolios_with_dividends=2,
        ),
        "integrity": DividendsSeedIntegrity(),
        "transaction": DividendsSeedTransaction(
            final_state="committed",
            committed=True,
            rollback_performed=False,
        ),
    }
    values.update(overrides)
    return PreProdDividendsSeedResult(**values)


def test_validate_identity_accepts_canonical_values() -> None:
    validate_dividends_seed_identity(
        run_id="20260728-180000",
        branch=DIVIDENDS_SEED_BRANCH,
        commit_sha=_VALID_SHA,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", "2026-07-28"),
        ("branch", "main"),
        ("commit_sha", "ABC123"),
    ],
)
def test_validate_identity_rejects_invalid_values(
    field: str,
    value: str,
) -> None:
    kwargs = {
        "run_id": "20260728-180000",
        "branch": DIVIDENDS_SEED_BRANCH,
        "commit_sha": _VALID_SHA,
    }
    kwargs[field] = value

    with pytest.raises(DividendsSeedContractError):
        validate_dividends_seed_identity(**kwargs)


def test_table_boundary_is_exact_and_immutable() -> None:
    boundary = DividendsSeedTableBoundary()

    assert boundary.read == DIVIDENDS_SEED_READ_TABLES
    assert boundary.write == DIVIDENDS_SEED_WRITE_TABLES
    assert boundary.inspect_only == ("dividends_sync_jobs",)

    with pytest.raises(DividendsSeedContractError, match="escrita"):
        DividendsSeedTableBoundary(write=("dividends", "transactions"))


def test_result_serializes_minimum_canonical_envelope() -> None:
    payload = _result().to_dict()

    assert payload["schema_version"] == DIVIDENDS_SEED_SCHEMA_VERSION
    assert payload["identity"] == {
        "branch": DIVIDENDS_SEED_BRANCH,
        "commit_sha": _VALID_SHA,
    }
    assert payload["authorized_tables"]["write"] == (
        "asset_dividends",
        "dividends",
    )
    assert payload["transaction"]["final_state"] == "committed"
    for section in (
        "window",
        "sources",
        "before",
        "collection",
        "global_persistence",
        "materialization",
        "after",
        "coverage",
        "integrity",
        "errors",
        "ok",
    ):
        assert section in payload


def test_result_ok_rejects_blocking_integrity_finding() -> None:
    with pytest.raises(DividendsSeedContractError, match="integridade"):
        _result(
            integrity=DividendsSeedIntegrity(
                duplicate_materializations=1,
            )
        )


def test_coverage_rejects_more_materialized_rights_than_eligible() -> None:
    with pytest.raises(DividendsSeedContractError, match="excedem"):
        DividendsSeedCoverage(
            eligible_materializations=1,
            materialized_eligible_rights=2,
        )


def test_result_ok_requires_committed_transaction() -> None:
    with pytest.raises(DividendsSeedContractError, match="confirmada"):
        _result(
            transaction=DividendsSeedTransaction(
                final_state="blocked",
                committed=False,
                rollback_performed=False,
            )
        )


def test_failed_result_preserves_errors_and_rollback_state() -> None:
    payload = _result(
        ok=False,
        errors=("provider unavailable",),
        transaction=DividendsSeedTransaction(
            final_state="rolled_back",
            committed=False,
            rollback_performed=True,
        ),
    ).to_dict()

    assert payload["ok"] is False
    assert payload["errors"] == ("provider unavailable",)
    assert payload["transaction"]["rollback_performed"] is True
