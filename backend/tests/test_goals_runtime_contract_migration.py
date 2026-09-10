from pathlib import Path


def test_goals_runtime_contract_migration_is_runtime_target() -> None:
    entrypoint = Path("entrypoint.sh").read_text(encoding="utf-8")
    migration = Path(
        "alembic/versions/20260910_goals_runtime_contract.py"
    ).read_text(encoding="utf-8")

    assert 'RUNTIME_MIGRATION_TARGET="20260910_goals_runtime"' in entrypoint
    assert 'down_revision: str = "20260820_dividend_occurrence"' in migration
    assert "ADD COLUMN IF NOT EXISTS current_value" in migration
    assert "ADD COLUMN IF NOT EXISTS base_value" in migration
    assert "ADD COLUMN IF NOT EXISTS monthly_contribution" in migration
    assert "ALTER COLUMN goal_type TYPE VARCHAR" in migration
