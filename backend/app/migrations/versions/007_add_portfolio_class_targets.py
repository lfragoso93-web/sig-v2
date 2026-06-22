"""
007 - Cria tabela portfolio_class_targets para armazenar a meta de alocação
por classe de ativo definida pelo usuário em cada carteira.

Revision ID: 007
Down revision: 006
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'portfolio_class_targets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'portfolio_id',
            sa.Integer(),
            sa.ForeignKey('portfolios.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('target_pct', sa.Numeric(5, 2), nullable=False, default=0),
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


def downgrade():
    op.drop_table('portfolio_class_targets')
