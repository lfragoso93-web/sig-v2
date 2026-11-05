"""clean synthetic certification assets and test user from production db

Revision ID: 20261105_clean_cert_entities
Revises: 20261105_deprecate_fractions
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_clean_cert_entities"
down_revision: str | None = "20261105_deprecate_fractions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Obter IDs dos ativos sintéticos de certificação (ex: CERT303-*)
    cert_assets_query = sa.text("""
        SELECT id, ticker FROM assets 
        WHERE ticker LIKE 'CERT303%'
    """)
    rows = bind.execute(cert_assets_query).fetchall()
    if rows:
        cert_ids = [row[0] for row in rows]

        # Verificar se algum ativo possui dependências críticas em carteiras reais
        active_ids_query = sa.text("""
            SELECT DISTINCT asset_id FROM portfolio_positions WHERE asset_id = ANY(:ids)
            UNION
            SELECT DISTINCT a.id FROM assets a JOIN transactions t ON t.ticker = a.ticker WHERE a.id = ANY(:ids)
        """)
        active_ids = {r[0] for r in bind.execute(active_ids_query, {"ids": cert_ids}).fetchall()}
        safe_to_prune = [aid for aid in cert_ids if aid not in active_ids]

        if safe_to_prune:
            # Remover registros dependentes em tabelas de dados auxiliares
            bind.execute(
                sa.text("DELETE FROM asset_prices WHERE asset_id = ANY(:ids)"),
                {"ids": safe_to_prune},
            )
            bind.execute(
                sa.text("DELETE FROM asset_universe_memberships WHERE asset_id = ANY(:ids)"),
                {"ids": safe_to_prune},
            )
            bind.execute(
                sa.text("DELETE FROM asset_dividends WHERE asset_id = ANY(:ids)"),
                {"ids": safe_to_prune},
            )
            # Remover da tabela assets
            bind.execute(
                sa.text("DELETE FROM assets WHERE id = ANY(:ids)"),
                {"ids": safe_to_prune},
            )

    # 2. Remover usuário de teste (teste@gmail.com) caso não possua carteiras ou logs vinculados
    test_user_query = sa.text("""
        SELECT id FROM users WHERE email = 'teste@gmail.com'
    """)
    user_rows = bind.execute(test_user_query).fetchall()
    if user_rows:
        test_uid = user_rows[0][0]
        # Verificar dependências
        user_portfolios = bind.execute(
            sa.text("SELECT count(*) FROM portfolios WHERE user_id = :uid"),
            {"uid": test_uid},
        ).scalar() or 0

        if user_portfolios == 0:
            bind.execute(
                sa.text("DELETE FROM users WHERE id = :uid"),
                {"uid": test_uid},
            )


def downgrade() -> None:
    # A limpeza de artefatos de teste e certificação é permanente e idempotente.
    pass
