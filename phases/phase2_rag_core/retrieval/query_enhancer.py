from __future__ import annotations

import re
from pathlib import Path

import yaml

from phases.phase1_corpus.registry.source_registry import SourceRegistryService


class QueryEnhancer:
    """Detect scheme mentions and expand abbreviations before retrieval."""

    def __init__(self, sources_path: Path) -> None:
        registry = SourceRegistryService(sources_path=sources_path)
        self._sources = registry.get_allowlisted_urls()
        self._aliases = self._build_aliases()

    def enhance(self, query: str) -> tuple[str, str | None, str | None]:
        normalized = re.sub(r"\s+", " ", query.strip())
        expanded = self._expand_abbreviations(normalized)
        source_id, scheme_name = self._detect_scheme(expanded)
        return expanded, source_id, scheme_name

    def _expand_abbreviations(self, query: str) -> str:
        replacements = {
            r"\bELSS\b": "ELSS Equity Linked Savings Scheme",
            r"\bSIP\b": "SIP systematic investment plan",
            r"\bTER\b": "TER total expense ratio",
        }
        result = query
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _detect_scheme(self, query: str) -> tuple[str | None, str | None]:
        lowered = query.lower()
        best_match: tuple[str | None, str | None] = (None, None)
        best_len = 0

        for source_id, aliases in self._aliases.items():
            for alias in aliases:
                if alias in lowered and len(alias) > best_len:
                    entry = next(s for s in self._sources if s.source_id == source_id)
                    best_match = (source_id, entry.scheme_name)
                    best_len = len(alias)

        return best_match

    def _build_aliases(self) -> dict[str, list[str]]:
        aliases: dict[str, list[str]] = {}
        for entry in self._sources:
            names = {
                entry.scheme_name.lower(),
                entry.scheme_name.lower().replace(" direct growth", ""),
                entry.scheme_name.lower().replace(" direct plan growth", ""),
                entry.source_id.replace("-", " "),
            }
            if "elss" in entry.source_id:
                names.add("hdfc elss")
                names.add("elss tax saver")
            if "large cap" in entry.source_id:
                names.add("hdfc large cap")
            if "mid cap" in entry.source_id:
                names.add("hdfc mid cap")
            if "focused" in entry.source_id:
                names.add("hdfc focused")
            if "equity" in entry.source_id and "elss" not in entry.source_id:
                names.add("hdfc equity fund")
            aliases[entry.source_id] = sorted(names, key=len, reverse=True)
        return aliases
