from fastapi import APIRouter, Depends, Request

from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.help_chat import HelpChatQuestionRequest, HelpChatResponse
from app.services.help_document_chat_service import (
    get_help_document_chat_service,
)

router = APIRouter()


@router.post("/ask", response_model=HelpChatResponse)
@limiter.limit("10/minute")
async def ask_help_documentation(
    request: Request,
    payload: HelpChatQuestionRequest,
    _: User = Depends(get_current_user),
) -> HelpChatResponse:
    """Search user-facing documentation without accessing portfolio data."""
    service = get_help_document_chat_service()
    return await service.answer_async(payload.question)
