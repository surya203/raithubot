# Architecture

AgriSense AI is one FastAPI application. Routes validate input and call services. Services own weather retrieval, advisory generation, chat, alerts, and document ingestion. Repositories are the only Supabase access.

```text
api/routes
  -> services
       -> Open-Meteo
       -> Groq or OpenAI chat
       -> OpenAI embeddings
       -> repositories
            -> Supabase Postgres and Storage
```

Chat uses the Groq key already present in the environment unless `LLM_PROVIDER=openai`. Embeddings always use OpenAI `text-embedding-3-small` so vectors match the `vector(1536)` column.

The language-model calls sit in `llm_service.py`. Prompts are files in `app/prompts`. `response_validator.py` checks the JSON and drops citations that were not retrieved.

Weather is normalized in `weather_service.py` and cached in memory. A failed refresh can return the previous payload with `stale: true`.

Alert categories are created by `alert_rules.py` from numeric thresholds. The model may rewrite the description. It does not choose the category or severity.

There is no login, user table, or separate machine-learning model.
