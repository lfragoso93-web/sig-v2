"""add google oauth and mfa totp columns to users

Revision ID: 20261022_auth_oauth_mfa
Revises: 20261021_provider_configs
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261022_auth_oauth_mfa"
down_revision: str | None = "20261021_provider_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "users"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "auth_provider",
            sa.String(length=30),
            server_default="local",
            nullable=False,
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column("google_sub", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_users_google_sub", _TABLE, ["google_sub"], unique=True
    )
    op.add_column(
        _TABLE,
        sa.Column("totp_secret", sa.String(length=255), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column("totp_backup_codes", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "totp_backup_codes")
    op.drop_column(_TABLE, "totp_enabled")
    op.drop_column(_TABLE, "totp_secret")
    op.drop_index("ix_users_google_sub", table_name=_TABLE)
    op.drop_column(_TABLE, "google_sub")
    op.drop_column(_TABLE, "auth_provider")
