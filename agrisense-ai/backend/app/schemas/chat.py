from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.advisory import EvidenceItem
from app.schemas.common import Timestamped


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None
    crop_id: UUID | None = None

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Message cannot be blank.")
        return text


class ChatAnswer(BaseModel):
    answer: str
    references: list[EvidenceItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ChatMessageRead(Timestamped):
    id: UUID
    conversation_id: UUID
    crop_id: UUID | None = None
    role: str
    message: str
    metadata: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: ChatMessageRead
    answer: ChatAnswer
