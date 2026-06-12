from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from phases.phase1_corpus.registry.source_registry import SourceRegistryService
from phases.phase2_rag_core.embedding.vector_store import VectorStore
from phases.phase2_rag_core.validation.golden_runner import GOLDEN_QUERIES

if TYPE_CHECKING:
    from phases.phase2_rag_core.embedding.embedder import EmbeddingService

logger = logging.getLogger(__name__)

KNOWN_SECTIONS = {
    "fund_overview",
    "expense_ratio",
    "exit_load",
    "minimum_investment",
    "lock_in_period",
    "riskometer",
    "benchmark",
    "fund_manager",
    "aum",
    "investment_objective",
}


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class ValidationReport:
    passed: bool
    total_points: int
    checks: list[ValidationCheck] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "total_points": self.total_points,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail} for c in self.checks
            ],
        }


class IngestValidator:
    """Post-ingest validation per chunking-embedding-architecture §8.2 and §10.5."""

    def __init__(self, vector_store: VectorStore, sources_path: Path) -> None:
        self.vector_store = vector_store
        self.registry = SourceRegistryService(sources_path=sources_path)
        self.allowlisted_urls = self.registry.get_allowlisted_url_set()

    def validate(
        self,
        *,
        embedder: Optional[EmbeddingService] = None,
        expected_min_chunks: int = 1,
        expected_max_chunks: int = 60,
        full_corpus: bool = True,
        run_dense_smoke: bool = True,
    ) -> ValidationReport:
        checks: list[ValidationCheck] = []

        checks.append(
            ValidationCheck(
                name="chroma_backend_mode",
                passed=self.vector_store.mode in {"cloud", "ephemeral"},
                detail=f"mode={self.vector_store.mode} (cloud or ephemeral for tests)",
            )
        )

        reachable = self.vector_store.health_check()
        checks.append(
            ValidationCheck(
                name="chroma_collection_reachable",
                passed=reachable,
                detail=(
                    f"collection {self.vector_store.collection_name} "
                    f"via {self.vector_store.mode}"
                ),
            )
        )

        if not reachable:
            return ValidationReport(passed=False, total_points=0, checks=checks)

        chunks = self.vector_store.get_all_chunks()
        total = len(chunks)
        checks.append(
            ValidationCheck(
                name="index_non_empty",
                passed=total >= expected_min_chunks,
                detail=f"{total} points indexed (min {expected_min_chunks})",
            )
        )

        invalid_urls = [
            chunk["payload"].get("source_url")
            for chunk in chunks
            if not chunk["payload"].get("source_url")
            or chunk["payload"]["source_url"].rstrip("/") not in self.allowlisted_urls
        ]
        checks.append(
            ValidationCheck(
                name="allowlisted_source_urls",
                passed=len(invalid_urls) == 0,
                detail=f"{len(invalid_urls)} invalid URLs" if invalid_urls else "all URLs allowlisted",
            )
        )

        unknown_sections = sorted(
            {
                chunk["payload"].get("section_key")
                for chunk in chunks
                if chunk["payload"].get("section_key") not in KNOWN_SECTIONS
            }
        )
        if unknown_sections:
            logger.warning("New section keys detected: %s", unknown_sections)
        checks.append(
            ValidationCheck(
                name="known_or_logged_sections",
                passed=True,
                detail="unknown sections: " + (", ".join(unknown_sections) if unknown_sections else "none"),
            )
        )

        per_source = {entry.source_id: 0 for entry in self.registry.get_allowlisted_urls()}
        for chunk in chunks:
            sid = chunk["payload"].get("source_id")
            if sid in per_source:
                per_source[sid] += 1

        empty_sources = [sid for sid, count in per_source.items() if count == 0]
        if full_corpus:
            checks.append(
                ValidationCheck(
                    name="scheme_coverage",
                    passed=len(empty_sources) == 0,
                    detail=(
                        f"missing sources: {empty_sources}"
                        if empty_sources
                        else "all 5 schemes indexed"
                    ),
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="scheme_coverage",
                    passed=True,
                    detail=f"partial ingest ({len(per_source) - len(empty_sources)}/{len(per_source)} schemes)",
                )
            )

        expense_count = self.vector_store.count_by_metadata({"section_key": "expense_ratio"})
        checks.append(
            ValidationCheck(
                name="metadata_filter_expense_ratio",
                passed=expense_count >= 1,
                detail=f"{expense_count} expense_ratio chunk(s)",
            )
        )

        if full_corpus and not empty_sources:
            sane_min = min(45, len(per_source) * 3)
            in_corpus_range = sane_min <= total <= expected_max_chunks
            ideal = 45 <= total <= expected_max_chunks
            detail = f"{total} chunks (range {sane_min}–{expected_max_chunks}"
            if not ideal and in_corpus_range:
                detail += "; below ideal 45 for live Groww pages"
            detail += ")"
            checks.append(
                ValidationCheck(
                    name="corpus_size_range",
                    passed=in_corpus_range,
                    detail=detail,
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="corpus_size_range",
                    passed=total >= expected_min_chunks,
                    detail=f"{total} chunks (full corpus check skipped)",
                )
            )

        semantic_embedder = os.getenv("EMBEDDING_PROVIDER", "bge") != "hash"
        if full_corpus and run_dense_smoke and semantic_embedder and embedder is not None and total > 0:
            smoke_query, expected_section = GOLDEN_QUERIES[0]
            hits = embedder.search(smoke_query, limit=1)
            top_section = hits[0]["payload"].get("section_key") if hits else None
            checks.append(
                ValidationCheck(
                    name="dense_query_smoke",
                    passed=top_section == expected_section,
                    detail=(
                        f"query={smoke_query!r} top_section={top_section!r} "
                        f"expected={expected_section!r}"
                    ),
                )
            )

        passed = all(check.passed for check in checks if check.name != "known_or_logged_sections")
        return ValidationReport(passed=passed, total_points=total, checks=checks)
