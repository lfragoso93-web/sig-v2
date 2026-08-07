"""Gates para índices já existentes no schema migado e refletidos pelo ORM."""

from app.models.asset_price import AssetPrice
from app.models.audit_log import AuditLog
from app.models.portfolio_snapshot import PortfolioSnapshot


def _index_by_name(model) -> dict[str, object]:
    return {index.name: index for index in model.__table__.indexes}


def test_asset_price_metadata_preserves_existing_desc_composite_index() -> None:
    indexes = _index_by_name(AssetPrice)
    index = indexes["idx_ap_asset_ts"]
    expressions = list(index.expressions)

    assert "asset_id" in str(expressions[0])
    assert "timestamp" in str(expressions[1])
    assert "DESC" in str(expressions[1]).upper()


def test_audit_metadata_uses_existing_composite_indexes_without_extra_fk_indexes() -> None:
    indexes = _index_by_name(AuditLog)

    assert "ix_audit_logs_user_id" not in indexes
    assert "ix_audit_logs_portfolio_id" not in indexes

    for name in (
        "idx_audit_user_date",
        "idx_audit_resource_date",
        "idx_audit_action_date",
        "idx_audit_portfolio_date",
        "idx_audit_created_at",
    ):
        expression = list(indexes[name].expressions)[-1]
        assert "created_at" in str(expression)
        assert "DESC" in str(expression).upper()


def test_snapshot_metadata_preserves_existing_query_indexes() -> None:
    indexes = _index_by_name(PortfolioSnapshot)

    assert {
        "ix_portfolio_snapshots_portfolio_id",
        "ix_portfolio_snapshots_snapshot_date",
        "ix_portfolio_snapshots_portfolio_date",
        "idx_ps_portfolio_date_desc",
    }.issubset(indexes)

    desc_index = indexes["idx_ps_portfolio_date_desc"]
    expressions = list(desc_index.expressions)
    assert "portfolio_id" in str(expressions[0])
    assert "snapshot_date" in str(expressions[1])
    assert "DESC" in str(expressions[1]).upper()
