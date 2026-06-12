from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from phases.phase1_corpus.registry.source_registry import SourceRegistryService
from phases.phase3_generation.compliance.link_registry import ComplianceLinkRegistry
from phases.phase3_generation.generation.models import GeneratedResponse

_ADVISORY_PHRASES = (
    "you should invest",
    "i recommend",
    "better choice",
    "best fund",
    "buy this",
    "sell this",
)

_PERFORMANCE_PATTERNS = (
    r"\b\d+(\.\d+)?%\b",
    r"\bcagr\b",
    r"\bannualized return\b",
)

_PII_PATTERNS = (
    r"\b[A-Z]{5}\d{4}[A-Z]\b",  # PAN-like
    r"\b\d{12}\b",  # Aadhaar-like
    r"\b\d{10,16}\b",  # account-like
)

_URL_RE = re.compile(r"https?://[^\s)>\]]+")


@dataclass
class ValidationIssue:
    check: str
    message: str


@dataclass
class ValidationResult:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)


class ResponseValidator:
    """Post-generation guardrails (architecture §9)."""

    def __init__(
        self,
        *,
        sources_path: Path,
        compliance: ComplianceLinkRegistry,
        max_sentences: int = 3,
    ) -> None:
        registry = SourceRegistryService(sources_path=sources_path)
        self._allowed_urls = {s.url.rstrip("/") for s in registry.get_allowlisted_urls()}
        self._allowed_urls |= compliance.all_urls()
        self.max_sentences = max_sentences
        self.compliance = compliance

    def validate(
        self,
        response: GeneratedResponse,
        *,
        context_text: str = "",
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        text = response.answer

        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
        if len(sentences) > self.max_sentences:
            issues.append(
                ValidationIssue("sentence_count", f">{self.max_sentences} sentences")
            )

        urls_in_answer = _URL_RE.findall(text)
        if urls_in_answer:
            issues.append(ValidationIssue("citation_in_body", "URL embedded in answer body"))

        citation = response.citation.rstrip("/")
        if citation not in self._allowed_urls:
            issues.append(ValidationIssue("url_validity", f"Invalid citation: {citation}"))

        lowered = text.lower()
        for phrase in _ADVISORY_PHRASES:
            if phrase in lowered:
                issues.append(ValidationIssue("advisory_language", phrase))

        for pattern in _PERFORMANCE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(ValidationIssue("performance_data", pattern))

        for pattern in _PII_PATTERNS:
            if re.search(pattern, text):
                issues.append(ValidationIssue("pii_detection", pattern))

        if context_text and not self._is_grounded(text, context_text):
            issues.append(ValidationIssue("grounding", "Answer not grounded in context"))

        return ValidationResult(passed=len(issues) == 0, issues=issues)

    @staticmethod
    def _is_grounded(answer: str, context: str) -> bool:
        answer_tokens = {t for t in re.findall(r"[a-z0-9%]+", answer.lower()) if len(t) > 3}
        context_lower = context.lower()
        if not answer_tokens:
            return True
        overlap = sum(1 for t in answer_tokens if t in context_lower)
        return overlap / len(answer_tokens) >= 0.2
