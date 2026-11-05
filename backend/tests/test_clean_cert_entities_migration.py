from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_clean_cert_entities_migration_contract() -> None:
    migration_path = BACKEND_ROOT / "alembic/versions/20261105_clean_cert_entities.py"
    assert migration_path.exists(), "Migration 20261105_clean_cert_entities must exist"

    source = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "20261105_clean_cert_entities"' in source
    assert 'down_revision: str | None = "20261105_deprecate_fractions"' in source

    # Verifica que preserva integridade de dados e auditoria
    assert "real_data_certification_events" not in source, "Nunca deve tocar a tabela de auditoria real_data_certification_events"
    assert "DELETE FROM assets WHERE id = ANY(:ids)" in source
    assert "DELETE FROM users WHERE id = :uid" in source
    assert "SELECT count(*) FROM portfolios WHERE user_id = :uid" in source
    assert "ticker LIKE 'CERT303%'" in source
    assert "teste@gmail.com" in source


def test_purge_synthetic_cert_entities_migration_contract() -> None:
    migration_path = BACKEND_ROOT / "alembic/versions/20261105_purge_synthetic_cert_entities.py"
    assert migration_path.exists(), "Migration 20261105_purge_synthetic_cert_entities must exist"

    source = migration_path.read_text(encoding="utf-8")

    assert 'revision: str = "20261105_purge_synthetic_cert_entities"' in source
    assert 'down_revision: str | None = "20261105_clean_cert_entities"' in source

    # Verifica preservação absoluta da tabela de auditoria de certificação de dados reais
    assert "real_data_certification_events" not in source, "Nunca deve tocar a tabela de auditoria real_data_certification_events"

    # Verifica que remove as entidades sintéticas por cascade seguro
    assert "portfolio-certification-303@example.com" in source
    assert "PORTFOLIO-TEST-READY synthetic multiclasse" in source
    assert "sgi:certification:issue-303:v1" in source
    assert "ticker LIKE 'CERT303%'" in source
    assert "DELETE FROM portfolio_positions" in source
    assert "DELETE FROM transactions" in source
    assert "DELETE FROM portfolios" in source
    assert "DELETE FROM users" in source
    assert "DELETE FROM assets WHERE id = ANY(:aids)" in source
    assert "DELETE FROM rate_history WHERE source = 'synthetic-certification'" in source
