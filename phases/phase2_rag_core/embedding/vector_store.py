from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from phases.phase2_rag_core.embedding.chroma_client import create_chroma_client, resolve_chroma_mode
from phases.phase2_rag_core.embedding.models import UpsertResult, VectorRecord, VectorStoreConfig

logger = logging.getLogger(__name__)


class VectorStore:
    """Chroma vector store — local PersistentClient, CloudClient, or EphemeralClient."""

    def __init__(
        self,
        config: VectorStoreConfig,
        project_root: Path,
        vector_dimensions: int = 384,
        *,
        chroma_client=None,
        mode: str | None = None,
    ) -> None:
        self.config = config
        self.project_root = project_root
        self.vector_dimensions = vector_dimensions
        self._mode = mode or resolve_chroma_mode(config)
        self._client = chroma_client or create_chroma_client(
            config, project_root, mode=self._mode
        )
        self._collection = self._client.get_or_create_collection(
            name=self.config.collection,
            metadata={"hnsw:space": self.config.distance},
        )

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def collection_name(self) -> str:
        return self.config.collection

    def health_check(self) -> bool:
        """Verify the Chroma collection is reachable."""
        try:
            self._collection.count()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Chroma health check failed: %s", exc)
            return False

    def count_by_metadata(self, where: dict[str, Any]) -> int:
        result = self._collection.get(where=where)
        return len(result.get("ids", []))

    def delete_by_source_id(self, source_id: str) -> int:
        existing = self._collection.get(where={"source_id": source_id})
        ids = existing.get("ids", [])
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return 0

        self._collection.upsert(
            ids=[record.id for record in records],
            embeddings=[record.vector for record in records],
            documents=[record.payload.get("text", "") for record in records],
            metadatas=[self._chroma_metadata(record.payload) for record in records],
        )
        return len(records)

    def get_all_chunks(self) -> list[dict[str, Any]]:
        """Return all indexed chunks with text and metadata."""
        result = self._collection.get(include=["documents", "metadatas"])
        chunks: list[dict[str, Any]] = []
        for idx, point_id in enumerate(result.get("ids", [])):
            metadata = result["metadatas"][idx] if result.get("metadatas") else {}
            document = result["documents"][idx] if result.get("documents") else ""
            payload = dict(metadata)
            payload.setdefault("chunk_id", point_id)
            payload.setdefault("text", document)
            chunks.append({"id": point_id, "payload": payload, "text": document})
        return chunks

    def count(self) -> int:
        return self._collection.count()

    def count_for_source(self, source_id: str) -> int:
        result = self._collection.get(where={"source_id": source_id})
        return len(result.get("ids", []))

    def search(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        source_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        where = {"source_id": source_id} if source_id else None
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=where,
        )
        return self._format_chroma_results(results)

    def upsert_for_source(self, source_id: str, records: list[VectorRecord]) -> UpsertResult:
        try:
            deleted = self.delete_by_source_id(source_id)
            inserted = self.upsert(records)
            verified = self.count_for_source(source_id) == len(records)
            if not verified:
                return UpsertResult(
                    source_id=source_id,
                    deleted_count=deleted,
                    upserted_count=inserted,
                    verified=False,
                    error="Upsert count mismatch after insert",
                )
            return UpsertResult(
                source_id=source_id,
                deleted_count=deleted,
                upserted_count=inserted,
                verified=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Vector upsert failed for %s", source_id)
            return UpsertResult(
                source_id=source_id,
                deleted_count=0,
                upserted_count=0,
                verified=False,
                error=str(exc),
            )

    @staticmethod
    def _chroma_metadata(payload: dict[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
            else:
                metadata[key] = str(value)
        return metadata

    @staticmethod
    def _format_chroma_results(results: dict[str, Any]) -> list[dict[str, Any]]:
        formatted: list[dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for idx, point_id in enumerate(ids):
            formatted.append(
                {
                    "id": point_id,
                    "score": 1 - distances[idx] if distances else None,
                    "payload": metadatas[idx] if metadatas else {},
                }
            )
        return formatted
