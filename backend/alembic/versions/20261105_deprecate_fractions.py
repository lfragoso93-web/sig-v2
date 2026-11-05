"""deprecate b3 fractional share assets and prune orphan prices

Revision ID: 20261105_deprecate_fractions
Revises: 20261022_auth_oauth_mfa
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261105_deprecate_fractions"
down_revision: str | None = "20261022_auth_oauth_mfa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Obter IDs dos ativos fracionários da B3 (ex: PETR4F, VALE3F)
    fractional_assets_query = sa.text("""
        SELECT id, ticker FROM assets 
        WHERE ticker ~* '^[A-Z0-9]{4}[0-9]{1,2}[A-Z]?F$'
          AND asset_type IN ('ACAO', 'Ação', 'ETF_NACIONAL', 'FII', 'BDR')
    """)
    rows = bind.execute(fractional_assets_query).fetchall()
    if not rows:
        return

    frac_ids = [row[0] for row in rows]

    # 2. Normalizar tickers de transações legadas que porventura usem a terminação F
    bind.execute(sa.text("""
        UPDATE transactions
        SET ticker = regexp_replace(ticker, 'F$', '')
        WHERE ticker ~* '^[A-Z0-9]{4}[0-9]{1,2}[A-Z]?F$'
          AND asset_type IN ('ACAO', 'Ação', 'ETF_NACIONAL', 'FII', 'BDR')
    """))

    # 3. Verificar se algum ativo possui dependências críticas em carteiras, proventos ou eventos corporativos
    active_ids_query = sa.text("""
        SELECT DISTINCT asset_id FROM portfolio_positions WHERE asset_id = ANY(:ids)
        UNION
        SELECT DISTINCT a.id FROM assets a JOIN transactions t ON t.ticker = a.ticker WHERE a.id = ANY(:ids)
        UNION
        SELECT DISTINCT asset_id FROM asset_dividends WHERE asset_id = ANY(:ids)
        UNION
        SELECT DISTINCT asset_id FROM corporate_events WHERE asset_id = ANY(:ids)
        UNION
        SELECT DISTINCT destination_asset_id FROM corporate_events WHERE destination_asset_id = ANY(:ids)
        UNION
        SELECT DISTINCT destination_asset_id FROM corporate_event_destination_legs WHERE destination_asset_id = ANY(:ids)
    """)
    active_ids = {r[0] for r in bind.execute(active_ids_query, {"ids": frac_ids}).fetchall()}

    # IDs seguros para remoção (sem posições ou transações vinculadas)
    safe_to_prune = [aid for aid in frac_ids if aid not in active_ids]

    if safe_to_prune:
        # 3. Remover preços históricos acumulados desses ativos fracionários
        bind.execute(
            sa.text("DELETE FROM asset_prices WHERE asset_id = ANY(:ids)"),
            {"ids": safe_to_prune},
        )

        # 4. Remover membros de universo caso existam
        bind.execute(
            sa.text("DELETE FROM asset_universe_memberships WHERE asset_id = ANY(:ids)"),
            {"ids": safe_to_prune},
        )

        # 5. Remover os ativos fracionários redundantes da tabela assets
        bind.execute(
            sa.text("DELETE FROM assets WHERE id = ANY(:ids)"),
            {"ids": safe_to_prune},
        )


def downgrade() -> None:
    # A exclusão de frações é irreversível e idempotente; o mercado padrão (010) permanece íntegro.
    pass
