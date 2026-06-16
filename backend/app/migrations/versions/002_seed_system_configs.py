"""seed system_configs com valores padrao

Revision ID: 002
Down revision: 001
Create Date: 2026-06-16
"""
from alembic import op
from sqlalchemy.sql import table, column
from sqlalchemy import String, Text, Boolean


def upgrade():
    system_configs = table(
        'system_configs',
        column('key', String),
        column('value', Text),
        column('description', Text),
        column('is_public', Boolean),
    )
    op.bulk_insert(system_configs, [
        {'key': 'app_name', 'value': 'SGI', 'description': 'Nome do sistema', 'is_public': True},
        {'key': 'app_tagline', 'value': 'Sistema de Gestao de Investimentos', 'description': 'Subtitulo do sistema', 'is_public': True},
        {'key': 'allow_registration', 'value': 'true', 'description': 'Permite auto-registro de novos usuarios', 'is_public': True},
        {'key': 'max_portfolios_per_user', 'value': '10', 'description': 'Limite de carteiras por usuario', 'is_public': False},
        {'key': 'brapi_rate_limit', 'value': '300', 'description': 'Requisicoes por hora na BRAPI', 'is_public': False},
        {'key': 'ai_analysis_enabled', 'value': 'true', 'description': 'Habilita analise com IA (Gemini)', 'is_public': False},
        {'key': 'maintenance_mode', 'value': 'false', 'description': 'Modo manutencao - bloqueia acesso de usuarios', 'is_public': True},
    ])


def downgrade():
    op.execute("DELETE FROM system_configs WHERE key IN ('app_name','app_tagline','allow_registration','max_portfolios_per_user','brapi_rate_limit','ai_analysis_enabled','maintenance_mode')")
