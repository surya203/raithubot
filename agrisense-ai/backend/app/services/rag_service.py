from app.repositories.records import RecordsRepository
from app.schemas.knowledge import RetrievedChunk
from app.services.llm_service import LLMService


class RAGService:
    def __init__(self, records: RecordsRepository, llm: LLMService) -> None:
        self.records = records
        self.llm = llm

    def retrieve(
        self,
        query: str,
        *,
        crop: str | None = None,
        disease: str | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        text = query.strip()
        if not text:
            return []
        embedding = self.llm.embed([text])[0]
        rows = self.records.match_chunks(embedding, limit, crop, None, disease)
        return [RetrievedChunk.model_validate(row) for row in rows]
