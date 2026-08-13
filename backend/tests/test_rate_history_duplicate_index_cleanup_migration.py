"""Gates para limpeza idempotente do índice legado duplicado de rate_history."""

from pathlib import Path


MIGRATION = Path("alembic/versions/20260807_drop_duplicate_rate_history_index.py")


def _source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_rate_history_cleanup_is_chained_after_current_head() -> None:
    source = _source()

    assert 'revision: str = "20260807_drop_dup_rate_idx"' in source
    assert 'down_revision: str = "20260806_drop_irpf_records"' in source


def test_rate_history_cleanup_preserves_canonical_uniqueness_before_drop() -> None:
    source = _source()

    assert "uq_rate_history_indicator_date" in source
    assert "ix_rate_history_indicator_date_unique" in source
    assert "RAISE EXCEPTION" in source
    assert "DROP INDEX IF EXISTS ix_rate_history_indicator_date_unique" in source


def test_rate_history_cleanup_downgrade_restores_only_duplicate_index() -> None:
    source = _source()

    assert (
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_rate_history_indicator_date_unique"
        in source
    )
    assert "ON rate_history (indicator, date)" in source
