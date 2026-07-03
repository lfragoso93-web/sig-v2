"""
fix_dividend_quantity_on_date

Revision ID: 029
Revises: 028
Create Date: 2026-07-03

Algumas bases locais possuem a coluna legada `dividends.quantity_on_date` como
NOT NULL. O materializador atual usa `quantity`, mas precisa manter o campo
legado sincronizado até a limpeza definitiva do schema antigo.
"""
from alembic import op

revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS quantity_on_date NUMERIC(20, 8)
        """)
        op.execute("""
        UPDATE dividends
        SET quantity_on_date = COALESCE(quantity_on_date, quantity, 0)
        WHERE quantity_on_date IS NULL
        """)
        op.execute("""
        ALTER TABLE dividends
        ALTER COLUMN quantity_on_date SET DEFAULT 0
        """)
    else:
        pass


def downgrade() -> None:
    pass
