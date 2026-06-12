from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yaml

from phases.phase2_rag_core.chunking.models import Chunk
from phases.phase2_rag_core.embedding.models import (
    EmbeddingConfig,
    UpsertResult,
    VectorRecord,
    VectorStoreConfig,
)
from phases.phase2_rag_core.embedding.bge_embedder import BGEEmbedder
from phases.phase2_rag_core.embedding.openai_embedder import HashEmbedder, OpenAIEmbedder
from phases.phase2_rag_core.embedding.vector_store import VectorStore

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class EmbeddingService:
    """Batch-embed chunks and upsert vectors to the configured store."""

    def __init__(
        self,
        embedder,
        vector_store: VectorStore,
        embedding_config: EmbeddingConfig,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.embedding_config = embedding_config

    @classmethod
    def from_config_files(
        cls,
        embedding_config_path: Path,
        project_root: Optional[Path] = None,
    ) -> EmbeddingService:
        root = project_root or Path.cwd()
        with embedding_config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        embedding_raw = raw["embedding"]
        embedding_config = EmbeddingConfig(
            provider=embedding_raw.get("provider", "bge"),
            model=embedding_raw.get("model", "BAAI/bge-small-en-v1.5"),
            dimensions=int(embedding_raw.get("dimensions", 384)),
            batch_size=int(embedding_raw.get("batch_size", 32)),
            max_retries=int(embedding_raw.get("max_retries", 3)),
            timeout_seconds=int(embedding_raw.get("timeout_seconds", 60)),
            retry_backoff_seconds=tuple(embedding_raw.get("retry_backoff_seconds", [1, 2, 4])),
            normalize_embeddings=bool(embedding_raw.get("normalize_embeddings", True)),
            query_prefix=embedding_raw.get(
                "query_prefix",
                "Represent this sentence for searching relevant passages: ",
            ),
        )

        store_raw = raw["vector_store"]
        store_config = VectorStoreConfig(
            provider=store_raw.get("provider", "chroma"),
            mode=store_raw.get("mode", "cloud"),
            collection=store_raw.get("collection", "mf_faq_hdfc_groww"),
            distance=store_raw.get("distance", "cosine"),
            tenant=store_raw.get("tenant", ""),
            database=store_raw.get("database", "mf-faq-prod"),
            host=store_raw.get("host", "api.trychroma.com"),
        )

        provider = os.getenv("EMBEDDING_PROVIDER", embedding_config.provider)
        if provider == "hash":
            embedder = HashEmbedder(embedding_config)
        elif provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
            embedder = OpenAIEmbedder(embedding_config)
        elif provider == "bge":
            embedder = BGEEmbedder(embedding_config)
        else:
            embedder = BGEEmbedder(embedding_config)

        vector_store = VectorStore(
            store_config,
            project_root=root,
            vector_dimensions=embedding_config.dimensions,
        )
        return cls(embedder, vector_store, embedding_config)

    def embed_chunks(self, chunks: list[Chunk]) -> list[VectorRecord]:
        if not chunks:
            return []

        indexed_at = datetime.now(IST).isoformat(timespec="seconds")
        texts = [chunk.text for chunk in chunks]
        vectors = self.embedder.embed_texts(texts)

        records: list[VectorRecord] = []
        for chunk, vector in zip(chunks, vectors):
            records.append(
                VectorRecord(
                    id=chunk.chunk_id,
                    vector=vector,
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "source_id": chunk.source_id,
                        "source_url": chunk.source_url,
                        "scheme_name": chunk.scheme_name,
                        "scheme_category": chunk.scheme_category,
                        "section_key": chunk.section_key,
                        "section_heading": chunk.section_heading,
                        "document_type": chunk.document_type,
                        "text": chunk.text,
                        "token_count": chunk.token_count,
                        "content_hash": chunk.content_hash,
                        "indexed_at": indexed_at,
                    },
                )
            )
        return records

    def embed_query(self, query: str) -> list[float]:
        return self.embedder.embed_query(query)

    def upsert(self, records: list[VectorRecord], source_id: str) -> UpsertResult:
        return self.vector_store.upsert_for_source(source_id, records)

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        source_id: Optional[str] = None,
    ) -> list[dict]:
        query_vector = self.embed_query(query)
        return self.vector_store.search(query_vector, limit=limit, source_id=source_id)
