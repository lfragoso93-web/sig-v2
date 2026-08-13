from __future__ import annotations

from app.schemas.portfolio_positions import PositionGroupResponse
from app.services.canonical_positions_service import _project_group


def _legacy_group() -> dict:
    return {
        "asset_type": "CRIPTO",
        "label": "Criptomoedas",
        "color": "#14b8a6",
        "count": 1,
        "total_value": 330.37,
        "total_invested": 500.0,
        "current_pct": 100.0,
        "target_pct": None,
        "deviation_pct": None,
        "proventos": 0.0,
        "previous_reference_date": "2026-08-11",
        "daily_variation_value": -2.45,
        "daily_variation_pct": -0.7369,
        "positions": [
            {
                "id": 1,
                "ticker": "BTC",
                "asset_type": "CRIPTO",
                "asset_label": "Criptomoedas",
                "quantity": 0.001,
                "average_price": 500000.0,
                "average_price_brl": 500000.0,
                "average_price_usd": None,
                "current_price": 330368.116,
                "current_price_brl": 330368.116,
                "current_price_usd": None,
                "current_value": 330.37,
                "invested_value": 500.0,
                "variation_value": -169.63,
                "variation_percent": -33.9264,
                "allocation_pct": 100.0,
                "logo_url": None,
                "is_usd": False,
                "currency": "BRL",
                "legacy_extra": "must not leak",
            }
        ],
    }


def test_projected_group_validates_against_strict_response_schema() -> None:
    projected = _project_group(
        _legacy_group(),
        received_dividends=0.0,
        proventos_as_of="2026-08-12",
    )

    validated = PositionGroupResponse.model_validate(projected)

    assert validated.variation_pct == -0.7369
    assert validated.variation_reference_date == "2026-08-11"
    assert validated.positions[0].ticker == "BTC"


def test_projection_drops_legacy_group_and_position_extras() -> None:
    projected = _project_group(
        _legacy_group(),
        received_dividends=0.0,
        proventos_as_of="2026-08-12",
    )

    assert "asset_type" not in projected
    assert "color" not in projected
    assert "current_pct" not in projected
    assert "deviation_pct" not in projected
    assert "proventos" not in projected
    assert "previous_reference_date" not in projected
    assert "legacy_extra" not in projected["positions"][0]
