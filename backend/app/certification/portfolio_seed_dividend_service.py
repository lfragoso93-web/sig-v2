"""Synthetic AssetDividend seed for certification issue #321/#303."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_asset_policy import (
    SyntheticAssetIdentity,
    assert_persisted_asset_identity,
    build_synthetic_asset_plan,
)
from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend_enums import DividendType

SYNTHETIC_DIVIDEND_SOURCE = "synthetic-certification"


@dataclass(frozen=True)
class SyntheticDividendSeedResult:
    created: int
    reused: int


@dataclass(frozen=True)
class SyntheticDividendEvent:
    identity: SyntheticAssetIdentity
    record_date: date
    ex_date: date
    payment_date: date
    dividend_type: DividendType
    value_per_unit: Decimal
    quantity: Decimal
    gross_amount: Decimal


def _parse_date(raw: object, *, field: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError) as exc:
        raise SyntheticSeedContractError(
            f"synthetic dividend {field} is invalid"
        ) from exc


def _expected_dividends(
    fixture: dict,
    plan: dict[str, SyntheticAssetIdentity],
) -> list[SyntheticDividendEvent]:
    raw_events = fixture.get("income_events")
    if not isinstance(raw_events, list) or not raw_events:
        raise SyntheticSeedContractError("synthetic income events contract is invalid")

    expected: list[SyntheticDividendEvent] = []
    seen: set[tuple[str, date, DividendType, date, Decimal]] = set()
    for raw in raw_events:
        if not isinstance(raw, dict):
            raise SyntheticSeedContractError("synthetic income event is invalid")
        source_ticker = str(raw.get("ticker") or "").strip().upper()
        identity = plan.get(source_ticker)
        if identity is None:
            raise SyntheticSeedContractError(
                f"income ticker {source_ticker} has no synthetic asset owner"
            )

        record_date = _parse_date(raw.get("record_date"), field="record_date")
        ex_date = _parse_date(raw.get("ex_date"), field="ex_date")
        payment_date = _parse_date(raw.get("payment_date"), field="payment_date")
        if not record_date < ex_date <= payment_date:
            raise SyntheticSeedContractError(
                f"synthetic dividend dates are inconsistent for {source_ticker}"
            )

        try:
            dividend_type = DividendType(str(raw.get("dividend_type") or ""))
        except ValueError as exc:
            raise SyntheticSeedContractError(
                f"synthetic dividend type is invalid for {source_ticker}"
            ) from exc

        value_per_unit = Decimal(str(raw.get("value_per_unit")))
        quantity = Decimal(str(raw.get("quantity")))
        gross_amount = Decimal(str(raw.get("gross_amount")))
        if value_per_unit <= 0 or quantity <= 0 or gross_amount <= 0:
            raise SyntheticSeedContractError(
                f"synthetic dividend amounts must be positive for {source_ticker}"
            )
        if quantity * value_per_unit != gross_amount:
            raise SyntheticSeedContractError(
                f"synthetic dividend gross amount is inconsistent for {source_ticker}"
            )
        if raw.get("source") != SYNTHETIC_DIVIDEND_SOURCE:
            raise SyntheticSeedContractError(
                f"synthetic dividend source is invalid for {source_ticker}"
            )

        economic_identity = (
            identity.ticker,
            ex_date,
            dividend_type,
            payment_date,
            value_per_unit,
        )
        if economic_identity in seen:
            raise SyntheticSeedContractError(
                f"duplicate synthetic dividend identity for {source_ticker}"
            )
        seen.add(economic_identity)
        expected.append(
            SyntheticDividendEvent(
                identity=identity,
                record_date=record_date,
                ex_date=ex_date,
                payment_date=payment_date,
                dividend_type=dividend_type,
                value_per_unit=value_per_unit,
                quantity=quantity,
                gross_amount=gross_amount,
            )
        )
    return expected


async def _load_owned_asset(
    db: AsyncSession,
    event: SyntheticDividendEvent,
) -> Asset:
    identity = event.identity
    result = await db.execute(
        select(Asset).where(
            Asset.ticker == identity.ticker,
            Asset.asset_type == identity.asset_type,
        )
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise SyntheticSeedContractError(
            f"synthetic dividend asset {identity.ticker} must be seeded before dividends"
        )
    assert_persisted_asset_identity(
        ticker=asset.ticker,
        asset_type=asset.asset_type,
        name=asset.name,
        provider=asset.provider,
        provider_symbol=asset.provider_symbol,
        provider_status=asset.provider_status,
        expected=identity,
    )
    return asset


def _is_canonical_existing(row: AssetDividend, expected: SyntheticDividendEvent) -> bool:
    return (
        row.record_date == expected.record_date
        and row.ex_date == expected.ex_date
        and row.payment_date == expected.payment_date
        and row.dividend_type == expected.dividend_type
        and Decimal(row.value_per_unit) == expected.value_per_unit
        and row.source == SYNTHETIC_DIVIDEND_SOURCE
        and row.approved_on is None
        and row.gross_value_per_unit is None
        and row.factor is None
        and row.complete_factor is None
        and row.isin_code is None
        and row.asset_issued is None
        and row.related_to is None
        and row.remarks is None
        and row.raw_payload is None
    )


async def seed_synthetic_dividends(db: AsyncSession) -> SyntheticDividendSeedResult:
    """Seed global synthetic dividend events without portfolio materialization."""
    fixture = load_portfolio_synthetic_certification_fixture()
    plan = build_synthetic_asset_plan(fixture)
    expected_events = _expected_dividends(fixture, plan)

    assets_by_ticker: dict[str, Asset] = {}
    events_by_asset_id: dict[int, list[SyntheticDividendEvent]] = {}
    for event in expected_events:
        asset = assets_by_ticker.get(event.identity.ticker)
        if asset is None:
            asset = await _load_owned_asset(db, event)
            assets_by_ticker[event.identity.ticker] = asset
        events_by_asset_id.setdefault(asset.id, []).append(event)

    existing_result = await db.execute(
        select(AssetDividend).where(
            AssetDividend.asset_id.in_(list(events_by_asset_id))
        )
    )
    existing_rows = list(existing_result.scalars().all())

    reused_keys: set[tuple[int, date, DividendType, date, Decimal]] = set()
    for row in existing_rows:
        candidates = events_by_asset_id.get(row.asset_id, [])
        matching = [
            event
            for event in candidates
            if (
                row.ex_date == event.ex_date
                and row.dividend_type == event.dividend_type
                and row.payment_date == event.payment_date
                and Decimal(row.value_per_unit) == event.value_per_unit
            )
        ]
        if len(matching) != 1 or not _is_canonical_existing(row, matching[0]):
            ticker = next(
                (
                    ticker
                    for ticker, asset in assets_by_ticker.items()
                    if asset.id == row.asset_id
                ),
                str(row.asset_id),
            )
            raise SyntheticSeedContractError(
                f"synthetic dividend collision for {ticker}; existing row is not canonical"
            )
        event = matching[0]
        key = (
            row.asset_id,
            event.ex_date,
            event.dividend_type,
            event.payment_date,
            event.value_per_unit,
        )
        if key in reused_keys:
            raise SyntheticSeedContractError(
                f"duplicate persisted synthetic dividend for {event.identity.ticker}"
            )
        reused_keys.add(key)

    created = 0
    for event in expected_events:
        asset = assets_by_ticker[event.identity.ticker]
        key = (
            asset.id,
            event.ex_date,
            event.dividend_type,
            event.payment_date,
            event.value_per_unit,
        )
        if key in reused_keys:
            continue
        db.add(
            AssetDividend(
                asset_id=asset.id,
                record_date=event.record_date,
                ex_date=event.ex_date,
                payment_date=event.payment_date,
                dividend_type=event.dividend_type,
                value_per_unit=event.value_per_unit,
                source=SYNTHETIC_DIVIDEND_SOURCE,
            )
        )
        created += 1

    if created:
        await db.commit()

    return SyntheticDividendSeedResult(created=created, reused=len(reused_keys))
