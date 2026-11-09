from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import UUID

from app.errors import AppError, IntegrationError
from app.knowledge.chunking import chunk_pages
from app.knowledge.extract import extract_pages
from app.repositories.records import RecordsRepository, _vector_literal
from app.schemas.knowledge import KnowledgeCreate, KnowledgeRead
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

MAX_BYTES = 20 * 1024 * 1024
MAX_CHUNKS = 200


class KnowledgeService:
    def __init__(self, records: RecordsRepository, llm: LLMService) -> None:
        self.records = records
        self.llm = llm

    def list(self) -> list[KnowledgeRead]:
        return [KnowledgeRead.model_validate(row) for row in self.records.list_documents()]

    def delete(self, document_id: UUID) -> None:
        document = self.records.delete_document(document_id)
        path = document.get("storage_path")
        if path:
            self.records.remove_document_file(path)

    def ingest(
        self,
        filename: str,
        content_type: str,
        data: bytes,
        meta: KnowledgeCreate,
    ) -> KnowledgeRead:
        if not data:
            raise IntegrationError("The uploaded file is empty.")
        if len(data) > MAX_BYTES:
            raise IntegrationError("The file is larger than 20 MB.")
        document = self.records.create_document(
            {
                **meta.model_dump(mode="json"),
                "ingestion_status": "pending",
            }
        )
        document_id = UUID(document["id"])
        try:
            storage_path = f"{document_id}/{_safe_name(filename)}"
            self.records.upload_document_file(
                storage_path,
                data,
                content_type or "application/octet-stream",
            )
            self.records.update_document(
                document_id,
                {"storage_path": storage_path, "ingestion_status": "processing", "ingestion_error": None},
            )
            pages = extract_pages(filename, content_type or "", data)
            chunks = chunk_pages(pages)
            if not chunks:
                raise IntegrationError("No text could be extracted from the document.")
            if len(chunks) > MAX_CHUNKS:
                raise IntegrationError(
                    f"The document produced {len(chunks)} chunks. Split it so it stays within {MAX_CHUNKS}."
                )
            vectors = self.llm.embed([chunk.content for chunk in chunks])
            rows = []
            for chunk, vector in zip(chunks, vectors):
                rows.append(
                    {
                        "document_id": str(document_id),
                        "content": chunk.content,
                        "embedding": _vector_literal(vector),
                        "metadata": {
                            "page_number": chunk.page_number,
                            "chunk_index": chunk.chunk_index,
                        },
                    }
                )
            for start in range(0, len(rows), 50):
                self.records.insert_chunks(rows[start : start + 50])
            self.records.update_document(
                document_id,
                {"ingestion_status": "ready", "ingestion_error": None},
            )
        except AppError as exc:
            self._fail(document_id, exc.message)
            raise
        except Exception as exc:
            logger.exception("Document ingestion failed")
            self._fail(document_id, "The document could not be ingested.")
            raise IntegrationError("The document could not be ingested.") from exc
        return KnowledgeRead.model_validate(self.records.get_document(document_id))

    def _fail(self, document_id: UUID, message: str) -> None:
        try:
            self.records.update_document(
                document_id,
                {"ingestion_status": "failed", "ingestion_error": message[:1000]},
            )
        except AppError:
            logger.info("Could not record the ingestion failure for %s", document_id)


def _safe_name(filename: str) -> str:
    name = Path(filename or "document").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", name).strip("._")
    return (cleaned[:120] or "document")
