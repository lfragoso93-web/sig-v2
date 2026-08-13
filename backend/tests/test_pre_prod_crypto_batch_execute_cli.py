from pathlib import Path


CLI = Path("app/cli/pre_prod_crypto_batch_execute.py")


def test_crypto_batch_execute_chunks_seed_and_aborts_on_blocking_statuses():
    content = CLI.read_text(encoding="utf-8")

    assert "select_batch" in content
    assert "run_seed" in content
    assert "MAX_TICKERS_PER_RUN" in content
    assert "HISTORY_START_TRUNCATED" in content
    assert "HISTORY_START_COMPLEMENT_GAPPED" in content
    assert "HISTORY_START_COMPLEMENT_UNAVAILABLE" in content
    assert "blocking" in content
    assert "fetch_brapi" not in content
    assert "yfinance" not in content
    assert "requests." not in content


def test_crypto_batch_execute_never_processes_more_than_50_selected_assets():
    content = CLI.read_text(encoding="utf-8")

    assert "MAX_OPERATIONAL_BATCH = 50" in content
    assert "min(MAX_OPERATIONAL_BATCH" in content
