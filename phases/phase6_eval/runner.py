from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from phases.phase3_generation.intent.classifier import IntentClassifier
from phases.phase4_api.orchestrator import ChatOrchestrator
from phases.phase4_api.session.models import Thread


@dataclass
class EvalCaseResult:
    query: str
    category: str
    expected_intent: str
    actual_intent: str
    must_refuse: bool
    refused: bool
    citation_valid: bool
    passed: bool


@dataclass
class EvalReport:
    total: int
    passed: int
    refused_correct: int
    intent_correct: int
    results: list[EvalCaseResult] = field(default_factory=list)

    @property
    def passed_all(self) -> bool:
        return self.passed == self.total

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "refused_correct": self.refused_correct,
            "intent_correct": self.intent_correct,
            "pass_rate": round(self.passed / self.total, 4) if self.total else 0,
            "results": [
                {
                    "query": r.query,
                    "category": r.category,
                    "expected_intent": r.expected_intent,
                    "actual_intent": r.actual_intent,
                    "must_refuse": r.must_refuse,
                    "refused": r.refused,
                    "citation_valid": r.citation_valid,
                    "passed": r.passed,
                }
                for r in self.results
            ],
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)


class EvalRunner:
    """Run labeled eval set against intent + chat pipeline."""

    def __init__(
        self,
        orchestrator: ChatOrchestrator,
        classifier: IntentClassifier,
        sources_path: Path,
    ) -> None:
        self.orchestrator = orchestrator
        self.classifier = classifier
        self._groww_urls = {
            s.url.rstrip("/")
            for s in __import__(
                "phases.phase1_corpus.registry.source_registry",
                fromlist=["SourceRegistryService"],
            ).SourceRegistryService(sources_path=sources_path).get_allowlisted_urls()
        }

    @classmethod
    def from_project_root(cls, project_root: Path) -> EvalRunner:
        orchestrator = ChatOrchestrator.from_config_files(project_root)
        classifier = IntentClassifier(sources_path=project_root / "config" / "sources.yaml")
        return cls(
            orchestrator,
            classifier,
            sources_path=project_root / "config" / "sources.yaml",
        )

    def run(self, dataset_path: Path) -> EvalReport:
        with dataset_path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        results: list[EvalCaseResult] = []
        refused_correct = 0
        intent_correct = 0

        for category, cases in raw.get("categories", {}).items():
            for case in cases:
                query = case["query"]
                expected_intent = case["expected_intent"]
                must_refuse = bool(case.get("must_refuse", False))

                classification = self.classifier.classify(query)
                intent_match = classification.intent == expected_intent
                if intent_match:
                    intent_correct += 1

                thread = Thread.create()
                chat = self.orchestrator.handle_message(thread, query)
                refused = chat.intent in {"ADVISORY", "COMPARATIVE", "OUT_OF_SCOPE"}
                if must_refuse == refused:
                    refused_correct += 1

                citation = chat.citation.rstrip("/")
                citation_valid = citation in self._groww_urls or "amfi" in citation or "sebi" in citation

                passed = intent_match and (must_refuse == refused) and citation_valid
                results.append(
                    EvalCaseResult(
                        query=query,
                        category=category,
                        expected_intent=expected_intent,
                        actual_intent=chat.intent,
                        must_refuse=must_refuse,
                        refused=refused,
                        citation_valid=citation_valid,
                        passed=passed,
                    )
                )

        passed_count = sum(1 for r in results if r.passed)
        return EvalReport(
            total=len(results),
            passed=passed_count,
            refused_correct=refused_correct,
            intent_correct=intent_correct,
            results=results,
        )
