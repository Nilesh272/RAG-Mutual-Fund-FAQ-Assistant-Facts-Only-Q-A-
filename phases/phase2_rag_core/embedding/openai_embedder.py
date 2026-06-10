from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Protocol

import httpx

from phases.phase2_rag_core.embedding.models import EmbeddingConfig

logger = logging.getLogger(__name__)


class BaseEmbedder(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class OpenAIEmbedder:
    def __init__(self, config: EmbeddingConfig, api_key: str | None = None) -> None:
        self.config = config
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.config.batch_size):
            batch = texts[start : start + self.config.batch_size]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        attempts = self.config.max_retries + 1

        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self.config.timeout_seconds) as client:
                    response = client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={"model": self.config.model, "input": texts},
                    )
                    if response.status_code == 429 and attempt < attempts - 1:
                        backoff = self.config.retry_backoff_seconds[
                            min(attempt, len(self.config.retry_backoff_seconds) - 1)
                        ]
                        time.sleep(backoff)
                        continue
                    response.raise_for_status()
                    data = response.json()["data"]
                    ordered = sorted(data, key=lambda item: item["index"])
                    return [item["embedding"] for item in ordered]
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= attempts - 1:
                    raise
                backoff = self.config.retry_backoff_seconds[
                    min(attempt, len(self.config.retry_backoff_seconds) - 1)
                ]
                logger.warning("Embedding batch failed (attempt %s): %s", attempt + 1, exc)
                time.sleep(backoff)

        raise RuntimeError("Embedding batch failed") from last_error


class HashEmbedder:
    """Deterministic local embedder for tests and offline development."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vectorize(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._vectorize(query)

    def _vectorize(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self.config.dimensions:
            for byte in digest:
                values.append((byte / 255.0) * 2 - 1)
                if len(values) >= self.config.dimensions:
                    break
            digest = hashlib.sha256(digest).digest()
        return values[: self.config.dimensions]
