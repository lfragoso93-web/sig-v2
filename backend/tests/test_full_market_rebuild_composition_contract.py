"""Contrato estrutural da composição do full market rebuild canônico."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_SERVICE = ROOT / "app" / "services" / "full_market_rebuild_service.py"
CANONICAL_SERVICE = ROOT / "app" / "services" / "full_market_rebuild_canonical_service.py"


def test_canonical_rebuild_does_not_monkey_patch_base_module() -> None:
    source = CANONICAL_SERVICE.read_text(encoding="utf-8")

    forbidden_assignments = {
        "base_rebuild._sync_treasury =",
        "base_rebuild._rebuild_all_twr_snapshots =",
        "base_rebuild._step_payload =",
    }

    for assignment in forbidden_assignments:
        assert assignment not in source


def test_base_rebuild_exposes_explicit_step_composition() -> None:
    source = BASE_SERVICE.read_text(encoding="utf-8")

    assert "treasury_operation:" in source
    assert "snapshot_operation:" in source
    assert "step_payload_reader:" in source
