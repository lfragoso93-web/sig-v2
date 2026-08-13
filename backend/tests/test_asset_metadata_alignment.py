"""Gates para o contrato físico de assets refletido no MetaData."""

from app.models.asset import Asset


def _indexes() -> dict[str, object]:
    return {index.name: index for index in Asset.__table__.indexes}


def test_asset_metadata_preserves_migrated_columns_and_indexes() -> None:
    columns = Asset.__table__.c
    indexes = _indexes()

    assert "updated_at" in columns
    assert "isin_code" in columns
    assert "ix_assets_isin_code" in indexes
    assert "ix_assets_last_price_updated_at" in indexes
    assert "ix_assets_provider_status" in indexes


def test_asset_metadata_preserves_canonical_unique_constraint_name() -> None:
    constraints = {
        constraint.name: constraint
        for constraint in Asset.__table__.constraints
        if constraint.name
    }
    constraint = constraints["uq_asset_ticker_type"]

    assert [column.name for column in constraint.columns] == ["ticker", "asset_type"]


def test_asset_cache_and_currency_metadata_match_migrations() -> None:
    columns = Asset.__table__.c

    assert columns.currency.nullable is False
    assert columns.last_price.comment == (
        "Ultimo preco conhecido (cache L1). Nunca usar como fallback de PM."
    )
    assert columns.last_price_updated_at.comment == (
        "Timestamp da ultima atualizacao de last_price."
    )
