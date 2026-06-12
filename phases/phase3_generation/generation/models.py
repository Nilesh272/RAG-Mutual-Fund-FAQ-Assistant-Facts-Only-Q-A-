from __future__ import annotations

from dataclasses import dataclass

from phases.phase3_generation.intent.models import Intent


@dataclass(frozen=True)
class GeneratedResponse:
    answer: str
    citation: str
    last_updated: str | None
    intent: Intent
