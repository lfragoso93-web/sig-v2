from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _source() -> str:
    return MAIN_PATH.read_text(encoding="utf-8")


def test_main_uses_only_global_system_bootstrap_entrypoint() -> None:
    source = _source()

    assert "run_system_bootstrap" in source
    assert "_run_startup_bootstrap" in source
    assert "_boot_sequence" not in source


def test_main_does_not_own_domain_seed_or_backfill_logic() -> None:
    source = _source()

    forbidden = {
        "run_asset_seed",
        "seed_treasury_assets",
        "reconcile_treasury_transactions",
        "import_missing_treasury_price_history",
        "run_global_asset_price_backfill",
        "import_missing_benchmark_history",
    }

    findings = sorted(token for token in forbidden if token in source)
    assert findings == []
