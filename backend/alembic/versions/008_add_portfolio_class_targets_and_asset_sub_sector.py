"""add portfolio_class_targets table and assets.sub_sector column

Revision ID: 008
Revises: 007
Create Date: 2026-06-21

Corrige dois erros críticos que causavam HTTP 500 em GET /portfolios/{id}/positions:
  1. Tabela portfolio_class_targets não existia no banco.
  2. Coluna assets.sub_sector não existia no banco.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Criar tabela portfolio_class_targets ──────────────────────────────
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint('portfolio_id', 'asset_type', name='uq_portfolio_class_target'),
    )

    # ── 2. Adicionar coluna sub_sector na tabela assets ──────────────────────
    op.add_column(
        'assets',
        sa.Column('sub_sector', sa.String(), nullable=True),
    )


def downgrade() -> None:
    # Reverter na ordem inversa
    op.drop_column('assets', 'sub_sector')
    op.drop_table('portfolio_class_targets')
