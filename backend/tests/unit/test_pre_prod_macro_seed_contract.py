from __future__ import annotations

import pytest

from app.services.pre_prod_macro_seed_contract import (
    MACRO_SEED_BRANCH,
    MacroIndicatorState,
    MacroSeedContractError,
    MacroSeedState,
    PreProdMacroSeedResult,
    validate_macro_seed_identity,
)


SHA40 = "a" * 40


def _state(*, duplicate_rows: int = 0) -> MacroSeedState:
    return MacroSeedState(
        total_rows=4,
        indicators=(
            MacroIndicatorState(
                indicator="CDI",
                rows=1,
                first_date="2026-01-02",
                last_date="2026-01-02",
                duplicate_rows=duplicate_rows,
            ),
            MacroIndicatorState(
                indicator="SELIC",
                rows=1,
                first_date="2026-01-02",
                last_date="2026-01-02",
            ),
            MacroIndicatorState(
                indicator="IPCA",
                rows=1,
                first_date="2026-01-01",
                last_date="2026-01-01",
            ),
            MacroIndicatorState(
                indicator="IGPM",
                rows=1,
                first_date="2026-01-01",
                last_date="2026-01-01",
            ),
        ),
    )


def test_identity_accepts_only_operational_shape() -> None:
    validate_macro_seed_identity(
        run_id="20260725-235959",
        branch=MACRO_SEED_BRANCH,
        commit_sha=SHA40,
    )


@pytest.mark.parametrize(
    ("run_id", "branch", "commit_sha"),
    [
        ("2026-07-25", MACRO_SEED_BRANCH, SHA40),
        ("20260725-235959", "main", SHA40),
        ("20260725-235959", MACRO_SEED_BRANCH, "ABC"),
    ],
)
def test_identity_rejects_invalid_operational_shape(
    run_id: str,
    branch: str,
    commit_sha: str,
) -> None:
    with pytest.raises(MacroSeedContractError):
        validate_macro_seed_identity(
            run_id=run_id,
            branch=branch,
            commit_sha=commit_sha,
        )


def test_indicator_rejects_incomplete_coverage() -> None:
    with pytest.raises(MacroSeedContractError):
        MacroIndicatorState(
            indicator="CDI",
            rows=1,
            first_date="2026-01-01",
        )


def test_state_rejects_repeated_indicators() -> None:
    item = MacroIndicatorState(indicator="CDI", rows=0)
    with pytest.raises(MacroSeedContractError):
        MacroSeedState(total_rows=0, indicators=(item, item))


def test_ok_result_requires_reconciled_integrity() -> None:
    with pytest.raises(MacroSeedContractError):
        PreProdMacroSeedResult(
            run_id="20260725-235959",
            branch=MACRO_SEED_BRANCH,
            commit_sha=SHA40,
            started_at="2026-07-25T23:59:00+00:00",
            finished_at="2026-07-25T23:59:01+00:00",
            duration_seconds=1.0,
            ok=True,
            before=_state(),
            after=_state(duplicate_rows=1),
            imported={"CDI": 1},
        )


def test_result_serializes_versioned_envelope() -> None:
    result = PreProdMacroSeedResult(
        run_id="20260725-235959",
        branch=MACRO_SEED_BRANCH,
        commit_sha=SHA40,
        started_at="2026-07-25T23:59:00+00:00",
        finished_at="2026-07-25T23:59:01+00:00",
        duration_seconds=1.0,
        ok=True,
        before=_state(),
        after=_state(),
        imported={"CDI": 1, "SELIC": 1, "IPCA": 1, "IGPM": 1},
    )

    payload = result.to_dict()

    assert payload["schema_version"] == "pre-prod-macro-seed.v1"
    assert payload["ok"] is True
    assert payload["after"]["indicators"][0]["indicator"] == "CDI"
