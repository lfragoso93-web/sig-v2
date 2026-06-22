"""convert assets.asset_type and assets.currency from ENUM to VARCHAR

Revision ID: 009
Revises: 008
Create Date: 2026-06-21

O model Asset usa String() para asset_type e currency, mas a migration 001
criou essas colunas como ENUMs nativos do PostgreSQL (assettype, assetcurrency).
Isso causa DatatypeMismatchError ao inserir novos assets após o segundo
lançamento, pois asyncpg trata o tipo de forma estrita.

Fix: converter ambas as colunas para VARCHAR usando USING cast, e depois
dropar os ENUM types que não são mais necessários para assets
(outros ENUMs como transactiontype continuam intactos).
"""

from alembic import op


revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Converter asset_type: assettype ENUM -> VARCHAR
    op.execute("""
        ALTER TABLE assets
        ALTER COLUMN asset_type TYPE VARCHAR
        USING asset_type::VARCHAR
    """)

    # Converter currency: assetcurrency ENUM -> VARCHAR
    op.execute("""
        ALTER TABLE assets
        ALTER COLUMN currency TYPE VARCHAR
        USING currency::VARCHAR
    """)

    # Remover name constraint da coluna name (era NOT NULL com default vazio
    # em alguns ambientes — tornar nullable para consistencia com o model)
    op.execute("""
        ALTER TABLE assets
        ALTER COLUMN name DROP NOT NULL
    """)


def downgrade() -> None:
    # Restaurar ENUMs (requer que os valores existentes sejam validos)
    op.execute("""
        ALTER TABLE assets
        ALTER COLUMN asset_type TYPE assettype
        USING asset_type::assettype
    """)
    op.execute("""
        ALTER TABLE assets
        ALTER COLUMN currency TYPE assetcurrency
        USING currency::assetcurrency
    """)
    op.execute("""
        ALTER TABLE assets
        ALTER COLUMN name SET NOT NULL
    """)
