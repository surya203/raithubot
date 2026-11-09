from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_chat_service
from app.schemas.chat import ChatMessageRead, ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return service.reply(payload)


@router.get("/history/{conversation_id}", response_model=list[ChatMessageRead])
def chat_history(
    conversation_id: UUID,
    service: ChatService = Depends(get_chat_service),
) -> list[ChatMessageRead]:
    return service.history(conversation_id)
