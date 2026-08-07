from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_portfolio_position_indexes_match_migrated_schema() -> None:
    source = (ROOT / "app/models/portfolio_position.py").read_text(encoding="utf-8")

    assert 'Index("idx_pp_portfolio", "portfolio_id")' in source
    assert 'ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False\n    )' in source
    assert 'ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True' not in source


def test_portfolio_class_target_preserves_performance_index() -> None:
    source = (ROOT / "app/models/portfolio_class_target.py").read_text(encoding="utf-8")

    assert "Index('idx_pct_portfolio', 'portfolio_id')" in source


def test_performance_migration_remains_source_of_index_names() -> None:
    source = (ROOT / "alembic/versions/0020_add_performance_indexes.py").read_text(
        encoding="utf-8"
    )

    assert "CREATE INDEX IF NOT EXISTS idx_pp_portfolio" in source
    assert "CREATE INDEX IF NOT EXISTS idx_pct_portfolio" in source
