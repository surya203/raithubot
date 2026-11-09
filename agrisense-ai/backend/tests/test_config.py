from app.config import Settings


def _settings(**overrides) -> Settings:
    values = {
        "llm_provider": "",
        "llm_api_key": "",
        "llm_model": "",
        "embedding_model": "",
        "embedding_dimensions": 1536,
        "groq_api_key": "",
        "openai_api_key": "",
    }
    values.update(overrides)
    return Settings.model_construct(**values)


def test_existing_groq_key_is_the_default_chat_provider():
    config = _settings(groq_api_key="groq-key", openai_api_key="openai-key").llm_config()
    assert config.provider == "groq"
    assert config.api_key == "groq-key"
    assert config.model == "openai/gpt-oss-20b"
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.embedding_api_key == "openai-key"
    assert config.embedding_model == "text-embedding-3-small"
    assert config.embedding_dimensions == 1536


def test_explicit_provider_overrides_the_existing_keys():
    config = _settings(
        llm_provider="openai",
        llm_api_key="explicit-key",
        llm_model="gpt-4.1-mini",
        groq_api_key="groq-key",
        openai_api_key="openai-key",
    ).llm_config()
    assert config.provider == "openai"
    assert config.api_key == "explicit-key"
    assert config.model == "gpt-4.1-mini"


def test_openai_is_used_when_groq_is_absent():
    config = _settings(openai_api_key="openai-key").llm_config()
    assert config.provider == "openai"
    assert config.api_key == "openai-key"
    assert config.model == "gpt-4.1-mini"
