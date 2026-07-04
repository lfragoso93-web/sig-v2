"""
fix_dividend_value_per_share

Revision ID: 030
Revises: 029
Create Date: 2026-07-03

Algumas bases locais possuem a coluna legada `dividends.value_per_share` como
NOT NULL. O materializador atual usa `value_per_unit`, mas precisa manter o
campo legado sincronizado até a limpeza definitiva do schema antigo.
"""
from alembic import op

revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS value_per_share NUMERIC(20, 8)
        """)
        op.execute("""
        UPDATE dividends
        SET value_per_share = COALESCE(value_per_share, value_per_unit, 0)
        WHERE value_per_share IS NULL
        """)
        op.execute("""
        ALTER TABLE dividends
        ALTER COLUMN value_per_share SET DEFAULT 0
        """)
    else:
        pass


def downgrade() -> None:
    pass
