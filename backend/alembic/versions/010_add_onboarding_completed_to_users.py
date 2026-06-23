"""add onboarding_completed to users

Revision ID: 010
Revises: 009
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'onboarding_completed',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'onboarding_completed')
