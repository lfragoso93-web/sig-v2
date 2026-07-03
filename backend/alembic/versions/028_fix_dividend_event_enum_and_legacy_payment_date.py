"""
fix_dividend_event_enum_and_legacy_payment_date

Revision ID: 028
Revises: 027
Create Date: 2026-07-03

Corrige diferenças encontradas em bases locais durante o sync de proventos:

- o enum nativo PostgreSQL `dividendtype` podia não conter todos os valores
  usados pelo parser de eventos BRAPI;
- algumas bases possuíam `date_ex`, mas não `date_pagamento`, embora o código
  de compatibilidade legada passe a manter ambos sincronizados.
"""
from alembic import op
import sqlalchemy as sa

revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None

_EVENT_TYPES = (
    'DIVIDENDO',
    'JCP',
    'RENDIMENTO',
    'AMORTIZACAO',
    'BONIFICACAO',
    'SUBSCRICAO',
    'OUTROS',
)


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == 'postgresql':
        for value in _EVENT_TYPES:
            op.execute(f"ALTER TYPE dividendtype ADD VALUE IF NOT EXISTS '{value}'")

        op.execute("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS date_pagamento DATE
        """)
        op.execute("""
        UPDATE dividends
        SET date_pagamento = COALESCE(date_pagamento, payment_date, date_ex, ex_date)
        WHERE date_pagamento IS NULL
        """)
    else:
        # SQLite/testes não suportam ADD COLUMN IF NOT EXISTS de forma uniforme.
        # Em ambientes não-PostgreSQL, as tabelas costumam ser recriadas nos testes.
        pass


def downgrade() -> None:
    # Não removemos valores de enum PostgreSQL no downgrade porque PostgreSQL não
    # oferece remoção simples/segura de enum value. A coluna legada também é
    # mantida para compatibilidade com bases que dependam dela.
    pass
