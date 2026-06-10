from __future__ import annotations

from urllib.parse import urlparse

from phases.phase1_corpus.registry.models import SourceEntry
from phases.phase1_corpus.scraping.models import ScrapingConfig


class AllowlistError(ValueError):
    """Raised when a URL is not on the allowlist."""


class AllowlistValidator:
    """Enforces exact URL allowlist and domain/path rules from architecture."""

    def __init__(
        self,
        allowed_entries: list[SourceEntry],
        config: ScrapingConfig,
    ) -> None:
        self._allowed_urls = {entry.url.rstrip("/") for entry in allowed_entries}
        self._allowed_by_id = {entry.source_id: entry for entry in allowed_entries}
        self.config = config

    def validate_url(self, url: str) -> None:
        normalized = url.rstrip("/")
        parsed = urlparse(normalized)

        if parsed.scheme not in ("http", "https"):
            raise AllowlistError(f"Invalid scheme for URL: {url}")

        if parsed.netloc != self.config.allowed_domain:
            raise AllowlistError(
                f"Domain not allowed: {parsed.netloc} (expected {self.config.allowed_domain})"
            )

        if not parsed.path.startswith(self.config.allowed_path_prefix):
            raise AllowlistError(
                f"Path not allowed: {parsed.path} "
                f"(expected prefix {self.config.allowed_path_prefix})"
            )

        if normalized not in self._allowed_urls:
            raise AllowlistError(f"URL not in Source Registry allowlist: {url}")

    def get_entry_for_url(self, url: str) -> SourceEntry:
        self.validate_url(url)
        normalized = url.rstrip("/")
        for entry in self._allowed_by_id.values():
            if entry.url.rstrip("/") == normalized:
                return entry
        raise AllowlistError(f"URL not in Source Registry allowlist: {url}")

    def get_entry(self, source_id: str) -> SourceEntry:
        if source_id not in self._allowed_by_id:
            raise AllowlistError(f"Unknown source_id: {source_id}")
        return self._allowed_by_id[source_id]
