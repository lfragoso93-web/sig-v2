from pathlib import Path


ADMIN_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "routers"
    / "admin.py"
)


def test_legacy_admin_provider_ports_remain_explicitly_tracked_until_removal() -> None:
    source = ADMIN_PATH.read_text(encoding="utf-8")
    assert '"/assets/seed"' in source
    assert '"/prices/backfill"' in source
    assert '"/snapshots/backfill"' in source
