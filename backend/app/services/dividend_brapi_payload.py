"""Interpretação pura dos payloads de proventos retornados pela BRAPI."""
from typing import Any

FII_ASSET_TYPES = frozenset({"FII"})


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def extract_brapi_events(
    entry: dict[str, Any], default_category: str | None = None
) -> list[dict[str, Any]]:
    """Extrai eventos de formatos conhecidos sem acessar rede ou persistência."""

    data = entry.get("data") if isinstance(entry.get("data"), dict) else entry
    events: list[dict[str, Any]] = []

    for category, keys in (
        (
            default_category or "cash",
            (
                "cashDividends",
                "dividends",
                "provents",
                "income",
                "incomes",
                "earnings",
                "results",
            ),
        ),
        ("stock", ("stockDividends", "stock_dividends")),
        ("subscription", ("subscriptions",)),
    ):
        raw_items: list[Any] = []
        for key in keys:
            raw_items.extend(_as_list(data.get(key)))
        for item in raw_items:
            if isinstance(item, dict):
                enriched = dict(item)
                enriched.setdefault("eventCategory", category)
                events.append(enriched)

    # Alguns retornos de FII vêm como lista direta dentro de data/results, sem
    # wrapper por ticker nem chave dividends/cashDividends.
    if not events and any(
        key in data
        for key in ("paymentDate", "lastDatePrior", "rate", "value", "amount")
    ):
        enriched = dict(data)
        enriched.setdefault("eventCategory", default_category or "cash")
        events.append(enriched)

    return events


def iter_brapi_result_entries(
    payload: dict[str, Any], ticker: str
) -> list[dict[str, Any]]:
    """Retorna somente entradas compatíveis com o ticker solicitado."""

    ticker_upper = ticker.upper()
    entries: list[dict[str, Any]] = []

    for key in ("results", "stocks", "fiis", "dividends", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            entries.append(value)

    if not entries:
        entries.append(payload)

    filtered: list[dict[str, Any]] = []
    for entry in entries:
        symbol = (
            entry.get("symbol")
            or entry.get("ticker")
            or entry.get("stock")
            or entry.get("fii")
            or entry.get("code")
            or entry.get("asset")
            or ""
        )
        if not isinstance(symbol, str):
            continue
        if symbol and symbol.upper() != ticker_upper:
            continue
        filtered.append(entry)
    return filtered
