"""Gerenciamento de liquidacoes manuais de fracoes corporativas por carteira."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import date as DateType
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.core.clock import SYSTEM_CLOCK, Clock
from app.models.portfolio_corporate_fraction_settlement import (
    PortfolioCorporateFractionSettlement,
)
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.services.corporate_action_engine import NormalizedCorporateAction
from app.services.corporate_event_fractional_resolution import (
    PORTFOLIO_USER_CONFIRMED_AUCTION,
    FractionalResolution,
    FractionalResolutionPolicy,
)

READ_PORTFOLIO_CORPORATE_FRACTIONS = "portfolio:corporate-lifecycle:read"
WRITE_PORTFOLIO_CORPORATE_FRACTIONS = "portfolio:corporate-fractions:write"


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_positive_component_fraction(right: Mapping[str, Any]) -> bool:
    if right.get("has_fractional_entitlement") is False:
        return False
    components = right.get("components")
    if isinstance(components, Sequence) and not isinstance(components, (str, bytes)):
        return any(
            Decimal(str(comp.get("fractional_quantity") or 0)) > 0
            for comp in components
            if isinstance(comp, Mapping)
        )
    return bool(right.get("has_fractional_entitlement", False))


def _result_rows(result: Any) -> list[Any]:
    scalars_fn = getattr(result, "scalars", None)
    if not callable(scalars_fn):
        return []
    scalars = scalars_fn()
    all_fn = getattr(scalars, "all", None)
    if not callable(all_fn):
        return []
    rows = all_fn()
    return list(rows) if isinstance(rows, Iterable) else []


async def load_portfolio_fraction_settlement_map(
    db: AsyncSession,
    *,
    portfolio_id: int,
    source_event_ids: set[str] | None = None,
) -> dict[str, PortfolioCorporateFractionSettlement]:
    """Carrega liquidacoes confirmadas da carteira indexadas por ``source_event_id``."""
    stmt = select(PortfolioCorporateFractionSettlement).where(
        PortfolioCorporateFractionSettlement.portfolio_id == portfolio_id,
    )
    if source_event_ids is not None:
        normalized_ids = sorted({str(eid).strip() for eid in source_event_ids if str(eid).strip()})
        if not normalized_ids:
            return {}
        stmt = stmt.where(
            PortfolioCorporateFractionSettlement.source_event_id.in_(normalized_ids)
        )

    try:
        result = await db.execute(stmt)
    except StopAsyncIteration:
        return {}
    return {
        row.source_event_id: row
        for row in _result_rows(result)
        if isinstance(row, PortfolioCorporateFractionSettlement)
    }


async def apply_portfolio_corporate_fraction_settlements(
    db: AsyncSession,
    *,
    portfolio_id: int,
    actions_by_ticker: Mapping[str, Sequence[NormalizedCorporateAction]],
) -> dict[str, tuple[NormalizedCorporateAction, ...]]:
    """Aplica sobreposicao local de leilao confirmado sem mutar o catalogo global."""
    if not actions_by_ticker:
        return {}

    source_event_ids = {
        action.source_event_id
        for actions in actions_by_ticker.values()
        for action in actions
        if getattr(action, "source_event_id", None)
    }
    settlements = await load_portfolio_fraction_settlement_map(
        db,
        portfolio_id=portfolio_id,
        source_event_ids=source_event_ids,
    )
    if not settlements:
        return {ticker: tuple(actions) for ticker, actions in actions_by_ticker.items()}

    overlaid: dict[str, tuple[NormalizedCorporateAction, ...]] = {}
    for ticker, actions in actions_by_ticker.items():
        next_actions: list[NormalizedCorporateAction] = []
        for action in actions:
            settlement = settlements.get(action.source_event_id)
            if settlement is None:
                next_actions.append(action)
                continue
            prior = action.fractional_resolution
            next_resolution = FractionalResolution(
                policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
                fractional_quantity=(prior.fractional_quantity if prior is not None else None),
                settlement_gross_amount_brl=Decimal(str(settlement.gross_amount_brl)),
                settlement_date=settlement.settlement_date,
                cash_treatment=PORTFOLIO_USER_CONFIRMED_AUCTION,
                ledger_basis=(prior.ledger_basis if prior is not None else None),
                fraction_is_post_event_quantity=bool(
                    prior is not None and prior.fraction_is_post_event_quantity
                ),
            )
            next_actions.append(replace(action, fractional_resolution=next_resolution))
        overlaid[ticker] = tuple(next_actions)
    return overlaid


async def list_portfolio_corporate_fraction_settlements(
    db: AsyncSession,
    *,
    access: PortfolioAccessContext,
) -> list[dict[str, Any]]:
    """Lista liquidacoes manuais salvas na carteira com settlement_date e observacoes."""
    await get_accessible_portfolio(
        db,
        access,
        required_permission=READ_PORTFOLIO_CORPORATE_FRACTIONS,
    )
    settlements = await load_portfolio_fraction_settlement_map(
        db,
        portfolio_id=access.portfolio_id,
    )
    return [
        {
            "id": int(row.id),
            "portfolio_id": int(row.portfolio_id),
            "source_event_id": row.source_event_id,
            "ticker": row.ticker,
            "gross_amount_brl": Decimal(str(row.gross_amount_brl)),
            "settlement_date": row.settlement_date,
            "notes": row.notes,
            "cash_treatment": PORTFOLIO_USER_CONFIRMED_AUCTION,
            "event_date": row.settlement_date or row.created_at.date(),
        }
        for row in sorted(settlements.values(), key=lambda r: (r.source_event_id,))
    ]


async def upsert_portfolio_corporate_fraction_settlement(
    db: AsyncSession,
    *,
    access: PortfolioAccessContext,
    source_event_id: str,
    gross_amount_brl: Decimal,
    settlement_date: DateType | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Registra ou atualiza o valor recebido no leilao de fracoes na carteira."""
    from app.services.portfolio_asset_corporate_lifecycle_service import (
        READ_PORTFOLIO_CORPORATE_LIFECYCLE,
        load_portfolio_pending_corporate_fractions,
    )
    from app.services.portfolio_corporate_rights_service import (
        load_portfolio_corporate_rights,
    )

    await get_accessible_portfolio(
        db,
        access,
        required_permission=WRITE_PORTFOLIO_CORPORATE_FRACTIONS,
    )
    normalized_event_id = source_event_id.strip()
    if not normalized_event_id:
        raise ValueError("source_event_id e obrigatorio")
    if not gross_amount_brl.is_finite() or gross_amount_brl < 0:
        raise ValueError("gross_amount_brl deve ser finito e nao negativo")

    read_access = (
        PortfolioAccessContext.for_user(
            user_id=access.user_id,
            portfolio_id=access.portfolio_id,
            permissions=frozenset({READ_PORTFOLIO_CORPORATE_LIFECYCLE}),
        )
        if access.user_id is not None
        else PortfolioAccessContext.for_system(
            portfolio_id=access.portfolio_id,
            permissions=frozenset({READ_PORTFOLIO_CORPORATE_LIFECYCLE}),
            purpose="corporate_fraction_settlement_upsert",
        )
    )

    lifecycle = await load_portfolio_pending_corporate_fractions(db, access=read_access)
    matched_fraction = next(
        (
            item
            for item in lifecycle
            if item.get("source_event_id") == normalized_event_id
            and item.get("fractional_quantity") is not None
            and Decimal(str(item["fractional_quantity"])) > 0
        ),
        None,
    )
    matched_right: dict[str, Any] | None = None
    if matched_fraction is None:
        rights = await load_portfolio_corporate_rights(db, access=read_access)
        matched_right = next(
            (
                item
                for item in rights
                if item.get("source_event_id") == normalized_event_id
                and Decimal(str(item.get("calculated_gross_amount_brl") or 0)) >= 0
                and _has_positive_component_fraction(item)
            ),
            None,
        )

    if matched_fraction is None and matched_right is None:
        raise LookupError(
            "Evento corporativo com fracao elegivel nao encontrado nesta carteira."
        )

    target_ticker = str(
        (matched_fraction or matched_right or {}).get("ticker") or ""
    ).strip().upper()
    target_event_date = (
        matched_fraction["event_date"]
        if matched_fraction is not None
        else matched_right["record_date"]  # type: ignore[index]
    )

    existing_result = await db.execute(
        select(PortfolioCorporateFractionSettlement).where(
            PortfolioCorporateFractionSettlement.portfolio_id == access.portfolio_id,
            PortfolioCorporateFractionSettlement.source_event_id == normalized_event_id,
        )
    )
    record = existing_result.scalar_one_or_none()
    quantized_gross = gross_amount_brl.quantize(Decimal("0.01"))
    cleaned_notes = _clean_text(notes)
    effective_settlement_date = settlement_date or (
        matched_right.get("settlement_date") if matched_right is not None else target_event_date
    )

    if record is None:
        record = PortfolioCorporateFractionSettlement(
            portfolio_id=access.portfolio_id,
            source_event_id=normalized_event_id,
            ticker=target_ticker,
            gross_amount_brl=quantized_gross,
            settlement_date=effective_settlement_date,
            notes=cleaned_notes,
            created_by_user_id=access.user_id,
        )
        db.add(record)
    else:
        record.ticker = target_ticker
        record.gross_amount_brl = quantized_gross
        record.settlement_date = effective_settlement_date
        record.notes = cleaned_notes

    await db.commit()
    await db.refresh(record)

    return {
        "id": int(record.id),
        "portfolio_id": int(record.portfolio_id),
        "source_event_id": record.source_event_id,
        "ticker": record.ticker,
        "gross_amount_brl": Decimal(str(record.gross_amount_brl)),
        "settlement_date": record.settlement_date,
        "notes": record.notes,
        "cash_treatment": PORTFOLIO_USER_CONFIRMED_AUCTION,
        "event_date": target_event_date,
    }


async def delete_portfolio_corporate_fraction_settlement(
    db: AsyncSession,
    *,
    access: PortfolioAccessContext,
    source_event_id: str,
    clock: Clock = SYSTEM_CLOCK,
) -> DateType:
    """Remove liquidacao manual informada, retornando a fracao ao status anterior."""
    await get_accessible_portfolio(
        db,
        access,
        required_permission=WRITE_PORTFOLIO_CORPORATE_FRACTIONS,
    )
    normalized_event_id = source_event_id.strip()
    existing_result = await db.execute(
        select(PortfolioCorporateFractionSettlement).where(
            PortfolioCorporateFractionSettlement.portfolio_id == access.portfolio_id,
            PortfolioCorporateFractionSettlement.source_event_id == normalized_event_id,
        )
    )
    record = existing_result.scalar_one_or_none()
    if record is None:
        raise LookupError(
            "Liquidacao manual de fracao nao encontrada nesta carteira."
        )
    rebuild_from = record.settlement_date or clock.today()
    await db.delete(record)
    await db.commit()
    return rebuild_from


async def reconcile_portfolio_corporate_fraction_settlements(
    db: AsyncSession,
    *,
    portfolio_id: int,
    tickers: Iterable[str] | None = None,
    commit: bool = False,
    clock: Clock = SYSTEM_CLOCK,
) -> tuple[list[str], DateType | None]:
    """Remove liquidacoes manuais cuja fracao elegivel deixou de existir na carteira."""
    stmt = select(PortfolioCorporateFractionSettlement).where(
        PortfolioCorporateFractionSettlement.portfolio_id == portfolio_id,
    )
    if tickers is not None:
        normalized_tickers = sorted(
            {str(t).strip().upper() for t in tickers if str(t).strip()}
        )
        if not normalized_tickers:
            return [], None
        stmt = stmt.where(
            PortfolioCorporateFractionSettlement.ticker.in_(normalized_tickers)
        )

    try:
        rows_result = await db.execute(stmt)
    except StopAsyncIteration:
        return [], None

    settlements = [
        row
        for row in _result_rows(rows_result)
        if isinstance(row, PortfolioCorporateFractionSettlement)
    ]
    if not settlements:
        return [], None

    from app.models.transaction import Transaction
    from app.services.corporate_action_position_reader import (
        load_global_corporate_actions_by_ticker,
    )
    from app.services.portfolio_asset_corporate_lifecycle_service import (
        READ_PORTFOLIO_CORPORATE_LIFECYCLE,
    )
    from app.services.portfolio_corporate_rights_service import (
        load_portfolio_corporate_rights,
    )
    from app.services.snapshot_position_projection import (
        project_transaction_timelines,
    )

    affected_tickers = sorted(
        {str(row.ticker).strip().upper() for row in settlements if row.ticker}
    )
    eligible_event_ids: set[str] = set()

    if affected_tickers:
        try:
            tx_result = await db.execute(
                select(Transaction)
                .where(
                    Transaction.portfolio_id == portfolio_id,
                    func.upper(func.trim(Transaction.ticker)).in_(affected_tickers),
                )
                .order_by(Transaction.date.asc(), Transaction.id.asc())
            )
            transactions = [
                tx
                for tx in _result_rows(tx_result)
                if hasattr(tx, "ticker") and hasattr(tx, "date")
            ]
        except StopAsyncIteration:
            return [], None

        if transactions:
            actions_by_ticker = await load_global_corporate_actions_by_ticker(
                db,
                affected_tickers,
            )
            timelines = project_transaction_timelines(
                transactions=transactions,
                actions_by_ticker=actions_by_ticker,
                target_date=clock.today(),
            )
            for projection, _asset_type, _is_usd in timelines.values():
                for pending in projection.pending_corporate_action_fractions:
                    if Decimal(str(pending.fractional_quantity)) > 0:
                        eligible_event_ids.add(pending.source_event_id)
                for flow in projection.corporate_action_cash_flows:
                    if Decimal(str(flow.fractional_quantity)) > 0:
                        eligible_event_ids.add(flow.source_event_id)

            rights_access = PortfolioAccessContext.for_system(
                portfolio_id=portfolio_id,
                permissions=frozenset({READ_PORTFOLIO_CORPORATE_LIFECYCLE}),
                purpose="corporate_fraction_settlement_reconcile",
            )
            rights = await load_portfolio_corporate_rights(
                db,
                access=rights_access,
                clock=clock,
            )
            for right in rights:
                if _has_positive_component_fraction(right):
                    eligible_event_ids.add(str(right["source_event_id"]))

    stale = [
        row for row in settlements if row.source_event_id not in eligible_event_ids
    ]
    if not stale:
        return [], None

    stale_ids = [row.source_event_id for row in stale]
    dates = [
        row.settlement_date or row.created_at.date()
        for row in stale
        if (row.settlement_date is not None or row.created_at is not None)
    ]
    earliest_date = min(dates) if dates else None

    for row in stale:
        await db.delete(row)
    if commit:
        await db.commit()
    else:
        await db.flush()
    return stale_ids, earliest_date
