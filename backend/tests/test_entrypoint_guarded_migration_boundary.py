from pathlib import Path


ENTRYPOINT = Path(__file__).resolve().parents[1] / "entrypoint.sh"


def test_runtime_startup_uses_explicit_validated_migration_target() -> None:
    script = ENTRYPOINT.read_text(encoding="utf-8")

    assert "alembic upgrade heads" not in script
    assert 'RUNTIME_MIGRATION_TARGET="20260820_dividend_occurrence"' in script
    assert 'alembic upgrade "${RUNTIME_MIGRATION_TARGET}"' in script
    assert "20260729_dividend_identity" not in script
