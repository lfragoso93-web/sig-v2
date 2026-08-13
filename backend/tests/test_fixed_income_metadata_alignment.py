from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "app" / "models" / "fixed_income.py"
MIGRATION = ROOT / "alembic" / "versions" / "015_add_daily_liquidity_to_fixed_income.py"
INITIAL = ROOT / "alembic" / "versions" / "001_initial_schema.py"


def test_fixed_income_does_not_request_unmigrated_portfolio_index() -> None:
    source = MODEL.read_text(encoding="utf-8")
    initial = INITIAL.read_text(encoding="utf-8")

    assert 'ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False\n' in source
    assert 'nullable=False, index=True' not in source
    assert "ix_fixed_income_investments_portfolio_id" not in initial


def test_fixed_income_daily_liquidity_comment_matches_migration() -> None:
    source = MODEL.read_text(encoding="utf-8")
    migration = MIGRATION.read_text(encoding="utf-8")
    canonical = "Se TRUE o título pode ser resgatado a qualquer dia (sem vencimento relevante)"

    assert f'comment="{canonical}"' in source
    assert f"comment='{canonical}'" in migration
