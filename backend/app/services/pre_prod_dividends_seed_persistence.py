"""Persistência global transacional do seed isolado de proventos.

O chamador é o único responsável por confirmar ou reverter a transação. Este
módulo adquire um advisory transaction lock dedicado, nunca cria ativos e não
materializa direitos por carteira.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import DividendType
from app.services.dividend_type_service import normalize_dividend_type
from app.services.pre_prod_dividends_seed_collector import (
    StrictDividendAssetCollection,
)

_DIVIDENDS_SEED_LOCK_KEY = 7_317_202_607_28
_NUMERIC_EQUIVALENCE_TOLERANCE = Decimal("0.00000001")
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
    """Espelha a identidade econômica persistida pelo índice único."""

    return (
        asset_id,
        ex_date,
        dividend_type,
        values["payment_date"] or ex_date,
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

    A fonte complementar pode declarar que publicou um valor truncado em uma
    escala observada. A equivalência só é aceita para ``value_per_unit``, com no
    mínimo seis casas decimais, e nunca amplia a precisão de armazenamento de
    oito casas. Divergências fora desse contrato continuam bloqueantes.
    """

    if field != "value_per_unit":
        return False

    candidates = (left, right)
    for candidate in candidates:
        payload = candidate.get("raw_payload")
        if not isinstance(payload, dict):
            continue
        comparison = payload.get("canonicalComparison")
        if not isinstance(comparison, dict):
            continue
        field_policy = comparison.get(field)
        if not isinstance(field_policy, dict):
            continue
        if field_policy.get("mode") != "truncate":
            continue
        try:
            scale = int(field_policy.get("scale"))
        except (TypeError, ValueError):
            continue
        if not (_MIN_DECLARED_COMPLEMENTARY_SCALE <= scale <= 8):
            continue

        left_value = left[field]
        right_value = right[field]
        quantum = Decimal(1).scaleb(-scale)
        return left_value.quantize(quantum, rounding=ROUND_DOWN) == right_value.quantize(
            quantum,
            rounding=ROUND_DOWN,
        )
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


def _collapse_estimated_payment_components(events: tuple) -> tuple[tuple, int]:
    """Absorve parcelas estimadas quando já existe o total canônico da fonte."""

    grouped: dict[tuple, list] = {}
    for event in events:
        key = (
            event.ex_date,
            normalize_dividend_type(event.dividend_type),
        )
        grouped.setdefault(key, []).append(event)

    retained: list = []
    collapsed = 0
    for group in grouped.values():
        estimated = [
            event
            for event in group
            if _ESTIMATED_PAYMENT_REMARK
            in str((event.raw_payload or {}).get("remarks") or "")
        ]
        canonical = [event for event in group if event not in estimated]
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
                collapsed += len(estimated)
                continue
        retained.extend(group)
    return tuple(retained), collapsed


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
    existing = {}
    for row in existing_result.scalars().all():
        row_values = {"payment_date": row.payment_date}
        existing[
            _storage_identity(
                asset_id=row.asset_id,
                ex_date=row.ex_date,
                dividend_type=row.dividend_type,
                values=row_values,
            )
        ] = row

    created = 0
    updated = 0
    unchanged = 0
    seen: dict[
        tuple[int, object, DividendType],
        list[tuple[str, dict]],
    ] = {}

    for collection in collections:
        asset = assets[(collection.ticker, collection.asset_type)]
        for source_collection in sorted(collection.sources, key=_source_sort_key):
            source = source_collection.source.strip().lower()
            source_events, collapsed = _collapse_estimated_payment_components(
                source_collection.normalized_rows
            )
            unchanged += collapsed
            for event in source_events:
                dividend_type = normalize_dividend_type(event.dividend_type)
                base_key = (asset.id, event.ex_date, dividend_type)
                values = _event_values(event, source)

                prior_events = seen.get(base_key, [])
                equivalent = next(
                    (
                        prior
                        for prior in prior_events
                        if not _conflicting_event_fields(prior[1], values)
                    ),
                    None,
                )
                if equivalent is not None:
                    unchanged += 1
                    continue

                cross_source_prior = next(
                    (prior for prior in prior_events if prior[0] != source),
                    None,
                )
                if cross_source_prior is not None:
                    prior_source, prior_values = cross_source_prior
                    conflicts = _conflicting_event_fields(prior_values, values)
                    raise DividendsSeedPersistenceError(
                        "evento global conflitante entre fontes: "
                        f"{collection.ticker}/{event.ex_date}/"
                        f"{dividend_type.value} ({prior_source}, {source}); "
                        "valores divergentes: "
                        + _render_conflicting_event_values(
                            fields=conflicts,
                            left_source=prior_source,
                            left=prior_values,
                            right_source=source,
                            right=values,
                        )
                    )

                same_identity_prior = next(
                    (
                        prior
                        for prior in prior_events
                        if _storage_identity(
                            asset_id=asset.id,
                            ex_date=event.ex_date,
                            dividend_type=dividend_type,
                            values=prior[1],
                        )
                        == _storage_identity(
                            asset_id=asset.id,
                            ex_date=event.ex_date,
                            dividend_type=dividend_type,
                            values=values,
                        )
                    ),
                    None,
                )
                if same_identity_prior is not None:
                    prior_source, prior_values = same_identity_prior
                    conflicts = _conflicting_event_fields(prior_values, values)
                    raise DividendsSeedPersistenceError(
                        "evento global conflitante na mesma fonte: "
                        f"{collection.ticker}/{event.ex_date}/"
                        f"{dividend_type.value} ({source}); "
                        "valores divergentes: "
                        + _render_conflicting_event_values(
                            fields=conflicts,
                            left_source=prior_source,
                            left=prior_values,
                            right_source=source,
                            right=values,
                        )
                    )

                prior_events.append((source, values))
                seen[base_key] = prior_events
                storage_key = _storage_identity(
                    asset_id=asset.id,
                    ex_date=event.ex_date,
                    dividend_type=dividend_type,
                    values=values,
                )
                row = existing.get(storage_key)
                if row is None:
                    row = AssetDividend(
                        asset_id=asset.id,
                        ex_date=event.ex_date,
                        dividend_type=dividend_type,
                        **values,
                    )
                    db.add(row)
                    existing[storage_key] = row
                    created += 1
                    continue

                changed = False
                for field, value in values.items():
                    if getattr(row, field) != value:
                        setattr(row, field, value)
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
