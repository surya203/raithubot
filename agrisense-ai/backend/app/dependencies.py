from functools import lru_cache

from app.config import get_settings
from app.errors import ConfigurationError
from app.repositories.records import RecordsRepository
from app.repositories.supabase_client import get_supabase_client
from app.services.advisory_service import AdvisoryService
from app.services.alert_service import AlertService
from app.services.catalog_service import CropService, EnvironmentService, LocationService
from app.services.chat_service import ChatService
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import LLMService
from app.services.prompt_manager import PromptManager
from app.services.rag_service import RAGService
from app.services.weather_service import OpenMeteoProvider, WeatherService


def get_records() -> RecordsRepository:
    return RecordsRepository(get_supabase_client())


@lru_cache
def get_weather_service() -> WeatherService:
    settings = get_settings()
    provider_name = settings.weather_api_provider.strip().lower().replace("_", "-")
    if provider_name not in {"", "open-meteo"}:
        raise ConfigurationError("Only the open-meteo weather provider is implemented.")
    return WeatherService(OpenMeteoProvider(), settings.weather_cache_seconds)


def get_llm_service() -> LLMService:
    return LLMService(get_settings().llm_config())


def get_prompt_manager() -> PromptManager:
    return PromptManager()


def get_location_service() -> LocationService:
    return LocationService(get_records())


def get_crop_service() -> CropService:
    return CropService(get_records())


def get_environment_service() -> EnvironmentService:
    return EnvironmentService(get_records())


def get_rag_service() -> RAGService:
    return RAGService(get_records(), get_llm_service())


def get_alert_service() -> AlertService:
    return AlertService(
        get_records(),
        get_weather_service(),
        get_environment_service(),
        get_llm_service(),
        get_prompt_manager(),
        get_settings(),
    )


def get_advisory_service() -> AdvisoryService:
    return AdvisoryService(
        get_records(),
        get_weather_service(),
        get_environment_service(),
        get_rag_service(),
        get_llm_service(),
        get_prompt_manager(),
        get_alert_service(),
    )


def get_chat_service() -> ChatService:
    return ChatService(
        get_records(),
        get_weather_service(),
        get_rag_service(),
        get_llm_service(),
        get_prompt_manager(),
    )


def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService(get_records(), get_llm_service())
