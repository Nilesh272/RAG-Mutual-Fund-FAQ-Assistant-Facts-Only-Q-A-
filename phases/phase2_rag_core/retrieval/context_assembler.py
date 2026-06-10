from __future__ import annotations

from phases.phase2_rag_core.chunking.tokenizer import Tokenizer
from phases.phase2_rag_core.retrieval.models import RetrievedChunk


class ContextAssembler:
    """Build generator context from retrieved chunks (max 2000 tokens)."""

    def __init__(self, max_tokens: int = 2000) -> None:
        self.max_tokens = max_tokens
        self.tokenizer = Tokenizer()

    def assemble(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""

        sections: list[str] = []
        used_tokens = 0

        for chunk in chunks:
            block = (
                f"[Chunk — source: {chunk.source_url}, section: {chunk.section_heading}]\n"
                f"{chunk.text}"
            )
            block_tokens = self.tokenizer.count(block)
            if used_tokens + block_tokens > self.max_tokens:
                break
            sections.append(block)
            used_tokens += block_tokens

        return "\n\n".join(sections)

    def primary_source_url(self, chunks: list[RetrievedChunk]) -> str | None:
        if not chunks:
            return None
        return chunks[0].source_url

    def latest_indexed_at(self, chunks: list[RetrievedChunk]) -> str | None:
        dates = [chunk.indexed_at for chunk in chunks if chunk.indexed_at]
        return max(dates) if dates else None
