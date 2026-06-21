"""add portfolio_class_targets table and assets.sub_sector/float_description columns

Revision ID: 008
Revises: 007
Create Date: 2026-06-21

Corrige erros críticos que causavam HTTP 500:
  1. Tabela portfolio_class_targets não existia no banco.
  2. Coluna assets.sub_sector não existia no banco.
  3. Coluna assets.float_description não existia no banco.

Usa Inspector para ser idempotente (IF NOT EXISTS).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Criar tabela portfolio_class_targets ────────────────────────────
    if not _table_exists(conn, 'portfolio_class_targets'):
        op.create_table(
            'portfolio_class_targets',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column(
                'portfolio_id',
                sa.Integer(),
                sa.ForeignKey('portfolios.id', ondelete='CASCADE'),
                nullable=False,
                index=True,
            ),
            sa.Column('asset_type', sa.String(50), nullable=False),
            sa.Column('target_pct', sa.Numeric(5, 2), nullable=False, server_default='0'),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                'updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint('portfolio_id', 'asset_type', name='uq_portfolio_class_target'),
        )

    # ── 2. assets.sub_sector ──────────────────────────────────────────────
    if not _column_exists(conn, 'assets', 'sub_sector'):
        op.add_column('assets', sa.Column('sub_sector', sa.String(), nullable=True))

    # ── 3. assets.float_description ──────────────────────────────────────
    if not _column_exists(conn, 'assets', 'float_description'):
        op.add_column('assets', sa.Column('float_description', sa.Float(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, 'assets', 'float_description'):
        op.drop_column('assets', 'float_description')

    if _column_exists(conn, 'assets', 'sub_sector'):
        op.drop_column('assets', 'sub_sector')

    if _table_exists(conn, 'portfolio_class_targets'):
        op.drop_table('portfolio_class_targets')
