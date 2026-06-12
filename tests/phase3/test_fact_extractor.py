from phases.phase3_generation.generation.extractive_generator import ExtractiveGenerator
from phases.phase3_generation.generation.fact_extractor import extract_fact
from phases.phase2_rag_core.retrieval.models import RetrievedChunk


def test_extract_expense_ratio_from_metric_text() -> None:
    text = "HDFC Large Cap Fund Direct Growth — Expense Ratio: 0.99%"
    fact = extract_fact(
        query="expense ratio of HDFC Large Cap",
        text=text,
        section_key="expense_ratio",
    )
    assert fact == "The expense ratio is 0.99%."


def test_skips_definition_boilerplate() -> None:
    definition = (
        "Expense Ratio: A fee payable to a mutual fund house for managing "
        "your mutual fund investments."
    )
    assert extract_fact(
        query="expense ratio",
        text=definition,
        section_key="expense_ratio",
    ) is None


def test_extractive_skips_definition_chunk_uses_next() -> None:
    gen = ExtractiveGenerator()
    definition_chunk = RetrievedChunk(
        chunk_id="c1",
        source_id="hdfc-large-cap-direct-growth",
        source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        scheme_name="HDFC Large Cap Fund Direct Growth",
        section_key="expense_ratio",
        section_heading="Expense Ratio",
        text=(
            "HDFC Large Cap Fund Direct Growth — Expense Ratio: A fee payable "
            "to a mutual fund house for managing your mutual fund investments."
        ),
        dense_score=1.0,
        sparse_score=1.0,
        final_score=1.0,
        payload={},
    )
    value_chunk = RetrievedChunk(
        chunk_id="c2",
        source_id="hdfc-large-cap-direct-growth",
        source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        scheme_name="HDFC Large Cap Fund Direct Growth",
        section_key="expense_ratio",
        section_heading="Expense Ratio",
        text="HDFC Large Cap Fund Direct Growth — Expense Ratio: 1.04%",
        dense_score=0.9,
        sparse_score=0.9,
        final_score=0.9,
        payload={},
    )
    response = gen.generate(
        query="What is the expense ratio of HDFC Large Cap Fund?",
        chunks=[definition_chunk, value_chunk],
        citation=definition_chunk.source_url,
        last_updated="2026-06-12",
    )
    assert "1.04%" in response.answer
    assert "fee payable" not in response.answer.lower()


def test_extractive_generator_uses_fact() -> None:
    gen = ExtractiveGenerator()
    chunk = RetrievedChunk(
        chunk_id="c1",
        source_id="hdfc-large-cap-direct-growth",
        source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        scheme_name="HDFC Large Cap Fund Direct Growth",
        section_key="expense_ratio",
        section_heading="Expense Ratio",
        text="HDFC Large Cap Fund Direct Growth — Expense Ratio: 0.99%",
        dense_score=1.0,
        sparse_score=1.0,
        final_score=1.0,
        payload={},
    )
    response = gen.generate(
        query="What is the expense ratio of HDFC Large Cap Fund?",
        chunks=[chunk],
        citation=chunk.source_url,
        last_updated="2026-06-11",
    )
    assert "0.99%" in response.answer
    assert "fee payable" not in response.answer.lower()
