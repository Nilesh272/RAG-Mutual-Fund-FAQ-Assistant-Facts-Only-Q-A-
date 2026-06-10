from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class ScrapingConfig:
    user_agent: str = "MF-FAQ-Bot/1.0"
    rate_limit_seconds: float = 1.0
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: tuple[float, ...] = (2.0, 4.0)
    allowed_domain: str = "groww.in"
    allowed_path_prefix: str = "/mutual-funds/"
    save_raw_snapshots: bool = True
    raw_snapshot_dir: str = "data/raw"


ScrapeStatus = Literal["success", "failed"]


@dataclass
class ScrapeResult:
    source_id: str
    url: str
    status: ScrapeStatus
    http_status: Optional[int]
    html: Optional[str]
    content_hash: Optional[str]
    fetched_at: str
    error: Optional[str] = None
    changed: bool = False

    def to_summary_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "status": self.status,
            "http_status": self.http_status,
            "content_hash": self.content_hash,
            "fetched_at": self.fetched_at,
            "changed": self.changed,
            "error": self.error,
        }
