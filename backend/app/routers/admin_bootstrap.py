"""SuperAdmin surface for the single SGI system bootstrap."""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.models.user import User
from app.routers.admin import require_superadmin
from app.services.system_bootstrap_trigger_service import (
    bootstrap_launch_reserved,
    reserve_system_bootstrap_launch,
    run_reserved_system_bootstrap,
)
from app.services.system_readiness_service import get_bootstrap_readiness

router = APIRouter(tags=["admin-bootstrap"])


@router.get("/bootstrap/status")
async def admin_system_bootstrap_status(
    _: User = Depends(require_superadmin),
):
    readiness = get_bootstrap_readiness()
    return {
        **readiness.to_dict(),
        "launch_reserved": bootstrap_launch_reserved(),
    }


@router.post("/bootstrap", status_code=status.HTTP_202_ACCEPTED)
async def admin_trigger_system_bootstrap(
    background_tasks: BackgroundTasks,
    _: User = Depends(require_superadmin),
):
    if not reserve_system_bootstrap_launch():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="bootstrap global ja reservado ou em execucao",
        )

    background_tasks.add_task(run_reserved_system_bootstrap)
    return {
        "status": "accepted",
        "schema_version": "system-bootstrap.v1",
        "detail": "bootstrap global reservado para execucao",
    }
