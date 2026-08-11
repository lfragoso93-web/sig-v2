from pathlib import Path

from app.models.asset_universe_membership import AssetUniverseMembership
from app.services.asset_universe_membership_service import (
    CRYPTO_TOP100_UNIVERSE_KEY,
    CRYPTO_TOP100_UNIVERSE_SOURCE,
)
from app.services.crypto_financial_certification_service import (
    FINANCIALLY_CERTIFIED_CRYPTO_STATUSES,
)

ROOT = Path(__file__).resolve().parents[1]


def test_asset_universe_membership_metadata_contract() -> None:
    table = AssetUniverseMembership.__table__

    assert table.name == "asset_universe_memberships"
    assert {column.name for column in table.columns} == {
        "id",
        "asset_id",
        "universe_key",
        "rank",
        "source",
        "refreshed_at",
    }
    assert CRYPTO_TOP100_UNIVERSE_KEY == "crypto_top100_market_cap"
    assert CRYPTO_TOP100_UNIVERSE_SOURCE == "coingecko_market_cap_intersect_brapi"
    assert table.c.source.type.length == 64
    assert len(CRYPTO_TOP100_UNIVERSE_SOURCE) <= table.c.source.type.length


def test_seed_persists_candidate_universe_snapshot() -> None:
    source = (ROOT / "app" / "services" / "asset_seed_service.py").read_text(
        encoding="utf-8"
    )

    assert "replace_crypto_candidate_memberships" in source
    assert "await db.commit()" in source


def test_catalog_is_fail_closed_for_crypto() -> None:
    source = (
        ROOT / "app" / "services" / "asset_catalog_query_service.py"
    ).read_text(encoding="utf-8")

    assert "CRYPTO_TOP100_UNIVERSE_KEY" in source
    assert "FINANCIALLY_CERTIFIED_CRYPTO_STATUSES" in source
    assert "candidate_membership" in source
    assert FINANCIALLY_CERTIFIED_CRYPTO_STATUSES == {
        "HISTORY_START_EXHAUSTED",
        "HISTORY_START_SHALLOW_VERIFIED",
    }
