"""Gates para alinhamentos MetaData-only de tipos físicos já canônicos."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "app" / "models"


def test_asset_created_at_matches_timestamptz_schema() -> None:
    source = (MODELS / "asset.py").read_text(encoding="utf-8")
    assert "created_at = Column(DateTime(timezone=True), default=utc_now_naive)" in source


def test_asset_dividend_enum_keeps_varchar_storage() -> None:
    source = (MODELS / "asset_dividend.py").read_text(encoding="utf-8")
    assert "native_enum=False" in source
    assert "create_constraint=False" in source
    assert "length=20" in source
    assert "_DIVIDEND_TYPE_STORAGE" in source
    assert "SAEnum(DividendType" not in source.split("dividend_type:", 1)[1]
