from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ChunkingConfig:
    target_tokens: int = 500
    max_tokens: int = 600
    min_tokens: int = 100
    overlap_tokens: int = 60
    tokenizer: str = "cl100k_base"
    context_prefix: str = "{scheme_name} — {section_heading}: "


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    source_url: str
    document_type: str
    scheme_name: str
    scheme_category: str
    section_key: str
    section_heading: str
    content_format: str
    text: str
    token_count: int
    chunk_index: int
    content_hash: str
    text_hash: str
    indexed_at: Optional[str] = None
