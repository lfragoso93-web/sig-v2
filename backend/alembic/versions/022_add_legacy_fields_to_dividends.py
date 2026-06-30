"""
022_add_legacy_fields_to_dividends

Adds legacy dividend columns that exist in the ORM model (dividend.py)
but were never created via migration:
  - payment_date   (Date, nullable)
  - ex_date        (Date, nullable)
  - value_per_unit (Numeric 20,8, nullable)
  - total_received (Numeric 20,8, nullable)
  - dividend_type  (String, nullable)

Without these columns the query in _proventos_total that filters
by `payment_date >= since` raised:
  UndefinedColumnError: column dividends.payment_date does not exist

Revision ID: 022
Revises: 021_sprint5b_composite_indexes
Create Date: 2026-06-30
"""

from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use ADD COLUMN IF NOT EXISTS so the migration is idempotent — safe to run
    # even on databases that already have these columns from a manual ALTER.
    with op.get_context().autocommit_block():
        pass  # autocommit not needed for DDL in PostgreSQL transactional mode

    op.execute(
        "ALTER TABLE dividends ADD COLUMN IF NOT EXISTS payment_date DATE"
    )
    op.execute(
        "ALTER TABLE dividends ADD COLUMN IF NOT EXISTS ex_date DATE"
    )
    op.execute(
        "ALTER TABLE dividends ADD COLUMN IF NOT EXISTS value_per_unit NUMERIC(20, 8)"
    )
    op.execute(
        "ALTER TABLE dividends ADD COLUMN IF NOT EXISTS total_received NUMERIC(20, 8)"
    )
    op.execute(
        "ALTER TABLE dividends ADD COLUMN IF NOT EXISTS dividend_type VARCHAR"
    )

    # Index on payment_date for the _proventos_total `since` filter
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_div_portfolio_payment_date
        ON dividends (portfolio_id, payment_date)
        WHERE payment_date IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS idx_div_portfolio_payment_date"
    )
    op.execute("ALTER TABLE dividends DROP COLUMN IF EXISTS dividend_type")
    op.execute("ALTER TABLE dividends DROP COLUMN IF EXISTS total_received")
    op.execute("ALTER TABLE dividends DROP COLUMN IF EXISTS value_per_unit")
    op.execute("ALTER TABLE dividends DROP COLUMN IF EXISTS ex_date")
    op.execute("ALTER TABLE dividends DROP COLUMN IF EXISTS payment_date")
