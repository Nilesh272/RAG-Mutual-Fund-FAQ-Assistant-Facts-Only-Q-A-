from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RetrievalConfig:
    dense_weight: float = 0.7
    top_k: int = 10
    top_k_rerank: int = 5
    similarity_threshold: float = 0.65
    section_keywords: dict[str, list[str]] | None = None


@dataclass
class RetrievedChunk:
    chunk_id: str
    source_id: str
    source_url: str
    scheme_name: str
    section_key: str
    section_heading: str
    text: str
    dense_score: float
    sparse_score: float
    final_score: float
    payload: dict[str, Any]
    indexed_at: Optional[str] = None
