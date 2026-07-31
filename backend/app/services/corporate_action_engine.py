"""Motor canônico e independente de provedor para eventos corporativos."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Iterable


class CorporateActionKind(StrEnum):
    SPLIT = "DESDOBRAMENTO"
    REVERSE_SPLIT = "GRUPAMENTO"
    STOCK_BONUS = "BONIFICACAO"
    SUBSCRIPTION = "SUBSCRICAO"


class CorporateActionNormalizationError(ValueError):
    """Payload corporativo não satisfaz o contrato canônico."""


@dataclass(frozen=True)
class NormalizedCorporateAction:
    source: str
    source_event_id: str
    ticker: str
    event_date: date
    kind: CorporateActionKind
    quantity_factor: Decimal
    raw_payload: dict[str, Any]

    @property
    def automatically_affects_quantity(self) -> bool:
        return self.kind != CorporateActionKind.SUBSCRIPTION


@dataclass(frozen=True)
class CorporateActionProjection:
    quantity: Decimal
    total_cost: Decimal
    applied_event_ids: tuple[str, ...]
    subscription_event_ids: tuple[str, ...]

    @property
    def average_price(self) -> Decimal:
        if self.quantity <= 0:
            return Decimal(0)
        return self.total_cost / self.quantity


def _parse_date(value: object, *, field: str) -> date:
    text = str(value or "").strip()
    if not text:
        raise CorporateActionNormalizationError(f"{field} ausente")
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise CorporateActionNormalizationError(f"{field} inválido: {text}") from exc


def _positive_decimal(value: object, *, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise CorporateActionNormalizationError(f"{field} inválido") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise CorporateActionNormalizationError(f"{field} deve ser positivo")
    return parsed


def _event_id(
    *,
    source: str,
    ticker: str,
    kind: CorporateActionKind,
    event_date: date,
    quantity_factor: Decimal,
    payload: dict[str, Any],
) -> str:
    identity = {
        "source": source,
        "ticker": ticker,
        "kind": kind.value,
        "event_date": event_date.isoformat(),
        "quantity_factor": str(quantity_factor),
        "asset_issued": payload.get("assetIssued"),
        "isin_code": payload.get("isinCode"),
        "complete_factor": payload.get("completeFactor"),
        "provider_rate": payload.get("rate"),
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return f"{source}:{digest}"


def normalize_brapi_corporate_actions(
    ticker: str,
    payload: dict[str, Any],
) -> tuple[NormalizedCorporateAction, ...]:
    """Normaliza bonificações e subscrições da rota v2 de dividendos."""

    ticker = ticker.strip().upper()
    if not ticker:
        raise CorporateActionNormalizationError("ticker ausente")

    entries = payload.get("results")
    if not isinstance(entries, list):
        raise CorporateActionNormalizationError("results deve ser lista")

    actions: list[NormalizedCorporateAction] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        symbols = {
            str(value).upper()
            for value in (entry.get("symbol"), entry.get("requestedSymbol"))
            if value
        }
        if symbols and ticker not in symbols:
            continue
        data = entry.get("data")
        if not isinstance(data, dict):
            continue

        categories = (
            ("stockDividends", CorporateActionKind.STOCK_BONUS),
            ("subscriptions", CorporateActionKind.SUBSCRIPTION),
        )
        for key, kind in categories:
            rows = data.get(key) or []
            if not isinstance(rows, list):
                raise CorporateActionNormalizationError(f"{key} deve ser lista")
            for raw in rows:
                if not isinstance(raw, dict):
                    raise CorporateActionNormalizationError(f"{key} contém item inválido")
                event_date = _parse_date(
                    raw.get("lastDatePrior") or raw.get("exDate"),
                    field=f"{key}.lastDatePrior",
                )
                if kind == CorporateActionKind.STOCK_BONUS:
                    quantity_factor = _positive_decimal(
                        raw.get("factor"), field=f"{key}.factor"
                    )
                else:
                    # Subscrição cria um direito, não quantidade automática.
                    quantity_factor = Decimal(1)
                raw_payload = dict(raw)
                source_event_id = _event_id(
                    source="brapi",
                    ticker=ticker,
                    kind=kind,
                    event_date=event_date,
                    quantity_factor=quantity_factor,
                    payload=raw_payload,
                )
                actions.append(NormalizedCorporateAction(
                    source="brapi",
                    source_event_id=source_event_id,
                    ticker=ticker,
                    event_date=event_date,
                    kind=kind,
                    quantity_factor=quantity_factor,
                    raw_payload=raw_payload,
                ))

    return tuple(sorted(actions, key=lambda item: (item.event_date, item.source_event_id)))


def normalize_yahoo_splits(
    ticker: str,
    rows: Iterable[tuple[date, object]],
) -> tuple[NormalizedCorporateAction, ...]:
    """Normaliza fatores de split do Yahoo como multiplicadores de quantidade."""

    ticker = ticker.strip().upper()
    actions: list[NormalizedCorporateAction] = []
    for event_date, raw_factor in rows:
        factor = _positive_decimal(raw_factor, field="stock_split.factor")
        if factor == 1:
            continue
        kind = (
            CorporateActionKind.SPLIT
            if factor > 1
            else CorporateActionKind.REVERSE_SPLIT
        )
        raw_payload = {
            "eventDate": event_date.isoformat(),
            "factor": str(factor),
        }
        source_event_id = _event_id(
            source="yahoo",
            ticker=ticker,
            kind=kind,
            event_date=event_date,
            quantity_factor=factor,
            payload=raw_payload,
        )
        actions.append(NormalizedCorporateAction(
            source="yahoo",
            source_event_id=source_event_id,
            ticker=ticker,
            event_date=event_date,
            kind=kind,
            quantity_factor=factor,
            raw_payload=raw_payload,
        ))
    return tuple(sorted(actions, key=lambda item: (item.event_date, item.source_event_id)))


def project_corporate_actions(
    *,
    quantity: Decimal,
    total_cost: Decimal,
    actions: Iterable[NormalizedCorporateAction],
    through_date: date,
) -> CorporateActionProjection:
    """Projeta quantidade sem alterar operações históricas ou estado derivado."""

    if quantity < 0 or total_cost < 0:
        raise ValueError("quantidade e custo devem ser não negativos")

    projected_quantity = quantity
    applied: list[str] = []
    subscriptions: list[str] = []
    ordered = sorted(actions, key=lambda item: (item.event_date, item.source_event_id))
    for action in ordered:
        if action.event_date > through_date:
            continue
        if action.kind == CorporateActionKind.SUBSCRIPTION:
            subscriptions.append(action.source_event_id)
            continue
        projected_quantity *= action.quantity_factor
        applied.append(action.source_event_id)

    return CorporateActionProjection(
        quantity=projected_quantity,
        total_cost=total_cost,
        applied_event_ids=tuple(applied),
        subscription_event_ids=tuple(subscriptions),
    )
