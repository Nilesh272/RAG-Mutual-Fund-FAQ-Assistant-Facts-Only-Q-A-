from __future__ import annotations

import re
from pathlib import Path

from phases.phase1_corpus.registry.source_registry import SourceRegistryService
from phases.phase3_generation.intent.models import ClassificationResult, Intent

_ADVISORY_PATTERNS = (
    r"\bshould i\b",
    r"\bworth investing\b",
    r"\brecommend\b",
    r"\bi recommend\b",
    r"\bbuy or sell\b",
    r"\bgood time to invest\b",
    r"\binvest in this\b",
    r"\binvest now\b",
)

_COMPARATIVE_PATTERNS = (
    r"\bwhich fund is better\b",
    r"\bwhich is better\b",
    r"\bbest fund\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bor\b.+\bor\b",
)

_PERFORMANCE_PATTERNS = (
    r"\breturn(s)?\b",
    r"\bcagr\b",
    r"\bperformance\b",
    r"\blast year\b",
    r"\bnav\b",
    r"\bgains?\b",
    r"\bhow much did\b",
    r"\bannualized\b",
)

_OUT_OF_SCOPE_PATTERNS = (
    r"\bstock\b",
    r"\bcrypto\b",
    r"\bbitcoin\b",
    r"\bforex\b",
    r"\bipo\b",
)

_FACTUAL_KEYWORDS = (
    "expense ratio",
    "exit load",
    "minimum sip",
    "minimum investment",
    "lock-in",
    "lock in",
    "benchmark",
    "riskometer",
    "statement",
    "tax",
    "sip",
    "ter",
)


class IntentClassifier:
    """Rule-based intent classifier (architecture §6.2)."""

    def __init__(self, sources_path: Path) -> None:
        registry = SourceRegistryService(sources_path=sources_path)
        self._scheme_aliases = self._build_scheme_aliases(registry)

    def classify(self, message: str) -> ClassificationResult:
        text = re.sub(r"\s+", " ", message.strip().lower())
        if not text:
            return ClassificationResult("OUT_OF_SCOPE", 1.0, "empty")

        for pattern in _ADVISORY_PATTERNS:
            if re.search(pattern, text):
                return ClassificationResult("ADVISORY", 0.95, pattern)

        for pattern in _COMPARATIVE_PATTERNS:
            if re.search(pattern, text):
                return ClassificationResult("COMPARATIVE", 0.95, pattern)

        for pattern in _OUT_OF_SCOPE_PATTERNS:
            if re.search(pattern, text):
                return ClassificationResult("OUT_OF_SCOPE", 0.9, pattern)

        for pattern in _PERFORMANCE_PATTERNS:
            if re.search(pattern, text):
                return ClassificationResult("PERFORMANCE", 0.85, pattern)

        factual_signal = any(kw in text for kw in _FACTUAL_KEYWORDS)
        in_scope_scheme = self._mentions_in_scope_scheme(text)

        if factual_signal or in_scope_scheme:
            if not in_scope_scheme and "hdfc" not in text:
                return ClassificationResult("OUT_OF_SCOPE", 0.85, "factual_but_out_of_scope")
            if any(kw in text for kw in ("statement", "download", "tax report", "capital gains")):
                return ClassificationResult("FACTUAL_PROCESS", 0.8, "process_keyword")
            return ClassificationResult("FACTUAL_SCHEME", 0.8, "scheme_or_factual_keyword")

        return ClassificationResult("OUT_OF_SCOPE", 0.7, "no_match")

    def _mentions_in_scope_scheme(self, text: str) -> bool:
        return any(alias in text for alias in self._scheme_aliases)

    @staticmethod
    def _build_scheme_aliases(registry: SourceRegistryService) -> list[str]:
        aliases: set[str] = set()
        for entry in registry.get_allowlisted_urls():
            aliases.add(entry.scheme_name.lower())
            aliases.add(entry.source_id.replace("-", " "))
            short = entry.scheme_name.lower().replace(" direct growth", "")
            aliases.add(short)
            aliases.add(short.replace(" direct plan growth", ""))
            if "hdfc" not in short:
                aliases.add(f"hdfc {short}")
        aliases.add("hdfc")
        return sorted(aliases, key=len, reverse=True)
