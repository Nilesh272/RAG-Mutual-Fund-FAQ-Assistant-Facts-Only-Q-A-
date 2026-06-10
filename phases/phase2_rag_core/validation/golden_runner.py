from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from phases.phase2_rag_core.retrieval.hybrid_retriever import HybridRetriever

GOLDEN_QUERIES: list[tuple[str, str]] = [
    ("expense ratio of HDFC Large Cap Fund", "expense_ratio"),
    ("exit load HDFC Mid Cap", "exit_load"),
    ("minimum SIP HDFC Focused Fund", "minimum_investment"),
    ("ELSS lock-in period", "lock_in_period"),
    ("benchmark of HDFC Equity Fund", "benchmark"),
]


@dataclass
class GoldenQueryResult:
    query: str
    expected_section_key: str
    top_section_key: str | None
    top_score: float | None
    passed: bool


@dataclass
class GoldenQueryReport:
    passed: bool
    total: int
    passed_count: int
    results: list[GoldenQueryResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "total": self.total,
            "passed_count": self.passed_count,
            "results": [
                {
                    "query": r.query,
                    "expected_section_key": r.expected_section_key,
                    "top_section_key": r.top_section_key,
                    "top_score": r.top_score,
                    "passed": r.passed,
                }
                for r in self.results
            ],
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


class GoldenQueryRunner:
    """Golden query smoke tests per chunking-embedding-architecture §8.3."""

    def __init__(self, retriever: HybridRetriever) -> None:
        self.retriever = retriever

    def run(self, queries: list[tuple[str, str]] | None = None) -> GoldenQueryReport:
        self.retriever.refresh_sparse_index()
        pairs = queries or GOLDEN_QUERIES
        results: list[GoldenQueryResult] = []

        for query, expected_section in pairs:
            hits = self.retriever.retrieve(query)
            top = hits[0] if hits else None
            top_section = top.section_key if top else None
            results.append(
                GoldenQueryResult(
                    query=query,
                    expected_section_key=expected_section,
                    top_section_key=top_section,
                    top_score=top.final_score if top else None,
                    passed=top_section == expected_section,
                )
            )

        passed_count = sum(1 for result in results if result.passed)
        return GoldenQueryReport(
            passed=passed_count == len(results),
            total=len(results),
            passed_count=passed_count,
            results=results,
        )
