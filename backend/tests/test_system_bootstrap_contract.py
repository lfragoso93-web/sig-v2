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
        'BOOTSTRAP_SCHEMA_VERSION = "system-bootstrap.v4"',
        "class BootstrapStageResult",
        "class SystemBootstrapReport",
        '"b3_baseline"',
        '"asset_catalog"',
        '"treasury_catalog"',
        '"treasury_reconciliation"',
        '"treasury_history"',
        '"asset_price_history"',
        '"benchmarks"',
        '"fx_rates"',
        '"asset_dividends"',
        '"corporate_events"',
        "run_system_bootstrap_fx_stage",
        "run_system_bootstrap_dividends_stage",
        "run_system_bootstrap_corporate_events_stage",
        "run_pre_prod_b3_seed",
        "run_system_bootstrap",
    }

    missing = sorted(token for token in required if token not in source)
    assert missing == []


def test_system_bootstrap_does_not_bypass_domain_boundaries() -> None:
    source = _source()

    forbidden_runtime_imports = {
        "proventos_daily_sync_service",
        "corporate_event_service",
        "dividend_backfill_service",
        "pre_prod_dividends_seed_service",
        "treasury_price_history_service",
    }

    findings = sorted(token for token in forbidden_runtime_imports if token in source)
    assert findings == []


def test_treasury_history_stage_uses_official_provider_boundary() -> None:
    source = _source()

    assert "treasury_official_history_service" in source
    assert "rebuild_official_treasury_history" in source
    assert "primary_source" in source
    assert "fallback_source" in source
    assert "required_empty_payloads" in source
    assert "unresolved_assets" in source


def test_asset_catalog_stage_reconciles_existing_catalog_without_market_backfill() -> None:
    source = _source()

    assert '"b3_baseline"' in source
    assert '"asset_catalog"' in source
    assert "brapi_enrichment_and_crypto" in source
    assert "seed = await run_asset_seed(db)" in source
    assert "run_backfill" not in source
    assert "run_market_enrichment" not in source
    assert "assets já populado" not in source
    assert "select(func.count()).select_from(Asset)" not in source
