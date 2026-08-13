from app.cli import pre_prod_crypto_gap_classification_audit as audit


def test_gap_bucket_boundaries() -> None:
    assert audit._gap_bucket(None) == "unknown"
    assert audit._gap_bucket(0) == "up_to_30_days"
    assert audit._gap_bucket(30) == "up_to_30_days"
    assert audit._gap_bucket(31) == "31_to_90_days"
    assert audit._gap_bucket(90) == "31_to_90_days"
    assert audit._gap_bucket(91) == "91_to_365_days"
    assert audit._gap_bucket(365) == "91_to_365_days"
    assert audit._gap_bucket(366) == "over_365_days"
