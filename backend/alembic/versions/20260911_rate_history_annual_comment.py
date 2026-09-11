"""align rate_history annual-rate comment with ORM metadata

Revision ID: 20260911_rate_annual_comment
Revises: 20260911_merge_runtime
Create Date: 2026-09-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260911_rate_annual_comment"
down_revision: str = "20260911_merge_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANONICAL_COMMENT = "Taxa anual em % a.a. (ex: 10.5000)"
_PREVIOUS_COMMENT = "Taxa anual em % a.a."


def upgrade() -> None:
    """Align only the persisted column comment with the canonical ORM metadata."""
    op.execute(
        "COMMENT ON COLUMN rate_history.rate_annual IS "
        f"'{_CANONICAL_COMMENT}'"
    )


def downgrade() -> None:
    """Restore the previous persisted comment without changing column semantics."""
    op.execute(
        "COMMENT ON COLUMN rate_history.rate_annual IS "
        f"'{_PREVIOUS_COMMENT}'"
    )
