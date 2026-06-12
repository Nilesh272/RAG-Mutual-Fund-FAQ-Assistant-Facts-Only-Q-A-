from __future__ import annotations

import logging
import os

import httpx

from phases.phase2_rag_core.retrieval.models import RetrievedChunk
from phases.phase3_generation.generation.extractive_generator import ExtractiveGenerator
from phases.phase3_generation.generation.models import GeneratedResponse
from phases.phase3_generation.generation.prompts import SYSTEM_PROMPT, build_user_prompt
from phases.phase3_generation.intent.models import Intent

logger = logging.getLogger(__name__)


class OpenAIGenerator:
    """Optional LLM generation via OpenAI chat completions."""

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        fallback: ExtractiveGenerator | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.fallback = fallback or ExtractiveGenerator()

    def generate(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        context: str,
        citation: str,
        last_updated: str | None,
        intent: Intent = "FACTUAL_SCHEME",
    ) -> GeneratedResponse:
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set; using extractive generator")
            return self.fallback.generate(
                query=query,
                chunks=chunks,
                citation=citation,
                last_updated=last_updated,
                intent=intent,
            )

        user_prompt = build_user_prompt(
            query=query,
            context=context,
            scheme_url=citation,
        )
        try:
            answer_text = self._call_openai(user_prompt)
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAI generation failed: %s", exc)
            return self.fallback.generate(
                query=query,
                chunks=chunks,
                citation=citation,
                last_updated=last_updated,
                intent=intent,
            )

        return GeneratedResponse(
            answer=answer_text.strip(),
            citation=citation,
            last_updated=last_updated,
            intent=intent,
        )

    def _call_openai(self, user_prompt: str) -> str:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": 0.1,
                "max_tokens": 200,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
