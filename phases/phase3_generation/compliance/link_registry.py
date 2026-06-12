from __future__ import annotations

from pathlib import Path

import yaml


class ComplianceLinkRegistry:
    """Static educational links for refusal responses (architecture §8)."""

    def __init__(self, links: dict[str, str]) -> None:
        self._links = links

    @classmethod
    def from_config_file(cls, path: Path) -> ComplianceLinkRegistry:
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls(raw.get("links", {}))

    def get(self, key: str) -> str | None:
        return self._links.get(key)

    @property
    def amfi_url(self) -> str:
        return self._links.get(
            "amfi_investor_awareness",
            "https://www.amfiindia.com/investor-awareness",
        )

    @property
    def sebi_url(self) -> str:
        return self._links.get(
            "sebi_investor_education",
            "https://www.sebi.gov.in/sebiweb/home/HomeAction.html?do=investor-education",
        )

    def all_urls(self) -> set[str]:
        return set(self._links.values())
