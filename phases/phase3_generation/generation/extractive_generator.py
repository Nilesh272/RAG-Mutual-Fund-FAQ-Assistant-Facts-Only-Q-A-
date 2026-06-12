from __future__ import annotations

import re

from phases.phase2_rag_core.retrieval.models import RetrievedChunk
from phases.phase3_generation.generation.fact_extractor import extract_fact, is_definition_text
from phases.phase3_generation.generation.models import GeneratedResponse
from phases.phase3_generation.intent.models import Intent


def _first_sentences(text: str, max_sentences: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [p for p in parts if p][:max_sentences]
    return " ".join(kept) if kept else text.strip()[:400]


class ExtractiveGenerator:
    """Facts-only answers from retrieved chunks (no LLM required)."""

    def generate(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        citation: str,
        last_updated: str | None,
        intent: Intent = "FACTUAL_SCHEME",
    ) -> GeneratedResponse:
        if not chunks:
            return GeneratedResponse(
                answer=(
                    "I could not find that information on the indexed Groww scheme pages. "
                    "Please refer to the scheme page for the latest details."
                ),
                citation=citation,
                last_updated=last_updated,
                intent=intent,
            )

        scheme = chunks[0].scheme_name
        fact: str | None = None
        for chunk in chunks:
            if is_definition_text(chunk.text):
                continue
            fact = extract_fact(
                query=query, text=chunk.text, section_key=chunk.section_key
            )
            if fact:
                break

        if fact:
            answer = f"For {scheme}, {fact[0].lower()}{fact[1:]}"
        else:
            answer = (
                f"I couldn't verify this from the indexed Groww pages. "
                f"Please refer to the {scheme} scheme page for the latest expense ratio."
                if "expense ratio" in query.lower()
                else (
                    f"Factual details for {scheme} are listed on the "
                    "indexed Groww scheme page."
                )
            )
        if not answer.endswith("."):
            answer += "."

        return GeneratedResponse(
            answer=answer,
            citation=citation or top.source_url,
            last_updated=last_updated or top.indexed_at,
            intent=intent,
        )
