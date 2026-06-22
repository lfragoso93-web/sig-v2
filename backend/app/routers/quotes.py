from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def quotes_not_implemented():
    """Placeholder — funcionalidade coberta por /api/v1/prices."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Este endpoint é coberto por /api/v1/prices. Router quotes reservado para uso interno.",
            "sprint": "N/A",
        },
    )
