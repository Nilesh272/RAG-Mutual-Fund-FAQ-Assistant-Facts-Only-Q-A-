from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Intent = Literal[
    "FACTUAL_SCHEME",
    "FACTUAL_PROCESS",
    "PERFORMANCE",
    "ADVISORY",
    "COMPARATIVE",
    "OUT_OF_SCOPE",
]


@dataclass(frozen=True)
class ClassificationResult:
    intent: Intent
    confidence: float
    matched_pattern: str | None = None
