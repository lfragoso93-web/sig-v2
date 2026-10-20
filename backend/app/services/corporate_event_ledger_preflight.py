"""Preflight read-only da base de transacoes para eventos corporativos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.models.corporate_event import CorporateEvent
from app.models.asset import Asset
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.corporate_action_position_reader import (
    load_global_corporate_actions_by_ticker,
    _component_bonus_projection_spec,
)
from app.services.snapshot_position_projection import project_transaction_timelines


@dataclass(frozen=True)
class LedgerTransactionPreflight:
    portfolio_id: int
    ticker: str
    as_of: date
    transaction_ids: tuple[int, ...]
    first_transaction_date: date | None
    last_transaction_date: date | None
    buy_quantity: Decimal
    sell_quantity: Decimal

    @property
    def net_quantity(self) -> Decimal:
        return self.buy_quantity - self.sell_quantity

    @property
    def transaction_count(self) -> int:
        return len(self.transaction_ids)


@dataclass(frozen=True)
class CorporateEventLedgerPreflight:
    event_id: int
    event_type: str
    quantity_factor: Decimal
    ledger: LedgerTransactionPreflight
    pre_event_projected_quantity: Decimal
    component_bonus_projection: dict[str, Any] | None = None

    @property
    def projected_net_quantity(self) -> Decimal:
        if self.component_bonus_projection is not None:
            source = self.ledger.ticker
            rows = self.component_bonus_projection.get("positions", {})
            if source in rows:
                return Decimal(str(rows[source]["quantity"]))
        return self.pre_event_projected_quantity * self.quantity_factor

    @property
    def projected_whole_quantity(self) -> Decimal:
        return self.projected_net_quantity.to_integral_value(rounding=ROUND_FLOOR)

    @property
    def projected_fractional_quantity(self) -> Decimal:
        return self.projected_net_quantity - self.projected_whole_quantity


@dataclass(frozen=True)
class CorporateEventLedgerPreflightReport:
    schema_version: str
    dry_run: bool
    database_writes_executed: int
    ready_for_execution: bool
    preflight: CorporateEventLedgerPreflight

    def to_dict(self) -> dict[str, Any]:
        ledger = self.preflight.ledger
        return {
            "schema_version": self.schema_version,
            "dry_run": self.dry_run,
            "database_writes_executed": self.database_writes_executed,
            "ready_for_execution": self.ready_for_execution,
            "projection_scope": (
                "COMPONENT_MULTI_ASSET_DRY_RUN"
                if self.preflight.component_bonus_projection is not None
                else "ADVISORY_FACTOR_ONLY"
            ),
            "projection_note": (
                "Posicoes e direitos por componente foram calculados em memoria; "
                "nenhuma transacao, posicao ou caixa foi persistido."
                if self.preflight.component_bonus_projection is not None
                else "Acoes anteriores elegiveis foram projetadas; o fator do evento-alvo "
                "e aplicado sem resolver sua politica de fracao, custo ou caixa."
            ),
            "event_id": self.preflight.event_id,
            "event_type": self.preflight.event_type,
            "quantity_factor": str(self.preflight.quantity_factor),
            "portfolio_id": ledger.portfolio_id,
            "ticker": ledger.ticker,
            "as_of": ledger.as_of.isoformat(),
            "transaction_ids": list(ledger.transaction_ids),
            "transaction_count": ledger.transaction_count,
            "first_transaction_date": (
                ledger.first_transaction_date.isoformat()
                if ledger.first_transaction_date is not None
                else None
            ),
            "last_transaction_date": (
                ledger.last_transaction_date.isoformat()
                if ledger.last_transaction_date is not None
                else None
            ),
            "buy_quantity": str(ledger.buy_quantity),
            "sell_quantity": str(ledger.sell_quantity),
            "net_quantity": str(ledger.net_quantity),
            "pre_event_projected_quantity": str(
                self.preflight.pre_event_projected_quantity
            ),
            "projected_net_quantity": str(
                self.preflight.projected_net_quantity
            ),
            "projected_whole_quantity": str(
                self.preflight.projected_whole_quantity
            ),
            "projected_fractional_quantity": str(
                self.preflight.projected_fractional_quantity
            ),
            "component_bonus_projection": self.preflight.component_bonus_projection,
        }


async def read_ledger_transaction_preflight(
    db: AsyncSession,
    *,
    portfolio_id: int,
    ticker: str,
    as_of: date,
) -> LedgerTransactionPreflight:
    """Lê transações até ``as_of`` sem alterar a sessão ou o banco."""

    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        raise ValueError("ticker e obrigatorio")

    transactions = await _load_portfolio_transactions(
        db,
        portfolio_id=portfolio_id,
        ticker=clean_ticker,
        as_of=as_of,
    )
    return _build_ledger_transaction_preflight(
        transactions=transactions,
        portfolio_id=portfolio_id,
        ticker=clean_ticker,
        as_of=as_of,
    )


async def _load_portfolio_transactions(
    db: AsyncSession,
    *,
    portfolio_id: int,
    ticker: str,
    as_of: date,
) -> tuple[Transaction, ...]:
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= as_of,
            func.upper(func.trim(Transaction.ticker)) == ticker,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    return tuple(result.scalars().all())


def _build_ledger_transaction_preflight(
    *,
    transactions: tuple[Transaction, ...],
    portfolio_id: int,
    ticker: str,
    as_of: date,
) -> LedgerTransactionPreflight:
    """Build audit totals from the same ordered rows used by the timeline."""

    buy_quantity = sum(
        (
            Decimal(str(transaction.quantity))
            for transaction in transactions
            if transaction.operation == OperationType.buy
        ),
        Decimal("0"),
    )
    sell_quantity = sum(
        (
            Decimal(str(transaction.quantity))
            for transaction in transactions
            if transaction.operation == OperationType.sell
        ),
        Decimal("0"),
    )

    return LedgerTransactionPreflight(
        portfolio_id=portfolio_id,
        ticker=ticker,
        as_of=as_of,
        transaction_ids=tuple(int(transaction.id) for transaction in transactions),
        first_transaction_date=(transactions[0].date if transactions else None),
        last_transaction_date=(transactions[-1].date if transactions else None),
        buy_quantity=buy_quantity,
        sell_quantity=sell_quantity,
    )


async def read_corporate_event_ledger_preflight(
    db: AsyncSession,
    event: CorporateEvent,
    *,
    portfolio_id: int | None = None,
    effective_date: date | None = None,
    component_bonus_evidence_type: str | None = None,
    component_bonus_evidence_reference: str | None = None,
) -> CorporateEventLedgerPreflight:
    """Lê a base do evento e calcula a quantidade projetada sem persistir."""

    effective_portfolio_id = (
        portfolio_id if portfolio_id is not None else event.portfolio_id
    )
    if effective_portfolio_id is None:
        raise ValueError(
            "preflight do evento exige portfolio_id explicito"
        )
    if effective_portfolio_id <= 0:
        raise ValueError("portfolio_id explicito deve ser positivo")

    is_component_bonus = (
        str(event.ticker or "").strip().upper() == "KLBN11"
        and str(event.event_type or "").strip().upper() == "BONIFICACAO"
    )

    try:
        quantity_factor = Decimal(str(event.quantity_factor))
    except (InvalidOperation, ValueError):
        raise ValueError("quantity_factor do evento deve ser decimal") from None
    if not quantity_factor.is_finite() or quantity_factor <= 0:
        raise ValueError("quantity_factor do evento deve ser positivo")

    event_date = effective_date or event.effective_date
    if event_date is None:
        raise ValueError("data efetiva do evento e obrigatoria para o preflight")

    component_bonus_spec = None
    if is_component_bonus:
        if not component_bonus_evidence_type or not component_bonus_evidence_reference:
            raise ValueError(
                "preflight de KLBN11 exige referencia da evidencia oficial multiativa"
            )
        component_bonus_spec = _component_bonus_projection_spec(
            event,
            SimpleNamespace(
                decision="MATCHED",
                evidence_type=component_bonus_evidence_type,
                evidence_reference=component_bonus_evidence_reference,
            ),
        )
        if component_bonus_spec is None:
            raise ValueError(
                "preflight de KLBN11 exige contrato por componente completo e compativel"
            )
        identity_tickers = {
            str(component_bonus_spec["unit_ticker"]).strip().upper(),
            *(
                str(component["ticker"]).strip().upper()
                for component in component_bonus_spec["components"]
            ),
        }
        catalog_result = await db.execute(
            select(Asset).where(
                func.upper(func.trim(Asset.ticker)).in_(identity_tickers)
            )
        )
        catalog = {
            (
                str(asset.ticker).strip().upper(),
                str(getattr(asset.asset_type, "value", asset.asset_type)).strip().upper(),
            ): str(asset.isin_code or "").strip().upper()
            for asset in catalog_result.scalars().all()
        }
        expected_identities = [
            (
                str(component_bonus_spec["unit_ticker"]).strip().upper(),
                str(component_bonus_spec["unit_asset_type"]).strip().upper(),
                str(component_bonus_spec["unit_isin_code"]).strip().upper(),
            ),
            *[
                (
                    str(component["ticker"]).strip().upper(),
                    str(component["asset_type"]).strip().upper(),
                    str(component["isin_code"]).strip().upper(),
                )
                for component in component_bonus_spec["components"]
            ],
        ]
        if any(
            catalog.get((ticker, asset_type)) != isin
            for ticker, asset_type, isin in expected_identities
        ):
            raise ValueError(
                "preflight de KLBN11 encontrou identidade de ativo divergente no catalogo"
            )
        if event.effective_date is not None and event.effective_date != event_date:
            raise ValueError("data efetiva do preflight diverge do evento")

    ticker = str(event.ticker).strip().upper()
    basis_date = (
        date.fromisoformat(str(component_bonus_spec["record_date"]))
        if component_bonus_spec is not None
        else event_date
    )
    projection_target_date = (
        date.fromisoformat(str(component_bonus_spec["credit_date"]))
        if component_bonus_spec is not None
        else event_date
    )
    transactions = await _load_portfolio_transactions(
        db,
        portfolio_id=int(effective_portfolio_id),
        ticker=ticker,
        as_of=projection_target_date,
    )
    ledger_transactions = tuple(
        transaction for transaction in transactions if transaction.date <= basis_date
    )
    ledger = _build_ledger_transaction_preflight(
        transactions=ledger_transactions,
        portfolio_id=int(effective_portfolio_id),
        ticker=ticker,
        as_of=basis_date,
    )
    actions = await load_global_corporate_actions_by_ticker(db, [ticker])
    event_source_id = str(
        event.source_event_id
        or event.brapi_event_id
        or f"corporate-event:{event.id}"
    )
    prior_actions = tuple(
        action
        for action in actions.get(ticker, ())
        if action.source_event_id != event_source_id
    )
    projection_actions = dict(actions)
    if component_bonus_spec is not None:
        candidate = NormalizedCorporateAction(
            source=str(event.source_provider or "catalog"),
            source_event_id=event_source_id,
            ticker=ticker,
            event_date=event_date,
            kind=CorporateActionKind.STOCK_BONUS,
            quantity_factor=quantity_factor,
            raw_payload={},
            component_bonus=component_bonus_spec,
        )
        projection_actions[ticker] = prior_actions + (candidate,)
    else:
        projection_actions[ticker] = prior_actions
    base_rows = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker={ticker: prior_actions},
        target_date=basis_date,
    )
    base_position = base_rows.get(ticker)
    pre_event_projected_quantity = (
        base_position[0].quantity if base_position is not None else Decimal(0)
    )
    projected_rows = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=projection_actions,
        target_date=projection_target_date,
    )
    projected = projected_rows.get(ticker)
    component_projection = None
    if component_bonus_spec is not None:
        component_projection = {
            "source_ticker": ticker,
            "record_date": str(component_bonus_spec["record_date"]),
            "credit_date": str(component_bonus_spec["credit_date"]),
            "settlement_date": str(component_bonus_spec["settlement_date"]),
            "positions": {
                projected_ticker: {
                    "quantity": str(projection.quantity),
                    "cost_basis_brl": str(projection.total_cost),
                    "asset_type": asset_type,
                }
                for projected_ticker, (projection, asset_type, _is_usd)
                in projected_rows.items()
                if projected_ticker == ticker
                or any(
                    projected_ticker
                    == str(component["ticker"]).strip().upper()
                    for component in component_bonus_spec["components"]
                )
            },
            "cash_rights": [
                {
                    "component": right.component,
                    "quantity": str(right.quantity),
                    "unit_price_brl": str(right.unit_price_brl),
                    "gross_amount_brl": str(right.gross_amount_brl),
                    "attributed_cost_brl": str(right.attributed_cost_brl),
                    "status": right.status,
                }
                for right in (
                    projected[0].component_bonus_cash_rights
                    if projected is not None
                    else ()
                )
            ],
        }
    return CorporateEventLedgerPreflight(
        event_id=int(event.id),
        event_type=str(event.event_type),
        quantity_factor=quantity_factor,
        ledger=ledger,
        pre_event_projected_quantity=pre_event_projected_quantity,
        component_bonus_projection=component_projection,
    )


async def build_corporate_event_ledger_preflight_report(
    db: AsyncSession,
    event: CorporateEvent,
    *,
    portfolio_id: int | None = None,
    effective_date: date | None = None,
    component_bonus_evidence_type: str | None = None,
    component_bonus_evidence_reference: str | None = None,
) -> CorporateEventLedgerPreflightReport:
    preflight = await read_corporate_event_ledger_preflight(
        db,
        event,
        portfolio_id=portfolio_id,
        effective_date=effective_date,
        component_bonus_evidence_type=component_bonus_evidence_type,
        component_bonus_evidence_reference=component_bonus_evidence_reference,
    )
    return CorporateEventLedgerPreflightReport(
        schema_version=(
            "corporate-event-ledger-preflight.v4"
            if preflight.component_bonus_projection is not None
            else "corporate-event-ledger-preflight.v3"
        ),
        dry_run=True,
        database_writes_executed=0,
        ready_for_execution=False,
        preflight=preflight,
    )
