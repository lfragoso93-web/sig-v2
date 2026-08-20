from pathlib import Path


ENTRYPOINT = Path(__file__).resolve().parents[1] / "entrypoint.sh"


def test_runtime_startup_stops_before_guarded_dividend_contraction() -> None:
    script = ENTRYPOINT.read_text(encoding="utf-8")

    assert "alembic upgrade heads" not in script
    assert 'RUNTIME_MIGRATION_TARGET="20260729_dividend_identity"' in script
    assert 'alembic upgrade "${RUNTIME_MIGRATION_TARGET}"' in script
    assert "20260731_drop_legacy_divs" in script
