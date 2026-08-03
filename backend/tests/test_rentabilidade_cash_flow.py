from types import SimpleNamespace

from app.models.transaction import OperationType
from app.services.rentabilidade_cash_flow import calculate_net_contributed


def _normalize_asset_type(value: object) -> str:
    return str(value).upper()


def test_net_contributed_uses_net_sale_proceeds_in_brl():
    transactions = [
        SimpleNamespace(
            operation=OperationType.buy,
            quantity=10,
            price=100,
            fees=10,
            asset_type="ACAO",
            currency="BRL",
            fx_rate=None,
        ),
        SimpleNamespace(
            operation=OperationType.sell,
            quantity=4,
            price=150,
            fees=5,
            asset_type="ACAO",
            currency="BRL",
            fx_rate=None,
        ),
    ]

    result = calculate_net_contributed(
        transactions,
        buy_operation=OperationType.buy,
        sell_operation=OperationType.sell,
        usd_asset_types={"STOCK", "ETF_INTERNACIONAL"},
        normalize_asset_type=_normalize_asset_type,
    )

    assert result == 415.0


def test_net_contributed_converts_values_and_fees_with_saved_fx_rate():
    transactions = [
        SimpleNamespace(
            operation=OperationType.buy,
            quantity=10,
            price=20,
            fees=2,
            asset_type="STOCK",
            currency="USD",
            fx_rate=5,
        ),
        SimpleNamespace(
            operation=OperationType.sell,
            quantity=2,
            price=30,
            fees=1,
            asset_type="STOCK",
            currency="USD",
            fx_rate=5,
        ),
    ]

    result = calculate_net_contributed(
        transactions,
        buy_operation=OperationType.buy,
        sell_operation=OperationType.sell,
        usd_asset_types={"STOCK", "ETF_INTERNACIONAL"},
        normalize_asset_type=_normalize_asset_type,
    )

    assert result == 715.0
