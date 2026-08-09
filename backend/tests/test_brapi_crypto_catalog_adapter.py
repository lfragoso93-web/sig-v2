from __future__ import annotations

from app.integrations.brapi_crypto_catalog import _extract_items


def test_extract_items_filters_heterogeneous_dict_payload() -> None:
    payload = {
        "coins": [
            {"coin": "BTC", "coinName": "Bitcoin"},
            "ETH",
            {"symbol": "SOL", "name": "Solana"},
            None,
        ]
    }

    assert _extract_items(payload) == [
        {"coin": "BTC", "coinName": "Bitcoin"},
        {"symbol": "SOL", "name": "Solana"},
    ]


def test_extract_items_accepts_top_level_list_and_rejects_scalar() -> None:
    assert _extract_items([{"coin": "BTC"}, "ETH"]) == [{"coin": "BTC"}]
    assert _extract_items("BTC") == []
