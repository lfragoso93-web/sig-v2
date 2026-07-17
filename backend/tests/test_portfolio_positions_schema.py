from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.schemas.portfolio_positions import PositionGroupResponse


def _group_payload() -> dict:
    return {
        "label": "Ações",
        "count": 1,
        "total_value": 1100.0,
        "total_invested": 1000.0,
        "daily_variation_value": 10.0,
        "daily_variation_pct": 0.92,
        "variation_pct": 0.92,
        "variation_reference_date": "2026-07-16",
        "capital_result_value": 100.0,
        "capital_result_pct": 10.0,
        "received_dividends": 25.0,
        "proventos_grupo": 25.0,
        "total_result_value": 125.0,
        "total_result_pct": 12.5,
        "performance_source": "intraday_valuation_and_received_dividends",
        "proventos_as_of": "2026-07-17",
        "target_pct": 30.0,
        "positions": [
            {
                "id": 1,
                "ticker": "TEST3",
                "asset_type": "ACAO",
                "asset_label": "Ações",
                "quantity": 10.0,
                "average_price": 100.0,
                "average_price_brl": 100.0,
                "average_price_usd": None,
                "current_price": 110.0,
                "current_price_brl": 110.0,
                "current_price_usd": None,
                "current_value": 1100.0,
                "invested_value": 1000.0,
                "variation_value": 100.0,
                "variation_percent": 10.0,
                "allocation_pct": 100.0,
                "logo_url": None,
                "is_usd": False,
                "currency": "BRL",
            }
        ],
    }


def test_position_group_contract_preserves_canonical_class_totals():
    payload = _group_payload()
    payload["total_invested"] = 1234.56
    payload["positions"][0]["invested_value"] = 1000.0

    group = PositionGroupResponse.model_validate(payload)

    assert group.total_invested == 1234.56
    assert group.count == len(group.positions)


@pytest.mark.parametrize("legacy_field", ["rentabilidade_pct", "retorno_pct"])
def test_position_group_contract_rejects_legacy_return_fields(legacy_field: str):
    payload = _group_payload()
    payload[legacy_field] = 99.0

    with pytest.raises(ValidationError):
        PositionGroupResponse.model_validate(payload)


def test_position_group_contract_requires_total_invested():
    payload = deepcopy(_group_payload())
    payload.pop("total_invested")

    with pytest.raises(ValidationError):
        PositionGroupResponse.model_validate(payload)
