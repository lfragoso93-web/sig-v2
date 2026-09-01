from decimal import Decimal

import pytest

from app.services.pre_prod_dividends_seed_persistence import (
    _declared_precision_equivalent,
)


def _canonical(value: float) -> dict:
    return {
        "value_per_unit": Decimal(str(value)),
        "raw_payload": {"rate": value},
    }


def _quantized(value: float) -> dict:
    return {
        "value_per_unit": Decimal(str(value)),
        "raw_payload": {
            "rate": value,
            "eventSemantics": "aggregate_cash_by_ex_date",
            "canonicalComparison": {
                "value_per_unit": {
                    "mode": "provider_quantized",
                    "scale": 6,
                }
            },
        },
    }


@pytest.mark.parametrize(
    ("canonical", "quantized"),
    [
        (0.24956495, 0.249565),  # AFLT3/2011
        (0.08453883, 0.084538),  # AALR3/2019
        (0.19024149, 0.190242),  # AFLT3/2016
    ],
)
def test_provider_quantized_accepts_values_within_declared_resolution(
    canonical: float,
    quantized: float,
) -> None:
    assert _declared_precision_equivalent(
        field="value_per_unit",
        left=_canonical(canonical),
        right=_quantized(quantized),
    )


def test_provider_quantized_accepts_exact_declared_resolution_boundary() -> None:
    assert _declared_precision_equivalent(
        field="value_per_unit",
        left=_canonical(0.29248),
        right=_quantized(0.292479),
    )


@pytest.mark.parametrize(
    ("canonical", "quantized"),
    [
        (0.08453901, 0.084538),  # acima do quantum declarado de 1e-6
        (0.08453983, 0.084538),  # divergência materialmente maior
    ],
)
def test_provider_quantized_rejects_value_outside_declared_resolution(
    canonical: float,
    quantized: float,
) -> None:
    assert not _declared_precision_equivalent(
        field="value_per_unit",
        left=_canonical(canonical),
        right=_quantized(quantized),
    )
