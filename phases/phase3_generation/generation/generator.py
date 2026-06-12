from __future__ import annotations

import os
from pathlib import Path

import yaml

from phases.phase2_rag_core.retrieval.context_assembler import ContextAssembler
from phases.phase2_rag_core.retrieval.models import RetrievedChunk
from phases.phase3_generation.generation.extractive_generator import ExtractiveGenerator
from phases.phase3_generation.generation.models import GeneratedResponse
from phases.phase3_generation.generation.openai_generator import OpenAIGenerator
from phases.phase3_generation.intent.models import Intent


class GenerationService:
    """Constrained answer generation (architecture §7)."""

    def __init__(
        self,
        *,
        provider: str = "extractive",
        model: str = "gpt-4o-mini",
        context_assembler: ContextAssembler | None = None,
    ) -> None:
        self.provider = provider
        self.context_assembler = context_assembler or ContextAssembler()
        extractive = ExtractiveGenerator()
        if provider == "openai":
            self._backend = OpenAIGenerator(model=model, fallback=extractive)
        else:
            self._backend = extractive

    @classmethod
    def from_config_file(cls, path: Path) -> GenerationService:
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f).get("generation", {})
        provider = os.getenv("GENERATION_PROVIDER", raw.get("provider", "extractive"))
        return cls(
            provider=provider,
            model=raw.get("model", "gpt-4o-mini"),
        )

    def performance_response(self, scheme_url: str) -> GeneratedResponse:
        return GeneratedResponse(
            answer=(
                "For historical performance data, please refer to the scheme page. "
                "I can only share factual scheme details from the indexed Groww pages, "
                "not performance analysis."
            ),
            citation=scheme_url,
            last_updated=None,
            intent="PERFORMANCE",
        )

    def not_found_response(self, scheme_url: str, last_updated: str | None = None) -> GeneratedResponse:
        return GeneratedResponse(
            answer=(
                "I couldn't verify this from the indexed Groww pages. "
                "Please refer to the scheme page for the latest information."
            ),
            citation=scheme_url,
            last_updated=last_updated,
            intent="FACTUAL_SCHEME",
        )

    def generate_factual(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        intent: Intent = "FACTUAL_SCHEME",
    ) -> GeneratedResponse:
        context = self.context_assembler.assemble(chunks)
        citation = self.context_assembler.primary_source_url(chunks) or ""
        last_updated = self.context_assembler.latest_indexed_at(chunks)

        if isinstance(self._backend, OpenAIGenerator):
            return self._backend.generate(
                query=query,
                chunks=chunks,
                context=context,
                citation=citation,
                last_updated=last_updated,
                intent=intent,
            )

        return self._backend.generate(
            query=query,
            chunks=chunks,
            citation=citation,
            last_updated=last_updated,
            intent=intent,
        )
