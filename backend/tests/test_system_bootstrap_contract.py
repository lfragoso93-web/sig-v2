from pathlib import Path


BOOTSTRAP_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "system_bootstrap_service.py"
)


def _source() -> str:
    return BOOTSTRAP_PATH.read_text(encoding="utf-8")


def test_system_bootstrap_has_structured_report_and_explicit_stages() -> None:
    source = _source()

    required = {
        'BOOTSTRAP_SCHEMA_VERSION = "system-bootstrap.v2"',
        "class BootstrapStageResult",
        "class SystemBootstrapReport",
        '"asset_catalog"',
        '"treasury_catalog"',
        '"treasury_reconciliation"',
        '"treasury_history"',
        '"asset_price_history"',
        '"benchmarks"',
        '"fx_rates"',
        "run_system_bootstrap_fx_stage",
        "run_system_bootstrap",
    }

    missing = sorted(token for token in required if token not in source)
    assert missing == []


def test_system_bootstrap_does_not_silently_add_still_blocked_domains() -> None:
    source = _source()

    forbidden_runtime_imports = {
        "proventos_daily_sync_service",
        "corporate_event_service",
        "dividend_backfill_service",
        "pre_prod_dividends_seed_service",
    }

    findings = sorted(token for token in forbidden_runtime_imports if token in source)
    assert findings == []
