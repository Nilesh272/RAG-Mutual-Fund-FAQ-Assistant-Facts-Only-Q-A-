from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class EmbeddingConfig:
    provider: str = "bge"
    model: str = "BAAI/bge-small-en-v1.5"
    dimensions: int = 384
    batch_size: int = 32
    max_retries: int = 3
    timeout_seconds: int = 60
    retry_backoff_seconds: tuple[float, ...] = (1.0, 2.0, 4.0)
    normalize_embeddings: bool = True
    query_prefix: str = "Represent this sentence for searching relevant passages: "


@dataclass
class VectorStoreConfig:
    provider: str = "chroma"
    mode: str = "cloud"
    collection: str = "mf_faq_hdfc_groww"
    distance: str = "cosine"
    tenant: str = ""
    database: str = "mf-faq-prod"
    host: str = "api.trychroma.com"


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass
class UpsertResult:
    source_id: str
    deleted_count: int
    upserted_count: int
    verified: bool = True
    error: Optional[str] = None
