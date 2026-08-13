"""Gates para índices históricos de transactions refletidos no MetaData."""

from app.models.transaction import Transaction


def _indexes() -> dict[str, object]:
    return {index.name: index for index in Transaction.__table__.indexes}


def test_transaction_metadata_preserves_all_migrated_query_indexes() -> None:
    indexes = _indexes()

    for name in (
        "ix_transactions_portfolio_id",
        "idx_txn_portfolio_date",
        "idx_txn_portfolio_date_asc",
        "idx_txn_portfolio_operation",
        "idx_txn_ticker_date",
        "idx_txn_asset_type",
    ):
        assert name in indexes


def test_transaction_desc_indexes_preserve_direction() -> None:
    indexes = _indexes()

    for name in ("idx_txn_portfolio_date", "idx_txn_ticker_date"):
        expression = list(indexes[name].expressions)[-1]
        assert "date" in str(expression)
        assert "DESC" in str(expression).upper()
