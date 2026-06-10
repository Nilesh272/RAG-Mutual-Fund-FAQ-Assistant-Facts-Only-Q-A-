from __future__ import annotations

import re

from phases.phase2_rag_core.retrieval.models import RetrievedChunk, RetrievalConfig


class ChunkReranker:
    """Lightweight reranker using section-keyword overlap (v1 cross-encoder substitute)."""

    def __init__(self, config: RetrievalConfig) -> None:
        self.config = config
        self.section_keywords = config.section_keywords or {}

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []

        query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored: list[tuple[RetrievedChunk, float]] = []

        for chunk in chunks:
            boost = 0.0
            keywords = self.section_keywords.get(chunk.section_key, [])
            for keyword in keywords:
                if keyword in query.lower():
                    boost += 0.15
            overlap = len(query_terms.intersection(set(re.findall(r"[a-z0-9]+", chunk.text.lower()))))
            boost += min(overlap * 0.02, 0.1)
            scored.append((chunk, chunk.final_score + boost))

        scored.sort(key=lambda item: item[1], reverse=True)
        reranked: list[RetrievedChunk] = []
        for chunk, score in scored[: self.config.top_k_rerank]:
            reranked.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    source_url=chunk.source_url,
                    scheme_name=chunk.scheme_name,
                    section_key=chunk.section_key,
                    section_heading=chunk.section_heading,
                    text=chunk.text,
                    dense_score=chunk.dense_score,
                    sparse_score=chunk.sparse_score,
                    final_score=score,
                    payload=chunk.payload,
                    indexed_at=chunk.indexed_at,
                )
            )
        return reranked
