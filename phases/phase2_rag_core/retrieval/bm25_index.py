from __future__ import annotations

import re
from typing import Any

from rank_bm25 import BM25Okapi


class BM25Index:
    """Sparse retrieval index built from indexed chunk texts."""

    def __init__(self) -> None:
        self._chunks: list[dict[str, Any]] = []
        self._bm25: BM25Okapi | None = None

    def build(self, chunks: list[dict[str, Any]]) -> None:
        self._chunks = chunks
        tokenized = [self._tokenize(chunk.get("text", "")) for chunk in chunks]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def search(self, query: str, *, limit: int = 10) -> list[tuple[dict[str, Any], float]]:
        if not self._bm25 or not self._chunks:
            return []

        scores = self._bm25.get_scores(self._tokenize(query))
        ranked = sorted(
            zip(self._chunks, scores),
            key=lambda item: item[1],
            reverse=True,
        )
        return [(chunk, float(score)) for chunk, score in ranked[:limit] if score > 0]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z0-9%]+", text.lower())
