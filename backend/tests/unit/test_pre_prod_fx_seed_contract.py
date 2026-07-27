import pytest

from app.services.pre_prod_fx_seed_contract import (
    FX_SEED_BRANCH,
    FX_SEED_SCHEMA_VERSION,
    FxPairState,
    FxSeedContractError,
    FxSeedState,
    PreProdFxSeedResult,
    validate_fx_seed_identity,
)


_VALID_SHA = "a" * 40


def _state(*, duplicate_rows: int = 0, unsupported_pairs: tuple[str, ...] = ()) -> FxSeedState:
    return FxSeedState(
        total_rows=10,
        pairs=(
            FxPairState(
                pair="USD-BRL",
                rows=10,
                first_date="2026-01-02",
                last_date="2026-01-15",
                duplicate_rows=duplicate_rows,
            ),
        ),
        unsupported_pairs=unsupported_pairs,
    )


def test_validate_fx_seed_identity_accepts_canonical_identity() -> None:
    validate_fx_seed_identity(
        run_id="20260726-173000",
        branch=FX_SEED_BRANCH,
        commit_sha=_VALID_SHA,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", "2026-07-26"),
        ("branch", "main"),
        ("commit_sha", "ABC123"),
    ],
)
def test_validate_fx_seed_identity_rejects_invalid_values(field: str, value: str) -> None:
    kwargs = {
        "run_id": "20260726-173000",
        "branch": FX_SEED_BRANCH,
        "commit_sha": _VALID_SHA,
    }
    kwargs[field] = value

    with pytest.raises(FxSeedContractError):
        validate_fx_seed_identity(**kwargs)


def test_fx_pair_state_rejects_unsupported_pair() -> None:
    with pytest.raises(FxSeedContractError, match="não suportado"):
        FxPairState(pair="EUR-BRL", rows=0)


def test_fx_seed_state_exposes_duplicate_rows() -> None:
    state = _state(duplicate_rows=2)

    assert state.duplicate_rows == 2


def test_result_serializes_canonical_contract() -> None:
    result = PreProdFxSeedResult(
        run_id="20260726-173000",
        branch=FX_SEED_BRANCH,
        commit_sha=_VALID_SHA,
        started_at="2026-07-26T20:30:00+00:00",
        finished_at="2026-07-26T20:30:01+00:00",
        duration_seconds=1.0,
        ok=True,
        before=_state(),
        after=_state(),
        imported={"USD-BRL": 0},
    )

    payload = result.to_dict()

    assert payload["schema_version"] == FX_SEED_SCHEMA_VERSION
    assert payload["source"] == "BCB"
    assert payload["rate_type"] == "PTAX_SELL"
    assert payload["after"]["pairs"][0]["pair"] == "USD-BRL"


@pytest.mark.parametrize(
    "after",
    [
        _state(duplicate_rows=1),
        _state(unsupported_pairs=("EUR-BRL",)),
    ],
)
def test_result_ok_rejects_invalid_final_state(after: FxSeedState) -> None:
    with pytest.raises(FxSeedContractError):
        PreProdFxSeedResult(
            run_id="20260726-173000",
            branch=FX_SEED_BRANCH,
            commit_sha=_VALID_SHA,
            started_at="2026-07-26T20:30:00+00:00",
            finished_at="2026-07-26T20:30:01+00:00",
            duration_seconds=1.0,
            ok=True,
            before=_state(),
            after=after,
        )
