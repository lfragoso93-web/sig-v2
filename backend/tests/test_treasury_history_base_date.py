from datetime import datetime, timezone

from app.services.treasury_history_rebuild_service import extract_treasury_history


def test_extract_treasury_history_accepts_brapi_base_date_payload() -> None:
    symbol = "tesouro-selic-01032031"
    payload = {
        "results": [
            {
                "symbol": symbol,
                "bondType": "Tesouro Selic",
                "history": [
                    {
                        "baseDate": "2026-07-14",
                        "basePrice": 15234.56,
                        "buyPrice": 15240.12,
                        "sellPrice": 15228.43,
                    },
                    {
                        "baseDate": "2026-07-15",
                        "basePrice": 15242.0,
                        "buyPrice": 15247.81,
                        "sellPrice": 15235.92,
                    },
                ],
            }
        ],
        "requestedAt": "2026-07-15T12:00:00Z",
    }

    extracted = extract_treasury_history(payload, [symbol])

    assert extracted[symbol] == [
        (datetime(2026, 7, 14, tzinfo=timezone.utc), 15240.12),
        (datetime(2026, 7, 15, tzinfo=timezone.utc), 15247.81),
    ]


def test_extract_treasury_history_keeps_symbol_context_inside_history() -> None:
    symbols = [
        "tesouro-prefixado-01012029",
        "tesouro-selic-01032031",
    ]
    payload = {
        "results": [
            {
                "symbol": symbols[0],
                "history": [{"baseDate": "15/07/2026", "buyPrice": "R$ 812,34"}],
            },
            {
                "symbol": symbols[1],
                "history": [{"baseDate": "15/07/2026", "buyPrice": "15.247,81"}],
            },
        ]
    }

    extracted = extract_treasury_history(payload, symbols)

    assert extracted[symbols[0]][0][1] == 812.34
    assert extracted[symbols[1]][0][1] == 15247.81
