"""Estágio canônico de Proventos globais do bootstrap do SGI v2.

A integração existe no orquestrador global, mas a execução real permanece
explicitamente opt-in enquanto a Issue #226 não estiver operacionalmente
liberada. O estágio reutiliza integralmente o contrato
``pre-prod-dividends-seed.v2`` e nunca materializa direitos por carteira.
"""
from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime

import httpx

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_dividends_seed_contract import (
    validate_dividends_seed_identity,
)
from app.services.pre_prod_dividends_seed_providers import (
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

DIVIDENDS_BOOTSTRAP_AUTH_ENV = "SGI_BOOTSTRAP_ENABLE_DIVIDENDS"
DIVIDENDS_HISTORY_START_DATE = date(1970, 1, 1)

SeedRunner = Callable[..., Awaitable[object]]


class SystemBootstrapDividendsGateError(RuntimeError):
    """Indica que a execução real de Proventos continua bloqueada pela #226."""


def dividends_bootstrap_authorized() -> bool:
    """Retorna True somente para opt-in operacional explícito."""

    return os.getenv(DIVIDENDS_BOOTSTRAP_AUTH_ENV, "").strip().lower() == "true"


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
        result = await seed_runner(
            run_id=context.run_id,
            branch=context.branch,
            commit_sha=context.commit_sha,
            start_date=DIVIDENDS_HISTORY_START_DATE,
            end_date=target_end,
            db=db,
            providers=(
                StrictBrapiDividendProvider(client=client),
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
