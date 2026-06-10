from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SourceEntry:
    source_id: str
    url: str
    document_type: str
    scheme_name: str
    scheme_category: str
    plan_type: str = "Direct Growth"
    content_format: str = "html"
    language: str = "en"
    amc: str = "HDFC Mutual Fund"
    last_fetched: Optional[str] = None
    content_hash: Optional[str] = None


@dataclass
class SourceRegistry:
    amc: str
    language: str
    content_format: str
    sources: list[SourceEntry] = field(default_factory=list)
