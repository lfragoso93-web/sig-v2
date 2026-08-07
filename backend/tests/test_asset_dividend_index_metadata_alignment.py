"""Gates para índices físicos de asset_dividends refletidos no MetaData."""

from app.models.asset_dividend import AssetDividend


def _indexes() -> dict[str, object]:
    return {index.name: index for index in AssetDividend.__table__.indexes}


def test_asset_dividend_metadata_preserves_desc_history_index() -> None:
    index = _indexes()["idx_ad_asset_exdate_desc"]
    expressions = list(index.expressions)

    assert "asset_id" in str(expressions[0])
    assert "ex_date" in str(expressions[1])
    assert "DESC" in str(expressions[1]).upper()


def test_asset_dividend_metadata_preserves_approved_on_index() -> None:
    index = _indexes()["ix_asset_dividends_approved_on"]
    expressions = list(index.expressions)

    assert len(expressions) == 1
    assert "approved_on" in str(expressions[0])
