from functools import lru_cache
from typing import Any

from app.config import get_settings
from app.errors import ConfigurationError


@lru_cache
def get_supabase_client() -> Any:
    settings = get_settings()
    if not settings.database_configured:
        raise ConfigurationError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        )
    key = settings.supabase_service_role_key.strip()
    if key.startswith("sb_publishable_"):
        raise ConfigurationError(
            "SUPABASE_SERVICE_ROLE_KEY is a publishable key, so the database rejects writes. "
            "Replace it with the secret key from the Supabase dashboard (Settings, API)."
        )
    try:
        from supabase import create_client
    except ImportError as exc:
        raise ConfigurationError("The supabase package is not installed.") from exc
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def reset_supabase_client() -> None:
    get_supabase_client.cache_clear()
