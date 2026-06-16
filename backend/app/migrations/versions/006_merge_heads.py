"""merge dos dois branches de migration

Revision ID: 006
Down revision: ('004', '005_portfolio_snapshots')
Create Date: 2026-06-16

Este merge une o branch 004 (fx_fields) e o branch
005_portfolio_snapshots em um unico head linear.
Todas as tabelas ja foram criadas em 001_initial_schema,
portanto este arquivo nao executa DDL adicional.
"""
from alembic import op


revision = '006'
down_revision = ('004', '005_portfolio_snapshots')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
