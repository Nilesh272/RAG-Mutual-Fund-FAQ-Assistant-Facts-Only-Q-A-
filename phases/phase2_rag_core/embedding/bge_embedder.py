from __future__ import annotations

import logging

from phases.phase2_rag_core.embedding.models import EmbeddingConfig

logger = logging.getLogger(__name__)

DEFAULT_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class BGEEmbedder:
    """Local embeddings via HuggingFace sentence-transformers (BAAI/bge-small-en-v1.5)."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        self.query_prefix = config.query_prefix or DEFAULT_QUERY_PREFIX
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", self.config.model)
            self._model = SentenceTransformer(self.config.model)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        model = self._load_model()
        vectors = model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize_embeddings,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, query: str) -> list[float]:
        prefixed = f"{self.query_prefix}{query}"
        return self.embed_texts([prefixed])[0]
