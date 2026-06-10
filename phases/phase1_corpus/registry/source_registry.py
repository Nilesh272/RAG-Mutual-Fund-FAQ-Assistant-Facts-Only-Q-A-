from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import yaml

from phases.phase1_corpus.registry.models import SourceEntry, SourceRegistry


class SourceRegistryService:
    """Loads allowlisted sources and persists scrape metadata (hashes, last_fetched)."""

    def __init__(
        self,
        sources_path: Path,
        metadata_path: Optional[Path] = None,
    ) -> None:
        self.sources_path = sources_path
        self.metadata_path = metadata_path or Path("data/metadata/source_state.json")
        self._registry: Optional[SourceRegistry] = None
        self._metadata: dict[str, dict] = {}

    def load(self) -> SourceRegistry:
        if self._registry is not None:
            return self._registry

        with self.sources_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        sources = [
            SourceEntry(
                source_id=item["source_id"],
                url=item["url"].rstrip("/"),
                document_type=item.get("document_type", "scheme_page"),
                scheme_name=item["scheme_name"],
                scheme_category=item["scheme_category"],
                plan_type=item.get("plan_type", "Direct Growth"),
                content_format=raw.get("content_format", "html"),
                language=raw.get("language", "en"),
                amc=raw.get("amc", "HDFC Mutual Fund"),
            )
            for item in raw["sources"]
        ]

        self._registry = SourceRegistry(
            amc=raw.get("amc", "HDFC Mutual Fund"),
            language=raw.get("language", "en"),
            content_format=raw.get("content_format", "html"),
            sources=sources,
        )
        self._load_metadata()
        return self._registry

    def get_allowlisted_urls(self) -> list[SourceEntry]:
        registry = self.load()
        return list(registry.sources)

    def get_by_id(self, source_id: str) -> Optional[SourceEntry]:
        for entry in self.get_allowlisted_urls():
            if entry.source_id == source_id:
                return entry
        return None

    def get_allowlisted_url_set(self) -> set[str]:
        return {entry.url.rstrip("/") for entry in self.get_allowlisted_urls()}

    def get_stored_hash(self, source_id: str) -> Optional[str]:
        self._load_metadata()
        state = self._metadata.get(source_id, {})
        return state.get("content_hash")

    def get_last_fetched(self, source_id: str) -> Optional[str]:
        self._load_metadata()
        state = self._metadata.get(source_id, {})
        return state.get("last_fetched")

    def update_source_state(
        self,
        source_id: str,
        *,
        content_hash: str,
        last_fetched: str,
        http_status: int,
    ) -> None:
        self._load_metadata()
        self._metadata[source_id] = {
            "content_hash": content_hash,
            "last_fetched": last_fetched,
            "last_http_status": http_status,
        }
        self._save_metadata()

    def _load_metadata(self) -> None:
        if self._metadata:
            return
        if self.metadata_path.exists():
            with self.metadata_path.open(encoding="utf-8") as f:
                self._metadata = json.load(f)
        else:
            self._metadata = {}

    def _save_metadata(self) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with self.metadata_path.open("w", encoding="utf-8") as f:
            json.dump(self._metadata, f, indent=2)
