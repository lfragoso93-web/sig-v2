"""010 - add goal_type, monthly_contribution, base_value to goals

Revision ID: 010
Revises: 009
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # goal_type: PATRIMONIO | PROVENTOS | RENTABILIDADE | LIVRE
    op.add_column('goals', sa.Column(
        'goal_type', sa.String(), nullable=False, server_default='LIVRE'
    ))
    # aporte mensal projetado pelo usuário
    op.add_column('goals', sa.Column(
        'monthly_contribution', sa.Float(), nullable=True
    ))
    # snapshot do valor no momento da criação
    op.add_column('goals', sa.Column(
        'base_value', sa.Float(), nullable=False, server_default='0'
    ))


def downgrade() -> None:
    op.drop_column('goals', 'goal_type')
    op.drop_column('goals', 'monthly_contribution')
    op.drop_column('goals', 'base_value')
