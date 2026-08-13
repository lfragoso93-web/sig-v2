from __future__ import annotations

from app.integrations.brapi_crypto_catalog import _extract_items


def test_extract_items_normalizes_official_symbol_list() -> None:
    payload = {
        "coins": [
            "BTC",
            "eth",
            " SOL ",
        ]
    }

    assert _extract_items(payload) == [
        {"coin": "BTC"},
        {"coin": "ETH"},
        {"coin": "SOL"},
    ]


def test_extract_items_preserves_dicts_and_rejects_invalid_scalars() -> None:
    payload = {
        "coins": [
            {"coin": "BTC", "coinName": "Bitcoin"},
            "ETH",
            {"symbol": "SOL", "name": "Solana"},
            None,
            123,
            "   ",
        ]
    }

    assert _extract_items(payload) == [
        {"coin": "BTC", "coinName": "Bitcoin"},
        {"coin": "ETH"},
        {"symbol": "SOL", "name": "Solana"},
    ]


def test_extract_items_accepts_top_level_list_and_rejects_scalar_payload() -> None:
    assert _extract_items(["BTC", {"coin": "ETH"}]) == [
        {"coin": "BTC"},
        {"coin": "ETH"},
    ]
    assert _extract_items("BTC") == []
