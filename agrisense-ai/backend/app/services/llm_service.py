import json
import logging
from typing import Any

import httpx

from app.config import LLMConfig
from app.errors import ConfigurationError, IntegrationError

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete_json(self, system: str, user: str) -> str:
        self._require_chat()
        attempts = (
            {"json_mode": True, "temperature": True, "max_tokens": True},
            {"json_mode": True, "temperature": False, "max_tokens": True},
            {"json_mode": False, "temperature": False, "max_tokens": True},
            {"json_mode": False, "temperature": False, "max_tokens": False},
        )
        for attempt in attempts:
            try:
                return self._chat(system, user, **attempt)
            except IntegrationError as exc:
                if exc.status_code != 400:
                    raise
        raise IntegrationError("The language model rejected the request.")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.config.embeddings_configured:
            raise ConfigurationError(
                "Embeddings are not configured. Set OPENAI_API_KEY. "
                "The knowledge index uses 1536-dimension vectors."
            )
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 32):
            batch = texts[start : start + 32]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _require_chat(self) -> None:
        if not self.config.chat_configured:
            raise ConfigurationError(
                "No language model is configured. Set GROQ_API_KEY or OPENAI_API_KEY, "
                "or set LLM_PROVIDER and LLM_API_KEY."
            )

    def _chat(self, system: str, user: str, json_mode: bool, temperature: bool, max_tokens: bool) -> str:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if temperature:
            payload["temperature"] = 0.2
        if max_tokens:
            payload["max_tokens"] = 1800
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        body = self._post("/chat/completions", payload, self.config.api_key)
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise IntegrationError("The language model returned an unexpected response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise IntegrationError("The language model returned an empty response.")
        return content

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {
            "model": self.config.embedding_model,
            "input": texts,
        }
        if self.config.embedding_model.startswith("text-embedding-3"):
            payload["dimensions"] = self.config.embedding_dimensions
        body = self._post(
            "/embeddings",
            payload,
            self.config.embedding_api_key,
            base_url="https://api.openai.com/v1",
        )
        try:
            rows = sorted(body["data"], key=lambda item: item["index"])
            vectors = [row["embedding"] for row in rows]
        except (KeyError, TypeError) as exc:
            raise IntegrationError("The embedding model returned an unexpected response.") from exc
        expected = self.config.embedding_dimensions
        if len(vectors) != len(texts) or any(len(vector) != expected for vector in vectors):
            raise IntegrationError(
                f"Expected {expected}-dimension embeddings and received a different size."
            )
        return vectors

    def _post(
        self,
        path: str,
        payload: dict,
        api_key: str,
        base_url: str | None = None,
    ) -> dict:
        url = f"{base_url or self.config.base_url}{path}"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            with httpx.Client(timeout=90) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise IntegrationError("The language model could not be reached.") from exc
        if response.status_code == 400:
            logger.info(
                "Language model rejected the request shape for %s",
                payload.get("model"),
            )
            raise IntegrationError("The language model rejected the request shape.", status_code=400)
        if response.status_code >= 400:
            logger.info("Language model HTTP %s for %s", response.status_code, payload.get("model"))
            raise IntegrationError("The language model request failed.")
        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise IntegrationError("The language model returned invalid JSON metadata.") from exc
        if not isinstance(body, dict):
            raise IntegrationError("The language model returned an unexpected response.")
        return body
