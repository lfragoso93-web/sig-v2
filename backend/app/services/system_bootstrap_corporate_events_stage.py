"""Estágio canônico de eventos corporativos globais do bootstrap do SGI v2.

A execução permanece explicitamente opt-in enquanto o bootstrap certificado
não estiver operacionalmente liberado. O estágio lê somente o catálogo de
ativos persistido e delega toda coleta/persistência ao motor canônico de
eventos corporativos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset
from app.services.corporate_event_service import sync_corporate_events_for_asset
from app.services.system_bootstrap_execution_context import (
    SystemBootstrapExecutionContext,
)

CORPORATE_EVENTS_BOOTSTRAP_AUTH_ENV = "SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS"
CORPORATE_EVENTS_ADVISORY_LOCK_KEY = 254_001
SUPPORTED_CORPORATE_EVENT_ASSET_TYPES = ("ACAO", "BDR", "ETF_NACIONAL")


class SystemBootstrapCorporateEventsGateError(RuntimeError):
    """Indica que a execução real de eventos corporativos não foi autorizada."""


@dataclass(frozen=True)
class CorporateEventsStageReport:
    assets_processed: int
    events_created: int
    assets_skipped: int

    def to_detail(self) -> str:
        return (
            f"processed={self.assets_processed} created={self.events_created} "
            f"skipped={self.assets_skipped}"
        )


def corporate_events_bootstrap_authorized() -> bool:
    """Retorna True somente para opt-in operacional explícito."""

    return (
        os.getenv(CORPORATE_EVENTS_BOOTSTRAP_AUTH_ENV, "").strip().lower()
        == "true"
    )


async def run_system_bootstrap_corporate_events_stage(
    context: SystemBootstrapExecutionContext,
    *,
    authorized: bool | None = None,
) -> str:
    """Coleta eventos globais com gate, lock e transação única do estágio."""

    is_authorized = (
        corporate_events_bootstrap_authorized() if authorized is None else authorized
    )
    if not is_authorized:
        raise SystemBootstrapCorporateEventsGateError(
            "estágio de eventos corporativos bloqueado; "
            f"configure {CORPORATE_EVENTS_BOOTSTRAP_AUTH_ENV}=true somente na janela autorizada"
        )

    async with AsyncSessionLocal() as db:
        try:
            await db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": CORPORATE_EVENTS_ADVISORY_LOCK_KEY},
            )
            assets_result = await db.execute(
                select(Asset)
                .where(Asset.asset_type.in_(SUPPORTED_CORPORATE_EVENT_ASSET_TYPES))
                .order_by(Asset.id)
            )
            assets = tuple(assets_result.scalars().all())

            events_created = 0
            for asset in assets:
                created = await sync_corporate_events_for_asset(db, asset)
                events_created += len(created)

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    report = CorporateEventsStageReport(
        assets_processed=len(assets),
        events_created=events_created,
        assets_skipped=0,
    )
    return report.to_detail()
