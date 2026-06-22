"""
008 - Corrige constraint unique da tabela assets: troca unique(ticker)
por unique(ticker, asset_type), permitindo que o mesmo ticker exista
para tipos de ativo distintos e desbloqueando o cache L1 de cotacoes.

Revision ID: 008
Down revision: 007
"""
from alembic import op

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Remove o indice unico simples de ticker (se existir)
    with op.batch_alter_table('assets') as batch_op:
        try:
            batch_op.drop_index('ix_assets_ticker')
        except Exception:
            pass  # indice pode ter nome diferente dependendo do ambiente

        # Cria indice nao-unico em ticker (para buscas por ticker apenas)
        batch_op.create_index('ix_assets_ticker', ['ticker'], unique=False)

        # Cria unique composto (ticker, asset_type)
        batch_op.create_unique_constraint(
            'uq_assets_ticker_asset_type',
            ['ticker', 'asset_type'],
        )


def downgrade():
    with op.batch_alter_table('assets') as batch_op:
        batch_op.drop_constraint('uq_assets_ticker_asset_type', type_='unique')
        batch_op.drop_index('ix_assets_ticker')
        batch_op.create_index('ix_assets_ticker', ['ticker'], unique=True)
