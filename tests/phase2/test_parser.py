from phases.phase1_corpus.scraping.models import ScrapeResult
from phases.phase2_rag_core.parsing.groww_parser import GrowwParser


def test_parse_extracts_key_sections(sample_html: str) -> None:
    parser = GrowwParser()
    result = ScrapeResult(
        source_id="hdfc-large-cap-direct-growth",
        url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        status="success",
        http_status=200,
        html=sample_html,
        content_hash="hash123",
        fetched_at="2026-06-05T09:15:12+05:30",
    )
    scheme_meta = {
        "scheme_name": "HDFC Large Cap Fund Direct Growth",
        "scheme_category": "large-cap",
    }

    sections = parser.parse(result, scheme_meta)
    section_keys = {section.section_key for section in sections}

    assert "expense_ratio" in section_keys
    assert "exit_load" in section_keys
    assert "minimum_investment" in section_keys
    assert "riskometer" in section_keys
    assert "benchmark" in section_keys
