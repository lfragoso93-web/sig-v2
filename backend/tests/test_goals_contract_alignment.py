from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "app" / "models" / "goal.py"
MIGRATION = ROOT / "alembic" / "versions" / "20260807_goals_contract.py"
SCHEMA = ROOT / "app" / "schemas" / "goal.py"


def test_goals_migration_is_defensive_and_reversible() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "20260807_goals_contract"' in source
    assert 'down_revision: str = "20260807_pos_snap_ts_nn"' in source
    assert len("20260807_goals_contract") <= 32
    assert "SELECT COUNT(*) FROM goals" in source
    assert "raise RuntimeError" in source
    assert "current_value" in source
    assert "base_value" in source
    assert "monthly_contribution" in source
    assert "sa.Numeric(18, 2)" in source
    assert "postgresql_using=\"goal_type::text\"" in source
    assert "postgresql_using=\"goal_type::goaltype\"" in source
    assert "UPDATE goals" not in source
    assert "DELETE FROM goals" not in source
    assert "TRUNCATE" not in source


def test_goals_model_matches_active_api_contract_without_losing_physical_fields() -> None:
    model = MODEL.read_text(encoding="utf-8")
    schema = SCHEMA.read_text(encoding="utf-8")

    for value in ("PATRIMONIO", "PROVENTOS", "RENTABILIDADE", "LIVRE"):
        assert value in schema

    assert 'goal_type = Column(String(30)' in model
    assert 'Numeric(18, 2, asdecimal=False)' in model
    assert 'ForeignKey("portfolios.id", ondelete="CASCADE")' in model
    assert 'Index("ix_goals_portfolio_id", "portfolio_id")' in model
    assert "current_value" in model
    assert "base_value" in model
    assert "monthly_contribution" in model
    assert "is_active" in model
    assert "created_at" in model
    assert "updated_at" in model
    assert "DateTime(timezone=True)" in model
    assert "Float" not in model
