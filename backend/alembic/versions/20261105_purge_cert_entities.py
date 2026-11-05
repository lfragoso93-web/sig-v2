"""purge synthetic certification portfolios, transactions, assets and test users from production db

Revision ID: 20261105_purge_cert_entities
Revises: 20261105_clean_cert_entities
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_purge_cert_entities"
down_revision: str | None = "20261105_clean_cert_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Localizar usuários sintéticos / de teste
    users_query = sa.text("""
        SELECT id FROM users
        WHERE email IN ('portfolio-certification-303@example.com', 'teste@gmail.com')
    """)
    user_ids = [row[0] for row in bind.execute(users_query).fetchall()]

    # 2. Localizar carteiras sintéticas de certificação (por marcador, nome ou pertencentes aos usuários de teste)
    portfolios_query = sa.text("""
        SELECT id FROM portfolios
        WHERE description = 'sgi:certification:issue-303:v1'
           OR name = 'PORTFOLIO-TEST-READY synthetic multiclasse'
           OR (user_id = ANY(:uids) AND :has_uids)
    """)
    portfolio_rows = bind.execute(
        portfolios_query,
        {"uids": user_ids or [-1], "has_uids": bool(user_ids)},
    ).fetchall()
    portfolio_ids = [row[0] for row in portfolio_rows]

    # 3. Localizar ativos sintéticos CERT303%
    cert_assets_query = sa.text("SELECT id FROM assets WHERE ticker LIKE 'CERT303%'")
    cert_asset_ids = [row[0] for row in bind.execute(cert_assets_query).fetchall()]

    # 4. Remover dados dependentes vinculados às carteiras sintéticas
    if portfolio_ids:
        # Snapshots
        bind.execute(
            sa.text("DELETE FROM portfolio_class_snapshots WHERE portfolio_id = ANY(:pids)"),
            {"pids": portfolio_ids},
        )
        bind.execute(
            sa.text("DELETE FROM portfolio_snapshots WHERE portfolio_id = ANY(:pids)"),
            {"pids": portfolio_ids},
        )
        # Metas e alvos
        bind.execute(
            sa.text("DELETE FROM goals WHERE portfolio_id = ANY(:pids)"),
            {"pids": portfolio_ids},
        )
        bind.execute(
            sa.text("DELETE FROM portfolio_class_targets WHERE portfolio_id = ANY(:pids)"),
            {"pids": portfolio_ids},
        )
        # Contratos de renda fixa
        bind.execute(
            sa.text("DELETE FROM fixed_income_contracts WHERE portfolio_id = ANY(:pids)"),
            {"pids": portfolio_ids},
        )

    # 5. Excluir eventos corporativos sintéticos (vinculados às carteiras de teste ou ativos CERT303%)
    # Remove dependências em cascata para não vazar ações corporativas de teste para escopo global
    ev_query = sa.text("""
        SELECT id FROM corporate_events
        WHERE (portfolio_id = ANY(:pids) AND :has_pids)
           OR (asset_id = ANY(:aids) AND :has_aids)
           OR (destination_asset_id = ANY(:aids) AND :has_aids)
           OR ticker LIKE 'CERT303%'
    """)
    ev_rows = bind.execute(
        ev_query,
        {
            "pids": portfolio_ids or [-1],
            "has_pids": bool(portfolio_ids),
            "aids": cert_asset_ids or [-1],
            "has_aids": bool(cert_asset_ids),
        },
    ).fetchall()
    ev_ids = [row[0] for row in ev_rows]

    if ev_ids:
        bind.execute(
            sa.text("UPDATE corporate_events SET matched_event_id = NULL WHERE matched_event_id = ANY(:eids)"),
            {"eids": ev_ids},
        )
        bind.execute(
            sa.text("DELETE FROM corporate_event_reconciliation_evidence WHERE corporate_event_id = ANY(:eids)"),
            {"eids": ev_ids},
        )
        bind.execute(
            sa.text("DELETE FROM corporate_event_destination_legs WHERE corporate_event_id = ANY(:eids)"),
            {"eids": ev_ids},
        )
        bind.execute(
            sa.text("DELETE FROM corporate_events WHERE id = ANY(:eids)"),
            {"eids": ev_ids},
        )

    if cert_asset_ids:
        bind.execute(
            sa.text("DELETE FROM corporate_event_destination_legs WHERE destination_asset_id = ANY(:aids)"),
            {"aids": cert_asset_ids},
        )

    # 6. Remover posições e transações sintéticas (das carteiras de teste OU associadas a ativos CERT303%)
    bind.execute(sa.text("""
        DELETE FROM portfolio_positions
        WHERE (portfolio_id = ANY(:pids) AND :has_pids)
           OR (asset_id = ANY(:aids) AND :has_aids)
    """), {
        "pids": portfolio_ids or [-1],
        "has_pids": bool(portfolio_ids),
        "aids": cert_asset_ids or [-1],
        "has_aids": bool(cert_asset_ids),
    })

    bind.execute(sa.text("""
        DELETE FROM transactions
        WHERE (portfolio_id = ANY(:pids) AND :has_pids)
           OR ticker LIKE 'CERT303%'
    """), {
        "pids": portfolio_ids or [-1],
        "has_pids": bool(portfolio_ids),
    })

    # 7. Remover carteiras sintéticas
    if portfolio_ids:
        bind.execute(
            sa.text("DELETE FROM portfolios WHERE id = ANY(:pids)"),
            {"pids": portfolio_ids},
        )

    # 8. Remover usuários sintéticos / de teste que não possuam mais carteiras
    if user_ids:
        bind.execute(sa.text("""
            DELETE FROM users
            WHERE id = ANY(:uids)
              AND id NOT IN (SELECT DISTINCT user_id FROM portfolios)
        """), {"uids": user_ids})

    # 9. Agora que nenhuma posição, transação ou evento referencia ativos CERT303%, removê-los com segurança
    if cert_asset_ids:
        bind.execute(
            sa.text("DELETE FROM asset_prices WHERE asset_id = ANY(:aids)"),
            {"aids": cert_asset_ids},
        )
        bind.execute(
            sa.text("DELETE FROM asset_universe_memberships WHERE asset_id = ANY(:aids)"),
            {"aids": cert_asset_ids},
        )
        bind.execute(
            sa.text("DELETE FROM asset_dividends WHERE asset_id = ANY(:aids)"),
            {"aids": cert_asset_ids},
        )
        bind.execute(
            sa.text("DELETE FROM asset_aliases WHERE asset_id = ANY(:aids)"),
            {"aids": cert_asset_ids},
        )
        bind.execute(
            sa.text("DELETE FROM treasury_instruments WHERE asset_id = ANY(:aids)"),
            {"aids": cert_asset_ids},
        )
        bind.execute(
            sa.text("DELETE FROM assets WHERE id = ANY(:aids)"),
            {"aids": cert_asset_ids},
        )

    # 10. Remover taxas de benchmark sintéticas de certificação (source = 'synthetic-certification')
    bind.execute(sa.text("DELETE FROM rate_history_coverages WHERE source = 'synthetic-certification'"))
    bind.execute(sa.text("DELETE FROM rate_history WHERE source = 'synthetic-certification'"))


def downgrade() -> None:
    # A limpeza de artefatos de teste e certificação é permanente e idempotente.
    pass
