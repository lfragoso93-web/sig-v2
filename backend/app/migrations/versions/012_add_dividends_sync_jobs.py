"""add dividends_sync_jobs table

Revision ID: 012
Down revision: 011
Create Date: 2026-06-30

Cria a tabela dividends_sync_jobs para controle de estado, cursores
e lock do job de bootstrap/sync de dividendos FIIs via BRAPI.

A tabela permite:
- Evitar execucao concorrente via locked_by + locked_at
- Rastrear progresso incremental com last_cursor_date
- Auditar historico de runs com started_at / finished_at / last_success_at
- Registrar metricas e erros por run

Um registro por job_name. Lock expira apos 60min por default para
prevenir lock eterno em caso de crash da instancia.
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'dividends_sync_jobs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('job_name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='idle'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_cursor_date', sa.Date(), nullable=True),
        sa.Column('last_run_assets_processed', sa.Integer(), nullable=True),
        sa.Column('last_run_events_created', sa.Integer(), nullable=True),
        sa.Column('last_run_events_updated', sa.Integer(), nullable=True),
        sa.Column('last_run_errors', sa.Integer(), nullable=True),
        sa.Column('locked_by', sa.String(255), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
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
            nullable=False,
        ),
        sa.UniqueConstraint('job_name', name='uq_dividends_sync_jobs_job_name'),
    )
    op.create_index(
        'ix_dividends_sync_jobs_job_name',
        'dividends_sync_jobs',
        ['job_name'],
        unique=True,
    )


def downgrade():
    op.drop_index('ix_dividends_sync_jobs_job_name', table_name='dividends_sync_jobs')
    op.drop_table('dividends_sync_jobs')
