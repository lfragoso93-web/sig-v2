from pathlib import Path


SOURCE = Path("app/cli/pre_prod_crypto_seam_audit.py")


def test_crypto_seam_audit_is_db_only_and_reports_gap_classes() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "AsyncSessionLocal" in source
    assert "AssetPrice" in source
    assert "brapi_v2_crypto_max" in source
    assert "yfinance_crypto_ptax_brl_max" in source
    assert "HISTORY_START_COMPLEMENT_GAPPED" in source
    assert '"read_only": True' in source
    assert '"gapped"' in source
    assert '"continuous"' in source
    assert "fetch_brapi" not in source
    assert "yfinance" not in source.replace("yfinance_crypto_ptax_brl_max", "")
    assert ".commit(" not in source
    assert ".execute(Asset.__table__.update" not in source
    assert "insert(" not in source
