import json
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.corporate_event import CorporateEvent, CorporateEventType, CorporateEventStatus
from app.models.portfolio_position import PortfolioPosition
from app.models.transaction import Transaction, TransactionType
from app.models.asset import Asset
from app.integrations.brapi import get_dividends_and_events

logger = logging.getLogger(__name__)


def _parse_brapi_event_id(event: dict, ticker: str) -> str:
    return f"{ticker}_{event.get('type', '')}_{event.get('exDividendDate', '')}_{event.get('rate', '')}"


def _infer_event_type(event_type: str, ratio: float) -> CorporateEventType:
    if event_type == "SPLIT":
        return CorporateEventType.DESDOBRAMENTO if ratio > 1 else CorporateEventType.GRUPAMENTO
    return CorporateEventType.BONIFICACAO


async def sync_corporate_events_for_asset(
    db: AsyncSession, asset: Asset
) -> list[CorporateEvent]:
    ticker = asset.brapi_ticker or asset.ticker
    events = await get_dividends_and_events(ticker)
    new_events = []

    for raw in events:
        event_type_str = raw.get("type", "")
        if event_type_str not in ("SPLIT", "BONUS"):
            continue
        rate = float(raw.get("rate", 0) or 0)
        if rate <= 0:
            continue

        brapi_id = _parse_brapi_event_id(raw, ticker)
        existing = (await db.execute(
            select(CorporateEvent).where(CorporateEvent.brapi_event_id == brapi_id)
        )).scalar_one_or_none()
        if existing:
            continue

        ex_date_str = raw.get("exDividendDate")
        try:
            ex_date = date.fromisoformat(ex_date_str[:10]) if ex_date_str else date.today()
        except Exception:
            ex_date = date.today()

        event = CorporateEvent(
            asset_id=asset.id,
            event_type=_infer_event_type(event_type_str, rate),
            status=CorporateEventStatus.PENDENTE,
            event_date=ex_date,
            ratio=Decimal(str(rate)),
            brapi_event_id=brapi_id,
            raw_data=json.dumps(raw),
        )
        db.add(event)
        new_events.append(event)
        logger.info(f"[CorporateEvent] Novo: {ticker} {event.event_type} {ex_date} ratio={rate}")

    await db.flush()
    return new_events


async def apply_pending_events(db: AsyncSession) -> int:
    from datetime import datetime
    today = date.today()
    pending = (await db.execute(
        select(CorporateEvent).where(
            CorporateEvent.status == CorporateEventStatus.PENDENTE,
            CorporateEvent.event_date <= today,
        )
    )).scalars().all()

    applied_count = 0
    for event in pending:
        positions = (await db.execute(
            select(PortfolioPosition).where(
                PortfolioPosition.asset_id == event.asset_id,
                PortfolioPosition.quantity > 0,
            )
        )).scalars().all()

        for position in positions:
            try:
                await _apply_event_to_position(db, event, position)
            except Exception as e:
                logger.error(f"[CorporateEvent] Erro evento {event.id} posicao {position.id}: {e}")

        event.status = CorporateEventStatus.APLICADO
        event.applied_at = datetime.utcnow()
        applied_count += 1
        logger.info(f"[CorporateEvent] Evento {event.id} aplicado em {len(positions)} posicoes")

    await db.flush()
    return applied_count


async def _apply_event_to_position(
    db: AsyncSession,
    event: CorporateEvent,
    position: PortfolioPosition,
) -> None:
    qty = position.quantity
    avg = position.average_price
    ratio = event.ratio

    if event.event_type == CorporateEventType.DESDOBRAMENTO:
        position.quantity = (qty * ratio).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        position.average_price = (avg / ratio).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        tx_qty = position.quantity - qty
        tx_price = ratio
        tx_type = TransactionType.DESDOBRAMENTO

    elif event.event_type == CorporateEventType.GRUPAMENTO:
        position.quantity = (qty / ratio).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        position.average_price = (avg * ratio).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        tx_qty = qty - position.quantity
        tx_price = ratio
        tx_type = TransactionType.GRUPAMENTO

    elif event.event_type == CorporateEventType.BONIFICACAO:
        bonus_qty = (qty * ratio).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
        total_qty = qty + bonus_qty
        position.average_price = (qty * avg / total_qty).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
        position.quantity = total_qty
        tx_qty = bonus_qty
        tx_price = Decimal("0")
        tx_type = TransactionType.BONIFICACAO
    else:
        return

    db.add(Transaction(
        portfolio_id=position.portfolio_id,
        asset_id=event.asset_id,
        transaction_type=tx_type,
        date=event.event_date,
        quantity=tx_qty,
        unit_price=tx_price,
        total_cost=Decimal("0"),
        fees=Decimal("0"),
        notes=f"Aplicado automaticamente - Evento #{event.id} via BRAPI PRO",
        is_day_trade=False,
    ))
    await db.flush()
