from pathlib import Path


SCHEDULER_PATH = Path(__file__).resolve().parents[1] / "app" / "core" / "scheduler.py"


def _scheduler_source() -> str:
    return SCHEDULER_PATH.read_text(encoding="utf-8")


def test_scheduler_only_runs_recurring_price_provider_jobs() -> None:
    source = _scheduler_source()

    forbidden = {
        "seed_treasury_assets",
        "benchmark_rate_service",
        "proventos_daily_sync_service",
        "run_daily_proventos_sync",
        "market_pipeline_batch_service",
        "run_market_pipeline_batch",
        "sync_logo=True",
        "sync_events=True",
    }

    findings = sorted(token for token in forbidden if token in source)
    assert findings == []


def test_scheduler_keeps_price_and_local_snapshot_jobs() -> None:
    source = _scheduler_source()

    required = {
        "refresh_quotes_and_invalidate",
        "run_global_asset_price_backfill",
        "import_treasury_price_history",
        "maintain_twr_snapshots_for_active_portfolios",
        'id="persist_daily_close_prices"',
        'id="persist_treasury_daily_close"',
    }

    missing = sorted(token for token in required if token not in source)
    assert missing == []


def test_daily_close_does_not_trigger_broad_historical_backfill() -> None:
    source = _scheduler_source()

    assert "today = date.today()" in source
    assert "required_to=today" in source
    assert "history_start=today" in source
