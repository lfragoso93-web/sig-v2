"""Gates para o contrato financeiro persistido de transactions."""

from pathlib import Path

MODEL = Path(__file__).resolve().parents[1] / "app" / "models" / "transaction.py"


def _source() -> str:
    return MODEL.read_text(encoding="utf-8")


def test_transaction_financial_types_match_migrated_schema() -> None:
    source = _source()
    assert 'asset_type = Column(String(30), nullable=False)' in source
    assert 'quantity = Column(Numeric(18, 8), nullable=False)' in source
    assert 'price = Column(Numeric(18, 8), nullable=False)' in source
    assert 'fees = Column(Numeric(18, 2), nullable=False' in source
    assert 'notes = Column(Text, nullable=True)' in source
    assert 'Column(Float' not in source


def test_transaction_audit_timestamps_remain_in_metadata() -> None:
    source = _source()
    assert 'created_at = Column(DateTime(timezone=True)' in source
    assert 'updated_at = Column(DateTime(timezone=True)' in source
    assert 'server_default=func.now()' in source
