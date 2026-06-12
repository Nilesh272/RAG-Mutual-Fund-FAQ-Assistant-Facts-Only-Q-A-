from pathlib import Path

import pytest
import yaml

from phases.phase2_rag_core.chunking.chunker import ChunkingService
from phases.phase2_rag_core.chunking.models import Chunk
from phases.phase2_rag_core.embedding.embedder import EmbeddingService
@pytest.fixture
def embedder(project_root: Path, tmp_path: Path, monkeypatch) -> EmbeddingService:
    config_path = tmp_path / "embedding.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "embedding": {
                    "provider": "hash",
                    "model": "BAAI/bge-small-en-v1.5",
                    "dimensions": 384,
                    "batch_size": 20,
                    "max_retries": 3,
                },
                "vector_store": {
                    "provider": "chroma",
                    "mode": "ephemeral",
                    "collection": "test_mf_faq",
                    "distance": "cosine",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    return EmbeddingService.from_config_files(config_path, project_root=tmp_path)


def test_embed_and_upsert(embedder: EmbeddingService) -> None:
    chunks = [
        Chunk(
            chunk_id="hdfc-large-cap-direct-growth-expense_ratio-chunk-001",
            source_id="hdfc-large-cap-direct-growth",
            source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            document_type="scheme_page",
            scheme_name="HDFC Large Cap Fund Direct Growth",
            scheme_category="large-cap",
            section_key="expense_ratio",
            section_heading="Expense Ratio",
            content_format="html",
            text="HDFC Large Cap Fund Direct Growth — Expense Ratio: 0.96%",
            token_count=20,
            chunk_index=1,
            content_hash="page-hash",
            text_hash="chunk-hash",
        )
    ]

    records = embedder.embed_chunks(chunks)
    assert len(records) == 1
    assert len(records[0].vector) == 384

    result = embedder.upsert(records, "hdfc-large-cap-direct-growth")
    assert result.verified
    assert result.upserted_count == 1

    hits = embedder.search("expense ratio HDFC Large Cap", limit=1)
    assert hits
    assert hits[0]["payload"]["section_key"] == "expense_ratio"
