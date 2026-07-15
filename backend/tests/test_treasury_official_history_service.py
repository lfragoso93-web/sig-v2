from app.services.treasury_official_history_service import (
    _payload_diagnostics,
    _payload_items,
    _symbol_from_item,
)


def test_payload_items_reads_results_list():
    payload = {"results": [{"symbol": "tesouro-selic-01032031"}]}
    assert _payload_items(payload) == payload["results"]


def test_symbol_from_item_accepts_only_canonical_brapi_symbol():
    assert _symbol_from_item({"symbol": "tesouro-selic-01032031"}) == "tesouro-selic-01032031"
    assert _symbol_from_item({"symbol": "Tesouro Selic 2031"}) is None
    assert _symbol_from_item({"symbol": "tesouro-renda-mais-2060"}) == "tesouro-renda-mais-2060"


def test_payload_diagnostics_exposes_shape_without_values():
    payload = {
        "results": [
            {
                "symbol": "tesouro-selic-01032031",
                "historicalData": [
                    {"date": "2026-07-15", "buyPrice": 15240.12}
                ],
            }
        ],
        "requestedAt": "2026-07-15T00:00:00Z",
        "took": 12,
    }

    diagnostics = _payload_diagnostics(payload)

    assert diagnostics["results_count"] == 1
    assert diagnostics["first_item_keys"] == ["historicalData", "symbol"]
    assert diagnostics["first_item_historicalData_count"] == 1
    assert diagnostics["first_item_historicalData_keys"] == ["buyPrice", "date"]
    assert "15240.12" not in str(diagnostics)
