"""Persistência global transacional do seed isolado de proventos.

O chamador é o único responsável por confirmar ou reverter a transação. Este
módulo adquire um advisory transaction lock dedicado, nunca cria ativos e não
materializa direitos por carteira.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

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


def _conflicting_event_fields(left: dict, right: dict) -> tuple[str, ...]:
    """Compara somente atributos canônicos presentes nas duas fontes."""

    conflicts: list[str] = []
    for field in _CANONICAL_EVENT_FIELDS:
        left_value = left[field]
        right_value = right[field]
        if left_value is None or right_value is None:
            continue
        if field in _NUMERIC_EVENT_FIELDS:
            if abs(left_value - right_value) > _NUMERIC_EQUIVALENCE_TOLERANCE:
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
    existing = {
        (row.asset_id, row.ex_date, row.dividend_type): row
        for row in existing_result.scalars().all()
    }

    created = 0
    updated = 0
    unchanged = 0
    seen: dict[tuple[int, object, DividendType], tuple[str, dict]] = {}

    for collection in collections:
        asset = assets[(collection.ticker, collection.asset_type)]
        for source_collection in collection.sources:
            source = source_collection.source.strip().lower()
            for event in source_collection.normalized_rows:
                dividend_type = normalize_dividend_type(event.dividend_type)
                key = (asset.id, event.ex_date, dividend_type)
                values = _event_values(event, source)

                prior = seen.get(key)
                if prior is not None:
                    prior_source, prior_values = prior
                    conflicts = _conflicting_event_fields(prior_values, values)
                    if conflicts:
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
                    unchanged += 1
                    continue
                seen[key] = (source, values)

                row = existing.get(key)
                if row is None:
                    row = AssetDividend(
                        asset_id=asset.id,
                        ex_date=event.ex_date,
                        dividend_type=dividend_type,
                        **values,
                    )
                    db.add(row)
                    existing[key] = row
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
