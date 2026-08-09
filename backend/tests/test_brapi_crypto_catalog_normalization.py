from __future__ import annotations

from app.services.crypto_catalog_normalization import normalize_crypto_catalog_items


def test_normalize_crypto_catalog_items_filters_non_mapping_entries() -> None:
    payload = [
        {"coin": "BTC", "coinName": "Bitcoin"},
        "ETH",
        {"symbol": "SOL", "name": "Solana"},
        None,
    ]

    assert normalize_crypto_catalog_items(payload) == [
        {"coin": "BTC", "coinName": "Bitcoin"},
        {"symbol": "SOL", "name": "Solana"},
    ]


def test_normalize_crypto_catalog_items_rejects_non_list_payload() -> None:
    assert normalize_crypto_catalog_items({"coin": "BTC"}) == []
