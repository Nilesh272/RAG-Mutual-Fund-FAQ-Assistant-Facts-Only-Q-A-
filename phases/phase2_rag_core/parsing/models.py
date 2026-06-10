from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ContentType = Literal["text", "table"]


@dataclass
class SectionBlock:
    source_id: str
    source_url: str
    scheme_name: str
    scheme_category: str
    section_key: str
    section_heading: str
    content: str
    content_type: ContentType = "text"
    content_hash: str = ""
