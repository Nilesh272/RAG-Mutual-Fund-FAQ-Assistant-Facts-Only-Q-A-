from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from phases.phase1_corpus.registry.source_registry import SourceRegistryService
from phases.phase2_rag_core.retrieval.context_assembler import ContextAssembler
from phases.phase2_rag_core.retrieval.hybrid_retriever import HybridRetriever
from phases.phase2_rag_core.retrieval.query_enhancer import QueryEnhancer
from phases.phase3_generation.compliance.link_registry import ComplianceLinkRegistry
from phases.phase3_generation.generation.generator import GenerationService
from phases.phase3_generation.generation.models import GeneratedResponse
from phases.phase3_generation.intent.classifier import IntentClassifier
from phases.phase3_generation.intent.models import Intent
from phases.phase3_generation.refusal.handler import RefusalHandler
from phases.phase3_generation.validation.response_validator import ResponseValidator
from phases.phase4_api.pii_scanner import contains_pii
from phases.phase4_api.session.models import ChatMessage, Thread

logger = logging.getLogger(__name__)

_REFUSAL_INTENTS: set[Intent] = {"ADVISORY", "COMPARATIVE", "OUT_OF_SCOPE"}


@dataclass(frozen=True)
class ChatResult:
    thread_id: str
    answer: str
    citation: str
    last_updated: str | None
    intent: str
    formatted_answer: str


class ChatOrchestrator:
    """End-to-end query pipeline (architecture §6)."""

    def __init__(
        self,
        *,
        retriever: HybridRetriever,
        classifier: IntentClassifier,
        generator: GenerationService,
        validator: ResponseValidator,
        refusal_handler: RefusalHandler,
        query_enhancer: QueryEnhancer,
        sources_path: Path,
        max_regeneration_attempts: int = 2,
    ) -> None:
        self.retriever = retriever
        self.classifier = classifier
        self.generator = generator
        self.validator = validator
        self.refusal_handler = refusal_handler
        self.query_enhancer = query_enhancer
        self.sources_path = sources_path
        self.max_regeneration_attempts = max_regeneration_attempts
        self.context_assembler = ContextAssembler()
        self._default_scheme_url = self._first_scheme_url(sources_path)

    @classmethod
    def from_config_files(cls, project_root: Path) -> ChatOrchestrator:
        root = project_root
        retriever = HybridRetriever.from_config_files(
            embedding_config_path=root / "config" / "embedding.yaml",
            retrieval_config_path=root / "config" / "retrieval.yaml",
            sources_path=root / "config" / "sources.yaml",
            project_root=root,
        )
        compliance = ComplianceLinkRegistry.from_config_file(
            root / "config" / "compliance_links.yaml"
        )
        import yaml

        with (root / "config" / "generation.yaml").open(encoding="utf-8") as f:
            gen_cfg = yaml.safe_load(f).get("generation", {})

        return cls(
            retriever=retriever,
            classifier=IntentClassifier(sources_path=root / "config" / "sources.yaml"),
            generator=GenerationService.from_config_file(root / "config" / "generation.yaml"),
            validator=ResponseValidator(
                sources_path=root / "config" / "sources.yaml",
                compliance=compliance,
                max_sentences=int(gen_cfg.get("max_sentences", 3)),
            ),
            refusal_handler=RefusalHandler(compliance),
            query_enhancer=QueryEnhancer(sources_path=root / "config" / "sources.yaml"),
            sources_path=root / "config" / "sources.yaml",
            max_regeneration_attempts=int(gen_cfg.get("max_regeneration_attempts", 2)),
        )

    def handle_message(self, thread: Thread, message: str) -> ChatResult:
        if contains_pii(message):
            refusal = self.refusal_handler.build("OUT_OF_SCOPE")
            return self._finalize(thread, message, refusal.answer, refusal.citation, None, refusal.intent)

        query = self._rewrite_follow_up(thread, message)
        classification = self.classifier.classify(query)
        intent = classification.intent

        if intent in _REFUSAL_INTENTS:
            refusal = self.refusal_handler.build(intent)
            return self._finalize(
                thread, message, refusal.answer, refusal.citation, None, refusal.intent
            )

        _, source_id, scheme_name = self.query_enhancer.enhance(query)
        if scheme_name:
            thread.scheme_name = scheme_name
        if source_id:
            thread.source_id = source_id

        scheme_url = self._scheme_url(source_id) or self._default_scheme_url

        if intent == "PERFORMANCE":
            response = self.generator.performance_response(scheme_url)
            return self._finalize(
                thread,
                message,
                response.answer,
                response.citation,
                response.last_updated,
                response.intent,
            )

        hits = self.retriever.retrieve(query)
        if not hits:
            response = self.generator.not_found_response(
                scheme_url,
                last_updated=self.context_assembler.latest_indexed_at(hits),
            )
            return self._finalize(
                thread,
                message,
                response.answer,
                response.citation,
                response.last_updated,
                response.intent,
            )

        context = self.context_assembler.assemble(hits)
        response = self.generator.generate_factual(query=query, chunks=hits, intent=intent)
        validation = self.validator.validate(response, context_text=context)

        attempts = 0
        while not validation.passed and attempts < self.max_regeneration_attempts:
            attempts += 1
            logger.warning("Validation failed (attempt %s): %s", attempts, validation.issues)
            response = self.generator.not_found_response(
                response.citation,
                last_updated=response.last_updated,
            )
            validation = self.validator.validate(response, context_text=context)

        return self._finalize(
            thread,
            message,
            response.answer,
            response.citation,
            response.last_updated,
            response.intent,
        )

    def _rewrite_follow_up(self, thread: Thread, message: str) -> str:
        _, _, scheme_name = self.query_enhancer.enhance(message)
        if thread.scheme_name and not scheme_name:
            return f"{message} ({thread.scheme_name})"
        return message

    def _finalize(
        self,
        thread: Thread,
        user_message: str,
        answer: str,
        citation: str,
        last_updated: str | None,
        intent: str,
    ) -> ChatResult:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        thread.add_message(ChatMessage(role="user", content=user_message, timestamp=now))
        formatted = self._format_response(answer, citation, last_updated)
        thread.add_message(
            ChatMessage(
                role="assistant",
                content=formatted,
                timestamp=now,
                citation=citation,
                intent=intent,
            )
        )
        return ChatResult(
            thread_id=thread.thread_id,
            answer=answer,
            citation=citation,
            last_updated=last_updated,
            intent=intent,
            formatted_answer=formatted,
        )

    @staticmethod
    def _format_response(answer: str, citation: str, last_updated: str | None) -> str:
        date_str = last_updated[:10] if last_updated else "unknown"
        return (
            f"{answer}\n\n"
            f"Source: {citation}\n\n"
            f"Last updated from sources: {date_str}"
        )

    def _scheme_url(self, source_id: str | None) -> str | None:
        if not source_id:
            return None
        registry = SourceRegistryService(sources_path=self.sources_path)
        entry = registry.get_by_id(source_id)
        return entry.url if entry else None

    @staticmethod
    def _first_scheme_url(sources_path: Path) -> str:
        registry = SourceRegistryService(sources_path=sources_path)
        entries = registry.get_allowlisted_urls()
        return entries[0].url if entries else "https://groww.in/mutual-funds"

    def health_status(self) -> dict:
        chunk_count = self.retriever.embedder.vector_store.count()
        return {
            "status": "ok" if chunk_count > 0 else "degraded",
            "indexed_chunks": chunk_count,
            "collection": self.retriever.embedder.vector_store.config.collection,
        }
