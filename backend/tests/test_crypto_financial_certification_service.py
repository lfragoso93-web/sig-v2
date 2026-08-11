from app.services.crypto_financial_certification_service import (
    FINANCIALLY_CERTIFIED_CRYPTO_STATUSES,
    is_crypto_financially_certified,
)


def test_financial_certification_allows_only_explicit_terminal_states() -> None:
    assert FINANCIALLY_CERTIFIED_CRYPTO_STATUSES == {
        "HISTORY_START_EXHAUSTED",
        "HISTORY_START_SHALLOW_VERIFIED",
    }
    assert is_crypto_financially_certified("HISTORY_START_EXHAUSTED") is True
    assert is_crypto_financially_certified("history_start_shallow_verified") is True


def test_financial_certification_fails_closed_for_other_states() -> None:
    blocked = (
        None,
        "",
        "ACTIVE",
        "HISTORY_UNAVAILABLE",
        "HISTORY_START_TRUNCATED",
        "HISTORY_START_COMPLEMENT_GAPPED",
        "HISTORY_START_COMPLEMENT_UNAVAILABLE",
        "HISTORY_START_SHALLOW",
        "HISTORY_START_SHALLOW_UNAVAILABLE",
        "SOME_FUTURE_STATUS",
    )

    assert all(not is_crypto_financially_certified(status) for status in blocked)
