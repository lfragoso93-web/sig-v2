"""seed SuperAdmin overrides for B3 calendar source

Revision ID: 20261010_b3_calendar_config
Revises: 20261009_market_calendar
"""
from collections.abc import Sequence

from alembic import op


revision: str = "20261010_b3_calendar_config"
down_revision: str = "20261009_market_calendar"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO system_configs (key, value, description, is_public)
        VALUES
          ('market_calendar.b3_source_url',
           'https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm',
           'Fonte oficial B3 do calendario de mercado para auditoria.', false),
          ('market_calendar.b3_source_year', '2026',
           'Ano da fonte B3 usada pela auditoria de calendario.', false)
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM system_configs WHERE key IN "
        "('market_calendar.b3_source_url', 'market_calendar.b3_source_year')"
    )
