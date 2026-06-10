from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import yaml

from phases.phase2_rag_core.chunking.models import Chunk, ChunkingConfig
from phases.phase2_rag_core.chunking.splitter import TextSplitter
from phases.phase2_rag_core.chunking.tokenizer import Tokenizer
from phases.phase2_rag_core.parsing.models import SectionBlock

logger = logging.getLogger(__name__)


def _text_hash(text: str) -> str:
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ChunkingService:
    """Transform parsed sections into retrieval-ready chunks."""

    def __init__(self, config: ChunkingConfig) -> None:
        self.config = config
        self.tokenizer = Tokenizer(config.tokenizer)
        self.splitter = TextSplitter(
            self.tokenizer,
            max_tokens=config.max_tokens,
            overlap_tokens=config.overlap_tokens,
        )

    @classmethod
    def from_config_file(cls, path: Path) -> ChunkingService:
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)["chunking"]
        config = ChunkingConfig(
            target_tokens=int(raw.get("target_tokens", 500)),
            max_tokens=int(raw.get("max_tokens", 600)),
            min_tokens=int(raw.get("min_tokens", 100)),
            overlap_tokens=int(raw.get("overlap_tokens", 60)),
            tokenizer=raw.get("tokenizer", "cl100k_base"),
            context_prefix=raw.get("context_prefix", "{scheme_name} — {section_heading}: "),
        )
        return cls(config)

    def chunk(self, sections: list[SectionBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section in sections:
            chunks.extend(self.chunk_section(section))
        return chunks

    def chunk_page(self, sections: list[SectionBlock]) -> list[Chunk]:
        return self.chunk(sections)

    def chunk_section(self, section: SectionBlock) -> list[Chunk]:
        content = section.content.strip()
        if not content:
            logger.warning("Skipping empty section %s/%s", section.source_id, section.section_key)
            return []

        prefix = self.config.context_prefix.format(
            scheme_name=section.scheme_name,
            section_heading=section.section_heading,
        )
        prefixed = f"{prefix}{content}"
        parts = self.splitter.split(prefixed, section.content_type)

        seen_hashes: set[str] = set()
        section_chunks: list[Chunk] = []

        for index, part in enumerate(parts, start=1):
            text_hash = _text_hash(part)
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)

            chunk_id = f"{section.source_id}-{section.section_key}-chunk-{index:03d}"
            section_chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    source_id=section.source_id,
                    source_url=section.source_url,
                    document_type="scheme_page",
                    scheme_name=section.scheme_name,
                    scheme_category=section.scheme_category,
                    section_key=section.section_key,
                    section_heading=section.section_heading,
                    content_format="html",
                    text=part,
                    token_count=self.tokenizer.count(part),
                    chunk_index=index,
                    content_hash=section.content_hash,
                    text_hash=text_hash,
                )
            )

        return self._merge_orphans(section_chunks)

    def _merge_orphans(self, chunks: list[Chunk]) -> list[Chunk]:
        if not chunks:
            return []

        merged: list[Chunk] = []
        for chunk in chunks:
            if chunk.token_count < self.config.min_tokens and merged:
                prev = merged[-1]
                combined_text = f"{prev.text}\n{chunk.text}"
                merged[-1] = Chunk(
                    chunk_id=prev.chunk_id,
                    source_id=prev.source_id,
                    source_url=prev.source_url,
                    document_type=prev.document_type,
                    scheme_name=prev.scheme_name,
                    scheme_category=prev.scheme_category,
                    section_key=prev.section_key,
                    section_heading=prev.section_heading,
                    content_format=prev.content_format,
                    text=combined_text,
                    token_count=self.tokenizer.count(combined_text),
                    chunk_index=prev.chunk_index,
                    content_hash=prev.content_hash,
                    text_hash=_text_hash(combined_text),
                    indexed_at=prev.indexed_at,
                )
            else:
                merged.append(chunk)
        return merged
