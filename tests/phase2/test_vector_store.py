from pathlib import Path

import chromadb

from phases.phase2_rag_core.embedding.models import VectorRecord, VectorStoreConfig
from phases.phase2_rag_core.embedding.vector_store import VectorStore


def _sample_record(source_id: str = "hdfc-large-cap-direct-growth") -> VectorRecord:
    return VectorRecord(
        id=f"{source_id}-expense_ratio-chunk-001",
        vector=[0.1] * 384,
        payload={
            "chunk_id": f"{source_id}-expense_ratio-chunk-001",
            "source_id": source_id,
            "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "scheme_name": "HDFC Large Cap Fund Direct Growth",
            "scheme_category": "large-cap",
            "section_key": "expense_ratio",
            "section_heading": "Expense Ratio",
            "document_type": "scheme_page",
            "text": "HDFC Large Cap Fund Direct Growth — Expense Ratio: 0.96%",
            "token_count": 20,
            "content_hash": "page-hash",
            "indexed_at": "2026-06-05T09:15:45+05:30",
        },
    )


def test_vector_store_ephemeral_upsert_and_search(tmp_path: Path) -> None:
    client = chromadb.EphemeralClient()
    store = VectorStore(
        VectorStoreConfig(collection="test_mf_faq"),
        project_root=tmp_path,
        chroma_client=client,
        mode="ephemeral",
    )

    result = store.upsert_for_source("hdfc-large-cap-direct-growth", [_sample_record()])
    assert result.verified
    assert store.count() == 1
    assert store.health_check()
    assert store.count_by_metadata({"section_key": "expense_ratio"}) == 1

    hits = store.search([0.1] * 384, limit=1)
    assert hits
    assert hits[0]["payload"]["section_key"] == "expense_ratio"


def test_vector_store_delete_by_source_id(tmp_path: Path) -> None:
    client = chromadb.EphemeralClient()
    store = VectorStore(
        VectorStoreConfig(collection="test_delete"),
        project_root=tmp_path,
        chroma_client=client,
        mode="ephemeral",
    )

    store.upsert_for_source("hdfc-large-cap-direct-growth", [_sample_record()])
    deleted = store.delete_by_source_id("hdfc-large-cap-direct-growth")
    assert deleted == 1
    assert store.count() == 0
