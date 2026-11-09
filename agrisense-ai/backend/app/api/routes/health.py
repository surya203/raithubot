from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    app: str
    status: str
    database_configured: bool
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_configured: bool
    embeddings_configured: bool
    embedding_model: str | None = None
    weather_provider: str
    internal_auth_enabled: bool


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    llm = settings.llm_config()
    return HealthResponse(
        app="AgriSense AI",
        status="ok",
        database_configured=settings.database_configured,
        llm_provider=llm.provider or None,
        llm_model=llm.model or None,
        llm_configured=llm.chat_configured,
        embeddings_configured=llm.embeddings_configured,
        embedding_model=llm.embedding_model if llm.embeddings_configured else None,
        weather_provider="open-meteo",
        internal_auth_enabled=bool(settings.internal_api_token.strip()),
    )
