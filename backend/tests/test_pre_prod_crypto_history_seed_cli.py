from pathlib import Path


CLI_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cli"
    / "pre_prod_crypto_history_seed.py"
)


def _source() -> str:
    return CLI_PATH.read_text(encoding="utf-8")


def test_crypto_history_seed_exposes_db_only_dry_run() -> None:
    source = _source()

    assert 'parser.add_argument("--dry-run", action="store_true")' in source
    assert "audit_asset_price_coverage" in source
    assert "if args.dry_run:" in source
    assert "run_global_asset_price_backfill(" in source


def test_crypto_history_seed_bounds_concurrency() -> None:
    source = _source()

    assert "MAX_CONCURRENCY = 4" in source
    assert "min(MAX_CONCURRENCY, max(1, args.concurrency))" in source


def test_crypto_history_seed_can_scope_dry_run_and_execution_by_ticker() -> None:
    source = _source()

    assert 'parser.add_argument("--ticker", action="append", default=None)' in source
    assert "normalized_tickers" in source
    assert "item.ticker.upper() in normalized_tickers" in source
    assert "tickers=normalized_tickers" in source
