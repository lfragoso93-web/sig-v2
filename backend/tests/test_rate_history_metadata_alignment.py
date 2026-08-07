from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "app" / "models" / "rate_history.py"
MIGRATION = ROOT / "alembic" / "versions" / "014_add_rate_history.py"


def test_rate_history_uses_canonical_unique_index_representation() -> None:
    source = MODEL.read_text(encoding="utf-8")
    migration = MIGRATION.read_text(encoding="utf-8")

    assert 'Index("uq_rate_history_indicator_date", "indicator", "date", unique=True)' in source
    assert 'UniqueConstraint("indicator", "date", name="uq_rate_history_indicator_date")' not in source
    assert "op.create_index(" in migration
    assert "'uq_rate_history_indicator_date'" in migration
    assert "unique=True" in migration


def test_rate_history_comments_match_canonical_migration() -> None:
    source = MODEL.read_text(encoding="utf-8")

    assert 'comment="Indicador: CDI | IPCA | SELIC"' in source
    assert 'comment="Fonte: BCB | BRAPI | SEED | MANUAL"' in source
