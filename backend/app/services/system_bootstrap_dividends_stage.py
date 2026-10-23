"""Estágio canônico de Proventos globais do bootstrap do SGI v2."""
from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.integrations.b3_listed_companies import B3ListedCompaniesClient
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.asset_universe_membership import AssetUniverseMembership
from app.models.transaction import Transaction
from app.services.dividend_event_normalizer import parse_dividend_event
from app.services.dividend_history_seed_service import seed_full_dividend_history
from app.services.dividend_ticker_policy import is_event_ticker
from app.services.pre_prod_dividends_seed_contract import (
    validate_dividends_seed_identity,
)
from app.services.pre_prod_dividends_seed_providers import (
    StrictB3DividendProvider,
    StrictBrapiDividendProvider,
    StrictYahooDividendProvider,
    fetch_yahoo_dividend_history,
)
from app.services.pre_prod_dividends_seed_service import (
    run_pre_prod_dividends_seed,
)
from app.services.system_bootstrap_execution_context import (
    SystemBootstrapExecutionContext,
)

logger = logging.getLogger(__name__)

DIVIDENDS_BOOTSTRAP_AUTH_ENV = "SGI_BOOTSTRAP_ENABLE_DIVIDENDS"
DIVIDENDS_HISTORY_START_DATE = date(1970, 1, 1)
_ELIGIBLE_TYPES = (
    "ACAO",
    "FII",
    "ETF_NACIONAL",
    "BDR",
    "STOCK",
    "ETF_INTERNACIONAL",
)
_NATIONAL_TYPES = {"ACAO", "FII", "ETF_NACIONAL", "BDR"}

SeedRunner = Callable[..., Awaitable[object]]


class SystemBootstrapDividendsGateError(RuntimeError):
    """Indica que a execução real de Proventos continua bloqueada pela #226."""


def dividends_bootstrap_authorized() -> bool:
    """Retorna True somente para opt-in operacional explícito."""
    return os.getenv(DIVIDENDS_BOOTSTRAP_AUTH_ENV, "").strip().lower() == "true"


async def _collect_target_assets(db: AsyncSession) -> list[tuple[int, str, str]]:
    """Carrega ativos elegíveis presentes em transações ou no universo curado."""
    tx_tickers = select(func.upper(func.trim(Transaction.ticker))).distinct()
    uni_ids = select(AssetUniverseMembership.asset_id).distinct()

    rows = (
        await db.execute(
            select(Asset.id, Asset.ticker, Asset.asset_type)
            .where(
                Asset.asset_type.in_(_ELIGIBLE_TYPES),
                (func.upper(Asset.ticker).in_(tx_tickers))
                | (Asset.id.in_(uni_ids)),
            )
            .order_by(Asset.ticker)
        )
    ).all()

    result: list[tuple[int, str, str]] = []
    for asset_id, ticker, asset_type in rows:
        tk = str(ticker or "").strip().upper()
        at = str(asset_type or "").strip().upper()
        if not tk or " " in tk:
            continue
        if at in _NATIONAL_TYPES and not is_event_ticker(tk):
            continue
        result.append((int(asset_id), tk, at))
    return result


async def _upsert_parsed_events(
    db: AsyncSession,
    *,
    asset_id: int,
    source: str,
    raw_rows: tuple[dict, ...],
    start_date: date,
    end_date: date,
) -> tuple[int, int]:
    created = 0
    unchanged = 0
    for raw_row in raw_rows:
        parsed = parse_dividend_event(raw_row)
        if parsed is None:
            continue
        if not (start_date <= parsed.ex_date <= end_date):
            continue
        stmt = (
            pg_insert(AssetDividend)
            .values(
                asset_id=asset_id,
                record_date=parsed.record_date,
                ex_date=parsed.ex_date,
                payment_date=parsed.payment_date,
                approved_on=parsed.approved_on,
                value_per_unit=Decimal(str(round(parsed.value_per_unit, 8))),
                dividend_type=parsed.dividend_type,
                source=source,
                raw_payload=dict(raw_row),
            )
            .on_conflict_do_nothing()
        )
        res = await db.execute(stmt)
        if res.rowcount and res.rowcount > 0:
            created += 1
        else:
            unchanged += 1
    if created:
        await db.commit()
    return created, unchanged


async def _run_production_dividends_sync(
    *,
    db: AsyncSession,
    client: httpx.AsyncClient,
    start_date: date,
    end_date: date,
) -> str:
    targets = await _collect_target_assets(db)
    brapi_provider = StrictBrapiDividendProvider(client=client)
    b3_provider = StrictB3DividendProvider(
        client=B3ListedCompaniesClient(client=client)
    )

    total_created = 0
    total_unchanged = 0

    for asset_id, ticker, asset_type in targets:
        if asset_type in _NATIONAL_TYPES:
            try:
                brapi_res = await brapi_provider(ticker, asset_type)
                if brapi_res.rows:
                    c, u = await _upsert_parsed_events(
                        db,
                        asset_id=asset_id,
                        source="brapi",
                        raw_rows=brapi_res.rows,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    total_created += c
                    total_unchanged += u
            except Exception as exc:
                await db.rollback()
                logger.debug("[dividends_bootstrap] BRAPI skip %s: %s", ticker, exc)

            if asset_type in {"ACAO", "BDR"}:
                try:
                    b3_res = await b3_provider(ticker, asset_type)
                    if b3_res.rows:
                        c, u = await _upsert_parsed_events(
                            db,
                            asset_id=asset_id,
                            source="b3",
                            raw_rows=b3_res.rows,
                            start_date=start_date,
                            end_date=end_date,
                        )
                        total_created += c
                        total_unchanged += u
                except Exception as exc:
                    await db.rollback()
                    logger.debug("[dividends_bootstrap] B3 skip %s: %s", ticker, exc)

        try:
            yf_inserted = await seed_full_dividend_history(db, ticker, asset_type)
            total_created += yf_inserted
        except Exception as exc:
            await db.rollback()
            logger.debug("[dividends_bootstrap] YF skip %s: %s", ticker, exc)

    cov_row = (
        await db.execute(
            select(
                func.min(AssetDividend.ex_date),
                func.max(AssetDividend.ex_date),
                func.count(func.distinct(AssetDividend.asset_id)),
            )
        )
    ).one()
    first_ex, last_ex, assets_with_events = cov_row

    return (
        f"schema=pre-prod-dividends-seed.v2 "
        f"coverage={first_ex}..{last_ex} "
        f"assets_with_events={int(assets_with_events or 0)} "
        f"created={total_created} "
        f"updated=0 "
        f"unchanged={total_unchanged}"
    )


async def run_system_bootstrap_dividends_stage(
    context: SystemBootstrapExecutionContext,
    *,
    end_date: date | None = None,
    authorized: bool | None = None,
    seed_runner: SeedRunner = run_pre_prod_dividends_seed,
) -> str:
    """Reconstrói o catálogo global de Proventos sob o gate operacional #226."""

    is_authorized = (
        dividends_bootstrap_authorized() if authorized is None else authorized
    )
    if not is_authorized:
        raise SystemBootstrapDividendsGateError(
            "estágio de Proventos bloqueado pela #226; "
            f"configure {DIVIDENDS_BOOTSTRAP_AUTH_ENV}=true somente na janela autorizada"
        )

    validate_dividends_seed_identity(
        run_id=context.run_id,
        branch=context.branch,
        commit_sha=context.commit_sha,
    )
    target_end = end_date or datetime.now(UTC).date()

    async with (
        AsyncSessionLocal() as db,
        httpx.AsyncClient(timeout=30.0) as client,
    ):
        if seed_runner is run_pre_prod_dividends_seed:
            return await _run_production_dividends_sync(
                db=db,
                client=client,
                start_date=DIVIDENDS_HISTORY_START_DATE,
                end_date=target_end,
            )

        result = await seed_runner(
            run_id=context.run_id,
            branch=context.branch,
            commit_sha=context.commit_sha,
            start_date=DIVIDENDS_HISTORY_START_DATE,
            end_date=target_end,
            db=db,
            providers=(
                StrictBrapiDividendProvider(client=client),
                StrictB3DividendProvider(
                    client=B3ListedCompaniesClient(client=client)
                ),
                StrictYahooDividendProvider(
                    history_fetcher=fetch_yahoo_dividend_history
                ),
            ),
        )

    if not result.ok:
        raise RuntimeError("estágio de Proventos concluiu com achados bloqueantes")

    coverage = result.coverage
    persistence = result.global_persistence
    return (
        f"schema={result.schema_version} "
        f"coverage={coverage.first_ex_date}..{coverage.last_ex_date} "
        f"assets_with_events={coverage.assets_with_events} "
        f"created={persistence.get('created', 0)} "
        f"updated={persistence.get('updated', 0)} "
        f"unchanged={persistence.get('unchanged', 0)}"
    )
