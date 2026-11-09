"""Runtime configuration.

Chat defaults to the Groq key already present in the process environment.
Embeddings use the OpenAI key, because the database vector column is 1536
dimensions and Groq is not used as an embedding provider.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class LLMConfig:
    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str,
        embedding_api_key: str,
        embedding_model: str,
        embedding_dimensions: int,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.embedding_api_key = embedding_api_key
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions

    @property
    def chat_configured(self) -> bool:
        return bool(self.provider and self.api_key and self.model)

    @property
    def embeddings_configured(self) -> bool:
        return bool(self.embedding_api_key and self.embedding_model)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_model: str = ""
    embedding_dimensions: int = 1536
    weather_api_provider: str = "open-meteo"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    internal_api_token: str = ""

    # Read from the existing process environment when LLM_* is blank.
    openai_api_key: str = ""
    groq_api_key: str = ""

    # Operational heuristics. Not calibrated disease or IMD warning products.
    alert_heavy_rain_mm: float = 50
    alert_heavy_rain_probability: float = 80
    alert_heavy_rain_min_mm_with_probability: float = 20
    alert_extreme_heat_c: float = 40
    alert_extreme_cold_c: float = 5
    alert_high_humidity: float = 85
    alert_low_soil_moisture: float = 30
    alert_humidity_crops: str = "rice,paddy,tomato,potato,cotton,grape"
    alert_dedupe_hours: int = 12
    weather_cache_seconds: int = 600
    port: int = Field(default=8000, validation_alias="PORT")

    @property
    def database_configured(self) -> bool:
        return bool(self.supabase_url.strip() and self.supabase_service_role_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def humidity_crop_names(self) -> set[str]:
        return {
            name.strip().lower()
            for name in self.alert_humidity_crops.split(",")
            if name.strip()
        }

    def llm_config(self) -> LLMConfig:
        provider = self.llm_provider.strip().lower()
        if provider not in {"", "openai", "groq"}:
            provider = ""

        if not provider:
            if self.groq_api_key.strip():
                provider = "groq"
            elif self.openai_api_key.strip() or self.llm_api_key.strip():
                provider = "openai"

        if provider == "groq":
            api_key = self.llm_api_key.strip() or self.groq_api_key.strip()
            model = self.llm_model.strip() or DEFAULT_GROQ_MODEL
            base_url = GROQ_BASE_URL
        elif provider == "openai":
            api_key = self.llm_api_key.strip() or self.openai_api_key.strip()
            model = self.llm_model.strip() or DEFAULT_OPENAI_MODEL
            base_url = OPENAI_BASE_URL
        else:
            api_key = ""
            model = ""
            base_url = ""

        if provider == "openai":
            embedding_key = self.openai_api_key.strip() or self.llm_api_key.strip()
        else:
            embedding_key = self.openai_api_key.strip()

        return LLMConfig(
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            embedding_api_key=embedding_key,
            embedding_model=self.embedding_model.strip() or DEFAULT_EMBEDDING_MODEL,
            embedding_dimensions=self.embedding_dimensions,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
