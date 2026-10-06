from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_goals_runtime_contract_precedes_current_runtime_target() -> None:
    entrypoint = (BACKEND_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    migration = (
        BACKEND_ROOT / "alembic/versions/20260910_goals_runtime_contract.py"
    ).read_text(encoding="utf-8")

    assert 'RUNTIME_MIGRATION_TARGET="20261005_real_data_cert"' in entrypoint
    assert 'down_revision: str = "20260820_dividend_occurrence"' in migration
    assert "ADD COLUMN IF NOT EXISTS current_value" in migration
    assert "ADD COLUMN IF NOT EXISTS base_value" in migration
    assert "ADD COLUMN IF NOT EXISTS monthly_contribution" in migration
    assert "ALTER COLUMN goal_type TYPE VARCHAR" in migration


def test_real_data_certification_migration_is_runtime_target() -> None:
    entrypoint = (BACKEND_ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    migration = (
        BACKEND_ROOT / "alembic/versions/20261005_real_data_certification.py"
    ).read_text(encoding="utf-8")

    assert 'RUNTIME_MIGRATION_TARGET="20261005_real_data_cert"' in entrypoint
    assert 'revision: str = "20261005_real_data_cert"' in migration
    assert 'down_revision: str = "20260922_corp_ev_ledger_basis"' in migration
    assert 'op.create_table(\n        "real_data_certification_events"' in migration
