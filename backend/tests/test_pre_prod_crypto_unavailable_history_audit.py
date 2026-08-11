from app.cli import pre_prod_crypto_unavailable_history_audit as audit


def test_target_statuses_are_only_residual_unavailability_states() -> None:
    assert audit.TARGET_STATUSES == (
        "HISTORY_START_SHALLOW_UNAVAILABLE",
        "HISTORY_UNAVAILABLE",
    )
