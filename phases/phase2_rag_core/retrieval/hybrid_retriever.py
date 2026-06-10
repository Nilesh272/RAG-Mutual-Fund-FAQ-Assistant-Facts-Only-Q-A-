from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from phases.phase2_rag_core.embedding.embedder import EmbeddingService
from phases.phase2_rag_core.retrieval.bm25_index import BM25Index
from phases.phase2_rag_core.retrieval.models import RetrievedChunk, RetrievalConfig
from phases.phase2_rag_core.retrieval.query_enhancer import QueryEnhancer
from phases.phase2_rag_core.retrieval.reranker import ChunkReranker

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid dense + sparse retrieval with lightweight reranking."""

    def __init__(
        self,
        embedder: EmbeddingService,
        config: RetrievalConfig,
        query_enhancer: QueryEnhancer,
    ) -> None:
        self.embedder = embedder
        self.config = config
        self.query_enhancer = query_enhancer
        self.reranker = ChunkReranker(config)
        self._bm25 = BM25Index()
        self.refresh_sparse_index()

    @classmethod
    def from_config_files(
        cls,
        embedding_config_path: Path,
        retrieval_config_path: Path,
        sources_path: Path,
        project_root: Optional[Path] = None,
    ) -> HybridRetriever:
        root = project_root or Path.cwd()
        with retrieval_config_path.open(encoding="utf-8") as f:
            raw_all = yaml.safe_load(f)
        raw = raw_all["retrieval"]

        config = RetrievalConfig(
            dense_weight=float(raw.get("dense_weight", 0.7)),
            top_k=int(raw.get("top_k", 10)),
            top_k_rerank=int(raw.get("top_k_rerank", 5)),
            similarity_threshold=float(raw.get("similarity_threshold", 0.65)),
            section_keywords=raw_all.get("section_keywords", {}),
        )
        embedder = EmbeddingService.from_config_files(embedding_config_path, project_root=root)
        enhancer = QueryEnhancer(sources_path=sources_path)
        return cls(embedder, config, enhancer)

    def refresh_sparse_index(self) -> int:
        chunks = self.embedder.vector_store.get_all_chunks()
        self._bm25.build(chunks)
        logger.info("BM25 index rebuilt with %s chunks", len(chunks))
        return len(chunks)

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        enhanced_query, source_id, _ = self.query_enhancer.enhance(query)
        dense_hits = self.embedder.vector_store.search(
            self.embedder.embed_query(enhanced_query),
            limit=self.config.top_k,
            source_id=source_id,
        )
        sparse_hits = self._bm25.search(enhanced_query, limit=self.config.top_k)

        combined = self._combine_scores(dense_hits, sparse_hits)
        if not combined:
            return []

        filtered = [
            chunk
            for chunk in combined
            if chunk.final_score >= self.config.similarity_threshold
        ]
        if not filtered:
            filtered = combined[: self.config.top_k_rerank]

        return self.reranker.rerank(enhanced_query, filtered)

    def _combine_scores(
        self,
        dense_hits: list[dict[str, Any]],
        sparse_hits: list[tuple[dict[str, Any], float]],
    ) -> list[RetrievedChunk]:
        sparse_map: dict[str, float] = {}
        max_sparse = max((score for _, score in sparse_hits), default=0.0)
        for chunk, score in sparse_hits:
            chunk_id = chunk.get("id") or chunk.get("payload", {}).get("chunk_id")
            if chunk_id:
                sparse_map[chunk_id] = score / max_sparse if max_sparse > 0 else 0.0

        merged: dict[str, RetrievedChunk] = {}
        alpha = self.config.dense_weight

        for hit in dense_hits:
            payload = hit.get("payload", {})
            chunk_id = hit.get("id") or payload.get("chunk_id")
            if not chunk_id:
                continue
            dense_score = float(hit.get("score") or 0.0)
            sparse_score = sparse_map.get(chunk_id, 0.0)
            final_score = alpha * dense_score + (1 - alpha) * sparse_score
            merged[chunk_id] = self._to_retrieved_chunk(
                chunk_id, payload, dense_score, sparse_score, final_score
            )

        for chunk, score in sparse_hits:
            chunk_id = chunk.get("id") or chunk.get("payload", {}).get("chunk_id")
            if not chunk_id or chunk_id in merged:
                continue
            sparse_score = score / max_sparse if max_sparse > 0 else 0.0
            payload = chunk.get("payload", {})
            merged[chunk_id] = self._to_retrieved_chunk(
                chunk_id, payload, 0.0, sparse_score, (1 - alpha) * sparse_score
            )

        return sorted(merged.values(), key=lambda item: item.final_score, reverse=True)

    @staticmethod
    def _to_retrieved_chunk(
        chunk_id: str,
        payload: dict[str, Any],
        dense_score: float,
        sparse_score: float,
        final_score: float,
    ) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=chunk_id,
            source_id=payload.get("source_id", ""),
            source_url=payload.get("source_url", ""),
            scheme_name=payload.get("scheme_name", ""),
            section_key=payload.get("section_key", ""),
            section_heading=payload.get("section_heading", ""),
            text=payload.get("text", ""),
            dense_score=dense_score,
            sparse_score=sparse_score,
            final_score=final_score,
            payload=payload,
            indexed_at=payload.get("indexed_at"),
        )
