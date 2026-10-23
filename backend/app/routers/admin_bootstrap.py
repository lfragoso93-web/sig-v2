"""SuperAdmin surface for the single SGI system bootstrap."""
from __future__ import annotations

import logging
import os
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.routers.admin import require_superadmin
from app.services.system_bootstrap_execution_context import (
    BOOTSTRAP_COMMIT_SHA_ENV,
    DEFAULT_BOOTSTRAP_COMMIT_SHA,
)
from app.services.system_bootstrap_service import (
    BOOTSTRAP_SCHEMA_VERSION,
    CANONICAL_BOOTSTRAP_STAGES,
)
from app.services.system_bootstrap_trigger_service import (
    bootstrap_launch_reserved,
    reserve_system_bootstrap_launch,
    run_reserved_system_bootstrap,
)
from app.services.system_readiness_service import get_bootstrap_readiness
from app.services.user_test_readiness_service import (
    build_user_test_readiness,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-bootstrap"])


class BootstrapTriggerRequest(BaseModel):
    """Payload para acionamento do bootstrap pelo SuperAdmin."""

    commit_sha: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40}$",
        description="SHA opcional de 40 dígitos hexadecimais",
    )
    stages: list[str] | None = Field(
        default=None,
        description="Lista opcional de IDs de etapas para execução seletiva",
    )


@router.get("/bootstrap/status")
async def admin_system_bootstrap_status(
    _: User = Depends(require_superadmin),
):
    readiness = get_bootstrap_readiness()
    return {
        **readiness.to_dict(),
        "launch_reserved": bootstrap_launch_reserved(),
    }


@router.get("/bootstrap/user-test-readiness")
async def admin_user_test_readiness(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    report = await build_user_test_readiness(db)
    return report.to_dict()


@router.post("/bootstrap", status_code=status.HTTP_202_ACCEPTED)
async def admin_trigger_system_bootstrap(
    background_tasks: BackgroundTasks,
    payload: BootstrapTriggerRequest | None = None,
    commit_sha: str | None = Query(
        None,
        pattern=r"^[0-9a-f]{40}$",
        description="SHA opcional que identifica esta execução",
    ),
    stages: list[str] | None = Query(
        None,
        description="Lista opcional de IDs de etapas para execução seletiva",
    ),
    _: User = Depends(require_superadmin),
):
    actual_sha = (
        (payload.commit_sha if payload and payload.commit_sha else None)
        or commit_sha
        or os.getenv(BOOTSTRAP_COMMIT_SHA_ENV, "").strip().lower()
        or getattr(settings, "APP_COMMIT_SHA", "").strip().lower()
        or DEFAULT_BOOTSTRAP_COMMIT_SHA
    )
    if len(actual_sha) != 40:
        actual_sha = DEFAULT_BOOTSTRAP_COMMIT_SHA

    actual_stages = (
        payload.stages if payload and payload.stages else None
    ) or stages

    if actual_stages:
        valid_ids = {s.id for s in CANONICAL_BOOTSTRAP_STAGES}
        unknown = set(actual_stages) - valid_ids
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Etapas desconhecidas: {sorted(unknown)}. "
                    f"Válidas: {sorted(valid_ids)}"
                ),
            )

    if not reserve_system_bootstrap_launch(actual_sha, actual_stages):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="bootstrap global ja reservado ou em execucao",
        )

    background_tasks.add_task(run_reserved_system_bootstrap)
    return {
        "status": "accepted",
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "commit_sha": actual_sha,
        "stages": actual_stages,
        "detail": (
            f"bootstrap seletivo ({len(actual_stages)} etapas) reservado"
            if actual_stages
            else "bootstrap global reservado para execucao"
        ),
    }
