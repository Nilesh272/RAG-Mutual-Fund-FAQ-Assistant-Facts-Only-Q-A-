from __future__ import annotations

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from phases.phase1_corpus.scraping.models import ScrapeResult
from phases.phase2_rag_core.parsing.models import SectionBlock

logger = logging.getLogger(__name__)

HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

SECTION_RULES: list[tuple[str, str, list[str]]] = [
    ("fund_overview", "Fund Overview", [r"overview", r"about (the )?fund", r"fund details"]),
    ("expense_ratio", "Expense Ratio", [r"expense ratio", r"\bter\b", r"total expense"]),
    ("exit_load", "Exit Load", [r"exit load", r"redemption (fee|charge)", r"exit fee"]),
    ("minimum_investment", "Minimum Investment", [r"minimum (sip|investment)", r"min\.? sip", r"lumpsum"]),
    ("lock_in_period", "Lock-in Period", [r"lock[- ]?in", r"lockin"]),
    ("riskometer", "Riskometer", [r"riskometer", r"risk level", r"risk profile"]),
    ("benchmark", "Benchmark", [r"benchmark"]),
    ("fund_manager", "Fund Manager", [r"fund manager", r"managed by"]),
    ("aum", "AUM", [r"\baum\b", r"assets under management"]),
    ("investment_objective", "Investment Objective", [r"investment objective", r"objective of the scheme"]),
]

LABEL_KEY_MAP: list[tuple[str, list[str]]] = [
    ("expense_ratio", ["expense ratio", "ter"]),
    ("exit_load", ["exit load"]),
    ("minimum_investment", ["minimum sip", "min sip", "minimum investment", "min investment"]),
    ("lock_in_period", ["lock-in period", "lock in period", "lock-in"]),
    ("riskometer", ["riskometer", "risk level"]),
    ("benchmark", ["benchmark"]),
    ("fund_manager", ["fund manager"]),
    ("aum", ["aum", "assets under management"]),
]


class GrowwParser:
    """Extract structured SectionBlocks from Groww mutual fund HTML pages."""

    def parse(self, scrape_result: ScrapeResult, scheme_meta: dict) -> list[SectionBlock]:
        if not scrape_result.html:
            return []

        soup = BeautifulSoup(scrape_result.html, "html.parser")
        self._remove_noise(soup)

        sections: list[SectionBlock] = []
        sections.extend(self._parse_heading_sections(soup, scrape_result, scheme_meta))
        sections.extend(self._parse_label_value_pairs(soup, scrape_result, scheme_meta))

        if not sections:
            fallback = self._fallback_body_text(soup)
            if fallback:
                sections.append(self._make_block(
                    scrape_result, scheme_meta, "fund_overview", "Fund Overview", fallback
                ))

        return self._dedupe_sections(sections)

    def _make_block(
        self,
        scrape_result: ScrapeResult,
        scheme_meta: dict,
        section_key: str,
        section_heading: str,
        content: str,
        content_type: str = "text",
    ) -> SectionBlock:
        return SectionBlock(
            source_id=scrape_result.source_id,
            source_url=scrape_result.url,
            scheme_name=scheme_meta["scheme_name"],
            scheme_category=scheme_meta["scheme_category"],
            section_key=section_key,
            section_heading=section_heading,
            content=self._normalize_text(content),
            content_type=content_type,  # type: ignore[arg-type]
            content_hash=scrape_result.content_hash or "",
        )

    def _parse_heading_sections(
        self,
        soup: BeautifulSoup,
        scrape_result: ScrapeResult,
        scheme_meta: dict,
    ) -> list[SectionBlock]:
        sections: list[SectionBlock] = []
        root = soup.find("main") or soup.find("article") or soup.body or soup

        for heading in root.find_all(HEADING_TAGS):
            title = self._normalize_text(heading.get_text(" ", strip=True))
            if not title:
                continue

            section_key, canonical_heading = self._match_section(title)
            if section_key is None:
                continue

            content_parts: list[str] = []
            for sibling in heading.next_siblings:
                if isinstance(sibling, Tag) and sibling.name in HEADING_TAGS:
                    break
                text = self._extract_element_text(sibling)
                if text:
                    content_parts.append(text)

            content = "\n".join(content_parts).strip()
            if content:
                sections.append(
                    self._make_block(
                        scrape_result, scheme_meta, section_key, canonical_heading, content
                    )
                )

        return sections

    def _parse_label_value_pairs(
        self,
        soup: BeautifulSoup,
        scrape_result: ScrapeResult,
        scheme_meta: dict,
    ) -> list[SectionBlock]:
        sections: list[SectionBlock] = []
        seen_keys: set[str] = set()

        for dt in soup.find_all("dt"):
            label = self._normalize_text(dt.get_text(" ", strip=True))
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            value = self._normalize_text(dd.get_text(" ", strip=True))
            section_key = self._match_label(label)
            if section_key and value and section_key not in seen_keys:
                heading = next(h for k, h, _ in SECTION_RULES if k == section_key)
                sections.append(
                    self._make_block(
                        scrape_result, scheme_meta, section_key, heading, f"{label}: {value}"
                    )
                )
                seen_keys.add(section_key)

        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = self._normalize_text(cells[0].get_text(" ", strip=True))
            value = self._normalize_text(cells[1].get_text(" ", strip=True))
            section_key = self._match_label(label)
            if section_key and value and section_key not in seen_keys:
                heading = next(h for k, h, _ in SECTION_RULES if k == section_key)
                sections.append(
                    self._make_block(
                        scrape_result,
                        scheme_meta,
                        section_key,
                        heading,
                        f"{label}: {value}",
                        content_type="table",
                    )
                )
                seen_keys.add(section_key)

        return sections

    def _fallback_body_text(self, soup: BeautifulSoup) -> str:
        root = soup.find("main") or soup.find("article") or soup.body
        if not root:
            return ""
        return self._normalize_text(root.get_text("\n", strip=True))[:4000]

    @staticmethod
    def _remove_noise(soup: BeautifulSoup) -> None:
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()

    @staticmethod
    def _extract_element_text(element) -> str:
        if isinstance(element, NavigableString):
            return str(element).strip()
        if isinstance(element, Tag):
            if element.name == "table":
                return GrowwParser._table_to_text(element)
            return element.get_text("\n", strip=True)
        return ""

    @staticmethod
    def _table_to_text(table: Tag) -> str:
        rows: list[str] = []
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if cells:
                rows.append(" | ".join(cells))
        return "\n".join(rows)

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = text.replace("₹", "Rs ")
        return text.strip()

    @staticmethod
    def _match_section(heading: str) -> tuple[Optional[str], str]:
        lowered = heading.lower()
        for section_key, canonical, patterns in SECTION_RULES:
            for pattern in patterns:
                if re.search(pattern, lowered):
                    return section_key, canonical
        return None, heading

    @staticmethod
    def _match_label(label: str) -> Optional[str]:
        lowered = label.lower()
        for section_key, aliases in LABEL_KEY_MAP:
            for alias in aliases:
                if alias in lowered:
                    return section_key
        return None

    @staticmethod
    def _dedupe_sections(sections: list[SectionBlock]) -> list[SectionBlock]:
        """Keep one block per section_key (prefer richest content)."""
        best_by_key: dict[str, SectionBlock] = {}
        order: list[str] = []
        for section in sections:
            if section.section_key not in best_by_key:
                order.append(section.section_key)
                best_by_key[section.section_key] = section
                continue
            existing = best_by_key[section.section_key]
            if len(section.content) > len(existing.content):
                best_by_key[section.section_key] = section
        return [best_by_key[key] for key in order]
