from pathlib import Path


CLI = Path("app/cli/pre_prod_crypto_batch_selection.py")


def test_crypto_batch_selection_cli_is_db_only_and_explicitly_limited():
    content = CLI.read_text(encoding="utf-8")

    assert "DEFAULT_LIMIT = 50" in content
    assert "MAX_LIMIT = 100" in content
    assert "AsyncSessionLocal" in content
    assert "AssetPrice" in content
    assert "AssetType.CRIPTO" in content
    assert "--limit" in content
    assert "--after-ticker" in content
    assert "fetch_brapi" not in content
    assert "yfinance" not in content
    assert "commit(" not in content
    assert "flush(" not in content
    assert "add(" not in content
