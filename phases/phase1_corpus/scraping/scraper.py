from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
import yaml

from phases.phase1_corpus.registry.models import SourceEntry
from phases.phase1_corpus.registry.source_registry import SourceRegistryService
from phases.phase1_corpus.scraping.allowlist import AllowlistError, AllowlistValidator
from phases.phase1_corpus.scraping.models import ScrapeResult, ScrapingConfig

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def _now_ist_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _content_hash(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def _is_html_response(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    return "text/html" in content_type.lower()


class ScrapingService:
    """Fetches HTML from allowlisted Groww scheme URLs."""

    def __init__(
        self,
        registry: SourceRegistryService,
        config: Optional[ScrapingConfig] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.registry = registry
        self.config = config or ScrapingConfig()
        self.project_root = project_root or Path.cwd()
        registry.load()
        self.allowlist = AllowlistValidator(registry.get_allowlisted_urls(), self.config)

    @classmethod
    def from_config_files(
        cls,
        sources_path: Path,
        scraping_config_path: Path,
        project_root: Optional[Path] = None,
    ) -> ScrapingService:
        with scraping_config_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)["scraping"]

        config = ScrapingConfig(
            user_agent=raw.get("user_agent", "MF-FAQ-Bot/1.0"),
            rate_limit_seconds=float(raw.get("rate_limit_seconds", 1.0)),
            timeout_seconds=float(raw.get("timeout_seconds", 30)),
            max_retries=int(raw.get("max_retries", 2)),
            retry_backoff_seconds=tuple(raw.get("retry_backoff_seconds", [2, 4])),
            allowed_domain=raw.get("allowed_domain", "groww.in"),
            allowed_path_prefix=raw.get("allowed_path_prefix", "/mutual-funds/"),
            save_raw_snapshots=bool(raw.get("save_raw_snapshots", True)),
            raw_snapshot_dir=raw.get("raw_snapshot_dir", "data/raw"),
        )
        registry = SourceRegistryService(sources_path=sources_path)
        return cls(registry=registry, config=config, project_root=project_root)

    def start_scrape(self) -> list[ScrapeResult]:
        """Fetch all allowlisted URLs sequentially with rate limiting."""
        entries = self.registry.get_allowlisted_urls()
        results: list[ScrapeResult] = []

        for index, entry in enumerate(entries):
            if index > 0:
                time.sleep(self.config.rate_limit_seconds)

            result = self.scrape_entry(entry)
            results.append(result)

        return results

    def scrape_entry(self, entry: SourceEntry) -> ScrapeResult:
        fetched_at = _now_ist_iso()

        try:
            self.allowlist.validate_url(entry.url)
        except AllowlistError as exc:
            logger.error("Allowlist rejection for %s: %s", entry.source_id, exc)
            return ScrapeResult(
                source_id=entry.source_id,
                url=entry.url,
                status="failed",
                http_status=None,
                html=None,
                content_hash=None,
                fetched_at=fetched_at,
                error=str(exc),
            )

        try:
            html, http_status = self._fetch_with_retries(entry.url)
        except Exception as exc:  # noqa: BLE001 — surface as failed scrape result
            logger.error("Scrape failed for %s: %s", entry.source_id, exc)
            return ScrapeResult(
                source_id=entry.source_id,
                url=entry.url,
                status="failed",
                http_status=None,
                html=None,
                content_hash=None,
                fetched_at=fetched_at,
                error=str(exc),
            )

        if not html or not html.strip():
            return ScrapeResult(
                source_id=entry.source_id,
                url=entry.url,
                status="failed",
                http_status=http_status,
                html=None,
                content_hash=None,
                fetched_at=fetched_at,
                error="Empty HTML body",
            )

        content_hash = _content_hash(html)
        stored_hash = self.registry.get_stored_hash(entry.source_id)
        changed = stored_hash != content_hash

        if self.config.save_raw_snapshots:
            self._save_raw_snapshot(entry.source_id, html, fetched_at)

        return ScrapeResult(
            source_id=entry.source_id,
            url=entry.url,
            status="success",
            http_status=http_status,
            html=html,
            content_hash=content_hash,
            fetched_at=fetched_at,
            changed=changed,
        )

    def _fetch_with_retries(self, url: str) -> tuple[str, int]:
        last_error: Optional[Exception] = None
        attempts = self.config.max_retries + 1

        for attempt in range(attempts):
            try:
                return self._fetch_once(url)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if status < 500 or attempt >= attempts - 1:
                    raise
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise

            backoff = self.config.retry_backoff_seconds[
                min(attempt, len(self.config.retry_backoff_seconds) - 1)
            ]
            logger.warning(
                "Retry %s/%s for %s after %.1fs",
                attempt + 1,
                self.config.max_retries,
                url,
                backoff,
            )
            time.sleep(backoff)

        raise RuntimeError(f"Failed to fetch {url}") from last_error

    def _fetch_once(self, url: str) -> tuple[str, int]:
        headers = {"User-Agent": self.config.user_agent, "Accept": "text/html"}
        with httpx.Client(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            if not _is_html_response(response.headers.get("content-type")):
                raise ValueError(
                    f"Non-HTML response: {response.headers.get('content-type')}"
                )

            return response.text, response.status_code

    def _save_raw_snapshot(self, source_id: str, html: str, fetched_at: str) -> None:
        date_str = fetched_at[:10]
        snapshot_dir = self.project_root / self.config.raw_snapshot_dir / source_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{date_str}.html"
        snapshot_path.write_text(html, encoding="utf-8")
        logger.info("Saved raw snapshot: %s", snapshot_path)
