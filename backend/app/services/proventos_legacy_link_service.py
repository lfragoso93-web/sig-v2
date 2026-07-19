"""Dry-run determinístico para vincular direitos legados a eventos globais."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendType
from app.services.dividend_type_service import normalize_dividend_type


class LegacyLinkStatus(str, Enum):
    MATCHED = "matched"
    NO_CANDIDATE = "no_candidate"
    AMBIGUOUS = "ambiguous"
    LEGACY_DIVERGENCE = "legacy_divergence"
    INVALID_IDENTITY = "invalid_identity"
    DUPLICATE_RIGHT = "duplicate_right"


@dataclass(frozen=True)
class LegacyLinkDecision:
    dividend_id: int
    portfolio_id: int
    ticker: str | None
    status: LegacyLinkStatus
    candidate_event_ids: tuple[int, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        result["candidate_event_ids"] = list(self.candidate_event_ids)
        return result


@dataclass(frozen=True)
class LegacyLinkDryRunReport:
    decisions: tuple[LegacyLinkDecision, ...]

    @property
    def scanned(self) -> int:
        return len(self.decisions)

    def count(self, status: LegacyLinkStatus) -> int:
        return sum(decision.status == status for decision in self.decisions)

    def to_dict(self, *, include_details: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "scanned": self.scanned,
            **{status.value: self.count(status) for status in LegacyLinkStatus},
        }
        if include_details:
            result["decisions"] = [decision.to_dict() for decision in self.decisions]
        return result


def _resolve_pair(canonical: Any, legacy: Any) -> tuple[Any, bool]:
    if canonical is not None and legacy is not None and canonical != legacy:
        return canonical, True
    return (canonical if canonical is not None else legacy), False


def _identity(
    right: Dividend,
) -> tuple[
    tuple[str, date, DividendType, Decimal] | None,
    date | None,
    str | None,
]:
    ticker = str(right.ticker or "").strip().upper()
    ex_date, ex_diverges = _resolve_pair(right.ex_date, right.date_ex)
    value, value_diverges = _resolve_pair(
        right.value_per_unit,
        right.value_per_share,
    )
    _, quantity_diverges = _resolve_pair(right.quantity, right.quantity_on_date)
    payment_date, payment_diverges = _resolve_pair(
        right.payment_date,
        right.date_pagamento,
    )

    # O legado usa data ex como fallback quando o pagamento era desconhecido.
    if right.payment_date is None and payment_date == ex_date:
        payment_date = None
        payment_diverges = False

    if ex_diverges or value_diverges or quantity_diverges or payment_diverges:
        return None, None, "canonical and legacy fields diverge"
    if not ticker or ex_date is None or value is None or not right.dividend_type:
        return None, None, (
            "ticker, ex_date, dividend_type and value_per_unit are required"
        )

    dividend_type = normalize_dividend_type(right.dividend_type)
    raw_type = str(right.dividend_type).replace("DividendType.", "").strip().upper()
    if dividend_type == DividendType.OUTROS and raw_type != DividendType.OUTROS.value:
        return None, None, "dividend_type cannot be normalized safely"

    return (
        (ticker, ex_date, dividend_type, Decimal(str(value))),
        payment_date,
        None,
    )


async def dry_run_legacy_dividend_links(db: AsyncSession) -> LegacyLinkDryRunReport:
    """Classifica vínculos possíveis sem modificar direitos ou eventos."""
    with db.no_autoflush:
        rights = (
            await db.execute(
                select(Dividend)
                .where(Dividend.asset_dividend_id.is_(None))
                .order_by(Dividend.id)
            )
        ).scalars().all()

        tickers = sorted(
            {str(right.ticker).strip().upper() for right in rights if right.ticker}
        )
        event_rows = []
        if tickers:
            event_rows = (
                await db.execute(
                    select(Asset.ticker, AssetDividend)
                    .join(AssetDividend, AssetDividend.asset_id == Asset.id)
                    .where(func.upper(Asset.ticker).in_(tickers))
                )
            ).all()

        linked_rows = (
            await db.execute(
                select(Dividend.portfolio_id, Dividend.asset_dividend_id)
                .where(Dividend.asset_dividend_id.is_not(None))
            )
        ).all()
        linked_pairs = {(portfolio_id, event_id) for portfolio_id, event_id in linked_rows}

    events_by_identity: dict[
        tuple[str, date, DividendType, Decimal], list[AssetDividend]
    ] = {}
    for ticker, event in event_rows:
        identity = (
            str(ticker).strip().upper(),
            event.ex_date,
            normalize_dividend_type(event.dividend_type),
            Decimal(str(event.value_per_unit)),
        )
        events_by_identity.setdefault(identity, []).append(event)

    decisions: list[LegacyLinkDecision] = []
    provisional_matches: dict[tuple[int, int], list[int]] = {}
    for right in rights:
        identity, payment_date, identity_error = _identity(right)
        if identity is None:
            status = (
                LegacyLinkStatus.LEGACY_DIVERGENCE
                if identity_error == "canonical and legacy fields diverge"
                else LegacyLinkStatus.INVALID_IDENTITY
            )
            decisions.append(
                LegacyLinkDecision(
                    right.id,
                    right.portfolio_id,
                    right.ticker,
                    status,
                    reason=identity_error,
                )
            )
            continue

        candidates = events_by_identity.get(identity, [])
        if payment_date:
            candidates = [
                event
                for event in candidates
                if event.payment_date is None or event.payment_date == payment_date
            ]
        candidate_ids = tuple(sorted(event.id for event in candidates))

        if not candidates:
            decisions.append(
                LegacyLinkDecision(
                    right.id,
                    right.portfolio_id,
                    right.ticker,
                    LegacyLinkStatus.NO_CANDIDATE,
                    reason="no global event matches the strict identity",
                )
            )
        elif len(candidates) > 1:
            decisions.append(
                LegacyLinkDecision(
                    right.id,
                    right.portfolio_id,
                    right.ticker,
                    LegacyLinkStatus.AMBIGUOUS,
                    candidate_ids,
                    "more than one global event matches the strict identity",
                )
            )
        else:
            event_id = candidates[0].id
            pair = (right.portfolio_id, event_id)
            provisional_matches.setdefault(pair, []).append(right.id)
            decisions.append(
                LegacyLinkDecision(
                    right.id,
                    right.portfolio_id,
                    right.ticker,
                    LegacyLinkStatus.MATCHED,
                    (event_id,),
                )
            )

    duplicate_ids = {
        right_id
        for pair, right_ids in provisional_matches.items()
        if pair in linked_pairs or len(right_ids) > 1
        for right_id in right_ids
    }
    if duplicate_ids:
        decisions = [
            LegacyLinkDecision(
                decision.dividend_id,
                decision.portfolio_id,
                decision.ticker,
                LegacyLinkStatus.DUPLICATE_RIGHT,
                decision.candidate_event_ids,
                "portfolio already has or would have another right for this event",
            )
            if decision.dividend_id in duplicate_ids
            else decision
            for decision in decisions
        ]

    return LegacyLinkDryRunReport(tuple(decisions))
