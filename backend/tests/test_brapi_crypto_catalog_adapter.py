from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.integrations.brapi_crypto_catalog import (
    _extract_items,
    fetch_crypto_catalog_all,
)


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


@pytest.mark.asyncio
async def test_fetch_crypto_catalog_all_terminates_on_repeated_page() -> None:
    # Simula endpoint que repete as 507 moedas na pagina 1 e 2
    mock_resp = httpx.Response(
        status_code=200,
        json={"coins": [f"COIN_{i}" for i in range(507)]},
        request=httpx.Request("GET", "https://brapi.dev/api/v2/crypto/available"),
    )

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        coins = await fetch_crypto_catalog_all(limit=500)
        assert len(coins) == 507
