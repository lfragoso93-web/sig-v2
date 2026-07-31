from datetime import date
from decimal import Decimal

import pytest

from app.services.corporate_action_engine import (
    CorporateActionKind,
    CorporateActionNormalizationError,
    normalize_brapi_corporate_actions,
    normalize_yahoo_splits,
    project_corporate_actions,
)


def test_normalizes_brapi_stock_bonus_and_subscription() -> None:
    payload = {
        "results": [{
            "symbol": "ITSA4",
            "data": {
                "cashDividends": [{"rate": 0.02}],
                "stockDividends": [{
                    "assetIssued": "BRITSAACNPR7",
                    "factor": 1.02,
                    "completeFactor": "1,02 para 1",
                    "lastDatePrior": "2025-12-18T03:00:00.000Z",
                }],
                "subscriptions": [{
                    "assetIssued": "BRITSAACNPR7",
                    "lastDatePrior": "2026-01-10T03:00:00.000Z",
                    "rate": 9.5,
                }],
            },
        }],
    }

    actions = normalize_brapi_corporate_actions("itsa4", payload)

    assert [item.kind for item in actions] == [
        CorporateActionKind.STOCK_BONUS,
        CorporateActionKind.SUBSCRIPTION,
    ]
    assert actions[0].quantity_factor == Decimal("1.02")
    assert actions[1].quantity_factor == Decimal("1")
    assert actions[0].source_event_id.startswith("brapi:")
    assert actions == normalize_brapi_corporate_actions("ITSA4", payload)


def test_brapi_invalid_bonus_factor_is_blocking() -> None:
    payload = {
        "results": [{
            "symbol": "ITSA4",
            "data": {
                "stockDividends": [{
                    "factor": 0,
                    "lastDatePrior": "2025-12-18",
                }],
            },
        }],
    }

    with pytest.raises(CorporateActionNormalizationError, match="deve ser positivo"):
        normalize_brapi_corporate_actions("ITSA4", payload)


def test_yahoo_split_factors_use_one_quantity_multiplier_convention() -> None:
    actions = normalize_yahoo_splits(
        "AERI3",
        [
            (date(2024, 5, 14), Decimal("0.05")),
            (date(2025, 6, 1), Decimal("2")),
            (date(2026, 1, 1), Decimal("1")),
        ],
    )

    assert [item.kind for item in actions] == [
        CorporateActionKind.REVERSE_SPLIT,
        CorporateActionKind.SPLIT,
    ]
    assert [item.quantity_factor for item in actions] == [
        Decimal("0.05"),
        Decimal("2"),
    ]


def test_projection_preserves_total_cost_and_does_not_apply_subscription() -> None:
    bonus = normalize_brapi_corporate_actions("ITSA4", {
        "results": [{
            "symbol": "ITSA4",
            "data": {
                "stockDividends": [{
                    "factor": 1.10,
                    "lastDatePrior": "2023-01-01",
                }],
                "subscriptions": [{
                    "lastDatePrior": "2023-02-01",
                    "rate": 8,
                }],
            },
        }],
    })
    splits = normalize_yahoo_splits(
        "ITSA4",
        [
            (date(2023, 3, 1), Decimal("2")),
            (date(2024, 5, 1), Decimal("0.25")),
        ],
    )

    projection = project_corporate_actions(
        quantity=Decimal("100"),
        total_cost=Decimal("1000"),
        actions=(*bonus, *splits),
        through_date=date(2023, 12, 31),
    )

    assert projection.quantity == Decimal("220.0")
    assert projection.total_cost == Decimal("1000")
    assert projection.average_price == Decimal("1000") / Decimal("220.0")
    assert len(projection.applied_event_ids) == 2
    assert len(projection.subscription_event_ids) == 1


def test_projection_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError, match="não negativos"):
        project_corporate_actions(
            quantity=Decimal("-1"),
            total_cost=Decimal("0"),
            actions=(),
            through_date=date.today(),
        )
