"""Pure cash-flow helpers for profitability fallback calculations."""

from collections.abc import Iterable
from decimal import Decimal
from typing import Protocol


class TransactionCashFlow(Protocol):
    operation: object
    quantity: object
    price: object
    fees: object
    asset_type: object
    currency: object
    fx_rate: object


def calculate_net_contributed(
    transactions: Iterable[TransactionCashFlow],
    *,
    buy_operation: object,
    sell_operation: object,
    usd_asset_types: set[str],
    normalize_asset_type,
) -> float:
    """Return net contributed cash in BRL for the supplied transactions.

    Buys increase contributed cash by gross value plus fees. Sells reduce it by
    net proceeds, therefore sale fees remain part of the contributed balance.
    Corporate actions do not enter this calculation because they do not move
    cash by themselves.
    """
    total = Decimal(0)

    for transaction in transactions:
        quantity = Decimal(str(transaction.quantity or 0))
        price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))
        operation = transaction.operation
        asset_type = normalize_asset_type(transaction.asset_type)
        currency = str(getattr(transaction, "currency", "BRL") or "BRL").upper()
        is_usd = currency == "USD" or asset_type in usd_asset_types

        fx_rate = Decimal(1)
        if is_usd:
            saved_fx_rate = getattr(transaction, "fx_rate", None)
            if saved_fx_rate is not None and Decimal(str(saved_fx_rate or 0)) > 0:
                fx_rate = Decimal(str(saved_fx_rate))

        gross_value = quantity * price * fx_rate
        fees_brl = fees * fx_rate

        if operation == buy_operation:
            total += gross_value + fees_brl
        elif operation == sell_operation:
            total -= gross_value - fees_brl

    return float(total)
