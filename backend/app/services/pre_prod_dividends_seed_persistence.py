"""Persistência global transacional do seed isolado de proventos.

O chamador é o único responsável por confirmar ou reverter a transação. Este
módulo adquire um advisory transaction lock dedicado, nunca cria ativos e não
materializa direitos por carteira.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from sqlalchemy import select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType
from app.services.dividend_type_service import normalize_dividend_type
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendAssetCollection,
)

_DIVIDENDS_SEED_LOCK_KEY = 7_317_202_607_28
_NUMERIC_EQUIVALENCE_TOLERANCE = Decimal("0.00000001")
_SAME_SOURCE_AGGREGATE_TOLERANCE = Decimal("0.000001")
_STORAGE_VALUE_QUANTUM = Decimal("0.00000001")
_MIN_DECLARED_COMPLEMENTARY_SCALE = 6
_ESTIMATED_PAYMENT_REMARK = "csv:payment_date_estimated"
_SOURCE_PRECEDENCE = {
    "brapi": 0,
    "yfinance_history": 1,
}
_CANONICAL_EVENT_FIELDS = (
    "record_date",
    "payment_date",
    "approved_on",
    "value_per_unit",
    "gross_value_per_unit",
    "factor",
    "complete_factor",
    "isin_code",
    "asset_issued",
    "related_to",
    "remarks",
)
_NUMERIC_EVENT_FIELDS = {
    "value_per_unit",
    "gross_value_per_unit",
    "factor",
    "complete_factor",
}


class DividendsSeedPersistenceError(RuntimeError):
    """Falha bloqueante da persistência global de proventos."""


class DividendsSeedAlreadyRunningError(DividendsSeedPersistenceError):
    """Outra transação mantém o lock do estágio de proventos."""


@dataclass(frozen=True)
class DividendsSeedPersistenceResult:
    created: int
    updated: int
    unchanged: int

    @property
    def processed(self) -> int:
        return self.created + self.updated + self.unchanged


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _storage_value(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(_STORAGE_VALUE_QUANTUM, rounding=ROUND_HALF_UP)


def _reject_concurrent_brapi_yahoo_rows(
    collections: tuple[StrictDividendAssetCollection, ...],
) -> None:
    for collection in collections:
        row_sources = {
            source_collection.source.strip().lower()
            for source_collection in collection.sources
            if source_collection.normalized_rows
        }
        if {"brapi", "yfinance_history"}.issubset(row_sources):
            raise DividendsSeedPersistenceError(
                "coleção de proventos mistura linhas normalizadas de BRAPI e Yahoo: "
                f"{collection.ticker}/{collection.asset_type}; "
                "Yahoo é permitido apenas como fallback após BRAPI sem cobertura"
            )


def _event_values(event, source: str) -> dict:
    return {
        "record_date": event.record_date,
        "payment_date": event.payment_date,
        "approved_on": event.approved_on,
        "value_per_unit": _decimal(event.value_per_unit),
        "gross_value_per_unit": _decimal(event.gross_value_per_unit),
        "factor": _decimal(event.factor),
        "complete_factor": _decimal(event.complete_factor),
        "isin_code": event.isin_code,
        "asset_issued": event.asset_issued,
        "related_to": event.related_to,
        "remarks": event.remarks,
        "raw_payload": event.raw_payload,
        "source": source,
    }


def _storage_identity(
    *,
    asset_id: int,
    ex_date,
    dividend_type: DividendType,
    values: dict,
) -> tuple:
    """Espelha a identidade de ocorrência persistida pelo índice único."""

    return (
        asset_id,
        ex_date,
        dividend_type,
        values["payment_date"] or ex_date,
        _storage_value(values["value_per_unit"]),
    )


def _source_sort_key(source_collection) -> tuple[int, str]:
    source = source_collection.source.strip().lower()
    return (_SOURCE_PRECEDENCE.get(source, len(_SOURCE_PRECEDENCE)), source)


def _declared_precision_equivalent(
    *,
    field: str,
    left: dict,
    right: dict,
) -> bool:
    """Reconcilia apenas precisão complementar explicitamente declarada.

    A fonte complementar deve declarar a escala observada e a política de
    redução de precisão. ``provider_quantized`` representa uma fonte cujo valor
    é publicado em resolução limitada: a equivalência só é aceita quando a
    diferença absoluta não excede uma unidade da escala declarada. Os modos
    ``truncate`` e ``round_half_up`` preservam comparação determinística por
    quantização. A regra só vale para ``value_per_unit``, com no mínimo seis
    casas decimais, sem ampliar a precisão física de oito casas. Divergências
    fora desse contrato continuam bloqueantes.
    """

    if field != "value_per_unit":
        return False

    rounding_by_mode = {
        "truncate": (ROUND_DOWN,),
        "round_half_up": (ROUND_HALF_UP,),
    }
    candidates = ((left, right), (right, left))
    for candidate, counterpart in candidates:
        payload = candidate.get("raw_payload")
        if not isinstance(payload, dict):
            continue
        comparison = payload.get("canonicalComparison")
        if not isinstance(comparison, dict):
            continue
        field_policy = comparison.get(field)
        if not isinstance(field_policy, dict):
            continue
        mode = field_policy.get("mode")
        try:
            scale = int(field_policy.get("scale"))
        except (TypeError, ValueError):
            continue
        if not (_MIN_DECLARED_COMPLEMENTARY_SCALE <= scale <= 8):
            continue

        declared_value = candidate[field]
        other_value = counterpart[field]
        quantum = Decimal(1).scaleb(-scale)

        if mode == "provider_quantized":
            if abs(other_value - declared_value) <= quantum:
                return True
            continue

        roundings = rounding_by_mode.get(mode)
        if roundings is None:
            continue
        declared_quantized = declared_value.quantize(quantum, rounding=ROUND_HALF_UP)
        if any(
            other_value.quantize(quantum, rounding=rounding) == declared_quantized
            for rounding in roundings
        ):
            return True
    return False


def _conflicting_event_fields(left: dict, right: dict) -> tuple[str, ...]:
    """Compara somente atributos canônicos presentes nas duas fontes."""

    conflicts: list[str] = []
    for field in _CANONICAL_EVENT_FIELDS:
        left_value = left[field]
        right_value = right[field]
        if left_value is None or right_value is None:
            continue
        if field in _NUMERIC_EVENT_FIELDS:
            if abs(left_value - right_value) <= _NUMERIC_EQUIVALENCE_TOLERANCE:
                continue
            if _declared_precision_equivalent(field=field, left=left, right=right):
                continue
            conflicts.append(field)
        elif left_value != right_value:
            conflicts.append(field)
    return tuple(conflicts)


def _render_conflicting_event_values(
    *,
    fields: tuple[str, ...],
    left_source: str,
    left: dict,
    right_source: str,
    right: dict,
) -> str:
    """Renderiza somente valores normalizados dos campos em conflito."""

    return "; ".join(
        f"{field} ({left_source}={left[field]}, {right_source}={right[field]})"
        for field in fields
    )


def _collapse_declared_same_source_aggregate(group: list) -> tuple[tuple, tuple] | None:
    """Reconcilia um agregado canônico apenas sob evidência estrutural forte."""

    if len(group) != 3:
        return None
    aggregate_candidates = [event for event in group if event.approved_on is None]
    if len(aggregate_candidates) != 1:
        return None

    aggregate = aggregate_candidates[0]
    components = [event for event in group if event is not aggregate]
    approvals = {event.approved_on for event in components}
    if len(approvals) != 1 or None in approvals:
        return None

    for field in ("record_date", "payment_date", "isin_code"):
        aggregate_value = getattr(aggregate, field)
        component_values = {getattr(event, field) for event in components}
        if aggregate_value is None or component_values != {aggregate_value}:
            return None

    aggregate_value = _decimal(aggregate.value_per_unit)
    component_values = [_decimal(event.value_per_unit) for event in components]
    if aggregate_value is None or any(value is None for value in component_values):
        return None
    if (
        abs(sum(component_values, Decimal(0)) - aggregate_value)
        > _SAME_SOURCE_AGGREGATE_TOLERANCE
    ):
        return None

    return tuple(components), (aggregate,)


def _collapse_estimated_payment_components(
    events: tuple,
) -> tuple[tuple, tuple]:
    """Reconcilia estimativas e agregados da mesma fonte de forma conservadora."""

    grouped: dict[tuple, list] = {}
    for event in events:
        key = (
            event.ex_date,
            normalize_dividend_type(event.dividend_type),
        )
        grouped.setdefault(key, []).append(event)

    retained: list = []
    collapsed: list = []
    for group in grouped.values():
        estimated = [
            event
            for event in group
            if _ESTIMATED_PAYMENT_REMARK
            in str((event.raw_payload or {}).get("remarks") or "")
        ]
        canonical = [event for event in group if event not in estimated]
        if len(estimated) == 1 and not canonical:
            retained.extend(group)
            continue
        if len(estimated) == 1 and len(canonical) == 1:
            estimated_value = _decimal(estimated[0].value_per_unit)
            canonical_value = _decimal(canonical[0].value_per_unit)
            if (
                estimated_value is not None
                and canonical_value is not None
                and abs(estimated_value - canonical_value)
                > _NUMERIC_EQUIVALENCE_TOLERANCE
            ):
                retained.extend(group)
                continue
        if len(estimated) >= 2 and len(canonical) == 1:
            component_values = [_decimal(event.value_per_unit) for event in estimated]
            canonical_value = _decimal(canonical[0].value_per_unit)
            if (
                canonical_value is not None
                and all(value is not None for value in component_values)
                and abs(sum(component_values, Decimal(0)) - canonical_value)
                <= _NUMERIC_EQUIVALENCE_TOLERANCE
            ):
                retained.append(canonical[0])
                collapsed.extend(estimated)
                continue
        if not estimated:
            aggregate_collapse = _collapse_declared_same_source_aggregate(group)
            if aggregate_collapse is not None:
                aggregate_retained, aggregate_collapsed = aggregate_collapse
                retained.extend(aggregate_retained)
                collapsed.extend(aggregate_collapsed)
                continue
        if estimated or len(group) >= 3:
            raise DividendsSeedPersistenceError(
                "evento global conflitante na mesma fonte"
            )
        retained.extend(group)
    return tuple(retained), tuple(collapsed)


async def persist_asset_dividends_strict(
    *,
    db: AsyncSession,
    collections: tuple[StrictDividendAssetCollection, ...],
) -> DividendsSeedPersistenceResult:
    """Persiste eventos globais sem ``commit`` ou ``rollback`` internos."""

    acquired = await db.scalar(
        text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
        {"lock_key": _DIVIDENDS_SEED_LOCK_KEY},
    )
    if not acquired:
        raise DividendsSeedAlreadyRunningError(
            "estágio de proventos já está em execução"
        )

    scopes = {(item.ticker, item.asset_type) for item in collections}
    if not scopes:
        return DividendsSeedPersistenceResult(created=0, updated=0, unchanged=0)
    _reject_concurrent_brapi_yahoo_rows(collections)

    asset_result = await db.execute(
        select(Asset).where(tuple_(Asset.ticker, Asset.asset_type).in_(sorted(scopes)))
    )
    assets = {
        (asset.ticker.upper(), asset.asset_type.upper()): asset
        for asset in asset_result.scalars().all()
    }
    missing = sorted(scopes - set(assets))
    if missing:
        rendered = ", ".join(f"{ticker}/{asset_type}" for ticker, asset_type in missing)
        raise DividendsSeedPersistenceError(
            f"ativos globais não cadastrados: {rendered}"
        )

    asset_ids = [asset.id for asset in assets.values()]
    existing_result = await db.execute(
        select(AssetDividend).where(AssetDividend.asset_id.in_(asset_ids))
    )
    existing = existing_result.scalars().all()
    by_identity = {
        (
            item.asset_id,
            item.ex_date,
            item.dividend_type,
            item.payment_date or item.ex_date,
            _storage_value(_decimal(item.value_per_unit)),
        ): item
        for item in existing
    }

    created = 0
    updated = 0
    unchanged = 0
    seen: dict[tuple[int, object, DividendType], list[tuple[str, dict]]] = {}

    for collection in collections:
        asset = assets[(collection.ticker, collection.asset_type)]
        for source_collection in sorted(collection.sources, key=_source_sort_key):
            source = source_collection.source.strip().lower()
            retained, _collapsed = _collapse_estimated_payment_components(
                source_collection.normalized_rows
            )

            for event in retained:
                dividend_type = normalize_dividend_type(event.dividend_type)
                values = _event_values(event, source)
                identity_key = (asset.id, event.ex_date, dividend_type)
                prior_events = seen.setdefault(identity_key, [])

                conflict = False
                for prior_source, prior_values in prior_events:
                    if prior_source == source:
                        continue
                    conflicts = _conflicting_event_fields(prior_values, values)
                    if not conflicts:
                        continue
                    rendered = _render_conflicting_event_values(
                        fields=conflicts,
                        left_source=prior_source,
                        left=prior_values,
                        right_source=source,
                        right=values,
                    )
                    raise DividendsSeedPersistenceError(
                        "evento global conflitante entre fontes: "
                        f"{collection.ticker}/{event.ex_date}/{dividend_type.value} "
                        f"({prior_source}, {source}); valores divergentes: {rendered}"
                    )
                if conflict:
                    continue

                prior_events.append((source, values))
                storage_key = _storage_identity(
                    asset_id=asset.id,
                    ex_date=event.ex_date,
                    dividend_type=dividend_type,
                    values=values,
                )
                stored = by_identity.get(storage_key)
                if stored is None:
                    stored = AssetDividend(
                        asset_id=asset.id,
                        record_date=event.record_date,
                        ex_date=event.ex_date,
                        payment_date=event.payment_date,
                        approved_on=event.approved_on,
                        value_per_unit=_storage_value(values["value_per_unit"]),
                        gross_value_per_unit=_storage_value(
                            values["gross_value_per_unit"]
                        ),
                        factor=_storage_value(values["factor"]),
                        complete_factor=_storage_value(values["complete_factor"]),
                        dividend_type=dividend_type,
                        isin_code=event.isin_code,
                        asset_issued=event.asset_issued,
                        related_to=event.related_to,
                        remarks=event.remarks,
                        source=source,
                    )
                    db.add(stored)
                    by_identity[storage_key] = stored
                    created += 1
                    continue

                changes = {
                    "record_date": event.record_date,
                    "payment_date": event.payment_date,
                    "approved_on": event.approved_on,
                    "gross_value_per_unit": _storage_value(
                        values["gross_value_per_unit"]
                    ),
                    "factor": _storage_value(values["factor"]),
                    "complete_factor": _storage_value(values["complete_factor"]),
                    "isin_code": event.isin_code,
                    "asset_issued": event.asset_issued,
                    "related_to": event.related_to,
                    "remarks": event.remarks,
                }
                changed = False
                for field, incoming in changes.items():
                    if incoming is None:
                        continue
                    current = getattr(stored, field)
                    if current is None:
                        setattr(stored, field, incoming)
                        changed = True
                if source == "brapi" and stored.source != "brapi":
                    stored.source = "brapi"
                    changed = True
                if changed:
                    updated += 1
                else:
                    unchanged += 1

    if created or updated:
        await db.flush()
    return DividendsSeedPersistenceResult(
        created=created,
        updated=updated,
        unchanged=unchanged,
    )
