from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Timestamped

IngestionStatus = str


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1)
    source_organization: str = Field(min_length=1)
    document_url: str | None = None
    crop: str | None = None
    disease: str | None = None
    region: str | None = None
    publication_date: date | None = None


class KnowledgeRead(KnowledgeCreate, Timestamped):
    id: UUID
    storage_path: str | None = None
    ingestion_status: str
    ingestion_error: str | None = None


class RetrievedChunk(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    metadata: dict = Field(default_factory=dict)
    similarity: float | None = None
    title: str
    source_organization: str | None = None
    document_url: str | None = None
    crop: str | None = None
    disease: str | None = None
    region: str | None = None
