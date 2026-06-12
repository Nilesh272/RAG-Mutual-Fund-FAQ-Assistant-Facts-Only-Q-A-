from __future__ import annotations

from dataclasses import dataclass

from phases.phase3_generation.compliance.link_registry import ComplianceLinkRegistry
from phases.phase3_generation.intent.models import Intent


@dataclass(frozen=True)
class RefusalResponse:
    answer: str
    citation: str
    intent: Intent


class RefusalHandler:
    """Polite refusal templates with compliance links (architecture §8)."""

    def __init__(self, compliance: ComplianceLinkRegistry) -> None:
        self.compliance = compliance

    def build(self, intent: Intent) -> RefusalResponse:
        if intent == "ADVISORY":
            url = self.compliance.amfi_url
            answer = (
                "I can only answer factual questions about mutual fund schemes, "
                "not provide investment advice. For investor awareness, visit the AMFI link below."
            )
        elif intent == "COMPARATIVE":
            url = self.compliance.sebi_url
            answer = (
                "I cannot compare funds or suggest which is better. "
                "I can answer specific factual questions about individual schemes. "
                "Learn more at the SEBI investor education link below."
            )
        else:
            url = self.compliance.amfi_url
            answer = (
                "That question is outside my scope. I answer factual queries about "
                "five HDFC schemes using indexed Groww scheme pages only."
            )
        return RefusalResponse(answer=answer, citation=url, intent=intent)
