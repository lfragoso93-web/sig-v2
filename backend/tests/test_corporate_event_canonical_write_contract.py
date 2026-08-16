from pathlib import Path


_SERVICE = Path(__file__).resolve().parents[1] / "app/services/corporate_event_service.py"


def test_corporate_event_write_path_uses_only_canonical_identity_fields() -> None:
    source = _SERVICE.read_text(encoding="utf-8")

    forbidden = (
        "CorporateEvent.brapi_event_id",
        "event_date=action.event_date",
        "ratio=action.quantity_factor",
        "brapi_event_id=action.source_event_id",
        "raw_data=_serialized_action(action)",
        "portfolio_id=None",
    )
    unexpected = [token for token in forbidden if token in source]
    assert unexpected == [], f"write path corporativo ainda usa aliases legados: {unexpected}"
