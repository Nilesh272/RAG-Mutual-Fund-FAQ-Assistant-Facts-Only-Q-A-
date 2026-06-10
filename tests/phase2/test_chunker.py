from pathlib import Path

from phases.phase2_rag_core.chunking.chunker import ChunkingService
from phases.phase2_rag_core.parsing.groww_parser import GrowwParser
from phases.phase1_corpus.scraping.models import ScrapeResult


def test_chunker_produces_prefixed_chunks(project_root: Path, sample_html: str) -> None:
    parser = GrowwParser()
    chunker = ChunkingService.from_config_file(project_root / "config" / "chunking.yaml")

    result = ScrapeResult(
        source_id="hdfc-large-cap-direct-growth",
        url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        status="success",
        http_status=200,
        html=sample_html,
        content_hash="hash123",
        fetched_at="2026-06-05T09:15:12+05:30",
    )
    sections = parser.parse(
        result,
        {
            "scheme_name": "HDFC Large Cap Fund Direct Growth",
            "scheme_category": "large-cap",
        },
    )
    chunks = chunker.chunk_page(sections)

    assert len(chunks) >= 5
    assert all(chunk.token_count <= 600 for chunk in chunks)
    assert all("HDFC Large Cap Fund Direct Growth —" in chunk.text for chunk in chunks)
    assert chunks[0].chunk_id.startswith("hdfc-large-cap-direct-growth-")


def test_large_section_splits_into_multiple_chunks(project_root: Path) -> None:
    chunker = ChunkingService.from_config_file(project_root / "config" / "chunking.yaml")
    long_text = "Word " * 900

    from phases.phase2_rag_core.parsing.models import SectionBlock

    section = SectionBlock(
        source_id="hdfc-equity-direct-growth",
        source_url="https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        scheme_name="HDFC Equity Fund Direct Growth",
        scheme_category="diversified-equity",
        section_key="investment_objective",
        section_heading="Investment Objective",
        content=long_text,
        content_hash="hash",
    )

    chunks = chunker.chunk_section(section)
    assert len(chunks) > 1
