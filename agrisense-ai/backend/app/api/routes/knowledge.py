from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.dependencies import get_knowledge_service
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/upload", response_model=KnowledgeRead, status_code=201)
def upload_knowledge(
    file: UploadFile = File(...),
    title: str = Form(...),
    source_organization: str = Form(...),
    document_url: str | None = Form(default=None),
    crop: str | None = Form(default=None),
    disease: str | None = Form(default=None),
    region: str | None = Form(default=None),
    publication_date: date | None = Form(default=None),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeRead:
    meta = KnowledgeCreate(
        title=title,
        source_organization=source_organization,
        document_url=document_url or None,
        crop=crop or None,
        disease=disease or None,
        region=region or None,
        publication_date=publication_date,
    )
    data = file.file.read()
    return service.ingest(file.filename or "document", file.content_type or "", data, meta)


@router.get("", response_model=list[KnowledgeRead])
def list_knowledge(
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[KnowledgeRead]:
    return service.list()


@router.delete("/{document_id}", status_code=204)
def delete_knowledge(
    document_id: UUID,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> Response:
    service.delete(document_id)
    return Response(status_code=204)
