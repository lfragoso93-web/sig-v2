from __future__ import annotations

from pathlib import Path

from app.integrations.bcb_sgs import SGS_INDICATORS


SERVICE_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "benchmark_rate_service.py"


def test_benchmark_contract_has_four_required_official_series() -> None:
    assert set(SGS_INDICATORS) == {"CDI", "SELIC", "IPCA", "IGPM"}
    assert {meta.sgs_code for meta in SGS_INDICATORS.values()} == {11, 12, 189, 433}


def test_benchmark_service_uses_persisted_identity_without_runtime_ddl() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "on_conflict_do_update" in source
    assert "RateHistory.indicator" in source
    assert "RateHistory.date" in source
    assert "CREATE UNIQUE INDEX" not in source
    assert "ensure_rate_history_unique_index" not in source
    assert "scheduler" not in source.lower().split('"""', 2)[1]
