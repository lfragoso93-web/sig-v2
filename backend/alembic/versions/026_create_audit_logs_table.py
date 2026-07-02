"""
create_audit_logs_table

Revision ID: 026
Revises: 025
Create Date: 2026-07-02

Cria tabela audit_logs para rastreamento de operações de usuários.
Cobre CREATE, READ, UPDATE, DELETE, EXPORT, IMPORT, LOGIN, LOGOUT, BACKUP, RESTORE.
Armazena mudanças em JSON e contexto de requisição (IP, User-Agent).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '026'
down_revision = '025'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('portfolio_id', sa.Integer(), nullable=True),
        sa.Column('old_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('changes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='SUCCESS'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_audit_user_date', 'audit_logs', ['user_id', sa.desc('created_at')], unique=False)
    op.create_index('idx_audit_resource_date', 'audit_logs', ['resource_type', sa.desc('created_at')], unique=False)
    op.create_index('idx_audit_action_date', 'audit_logs', ['action', sa.desc('created_at')], unique=False)
    op.create_index('idx_audit_portfolio_date', 'audit_logs', ['portfolio_id', sa.desc('created_at')], unique=False)
    op.create_index('idx_audit_status', 'audit_logs', ['status'], unique=False)
    op.create_index('idx_audit_created_at', 'audit_logs', [sa.desc('created_at')], unique=False)


def downgrade() -> None:
    op.drop_index('idx_audit_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_status', table_name='audit_logs')
    op.drop_index('idx_audit_portfolio_date', table_name='audit_logs')
    op.drop_index('idx_audit_action_date', table_name='audit_logs')
    op.drop_index('idx_audit_resource_date', table_name='audit_logs')
    op.drop_index('idx_audit_user_date', table_name='audit_logs')
    op.drop_table('audit_logs')
