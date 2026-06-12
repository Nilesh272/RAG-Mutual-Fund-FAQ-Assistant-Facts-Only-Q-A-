from pathlib import Path

import chromadb

from phases.phase2_rag_core.embedding.embedder import EmbeddingService
from phases.phase2_rag_core.embedding.models import VectorRecord, VectorStoreConfig
from phases.phase2_rag_core.embedding.vector_store import VectorStore
from phases.phase2_rag_core.validation.ingest_validator import IngestValidator


def _embedder_and_store(tmp_path: Path, project_root: Path) -> EmbeddingService:
    return EmbeddingService.from_config_files(
        project_root / "config" / "embedding.yaml",
        project_root=tmp_path,
    )


def test_validator_chroma_cloud_checks(project_root: Path, tmp_path: Path) -> None:
    embedder = _embedder_and_store(tmp_path, project_root)
    store = embedder.vector_store

    record = VectorRecord(
        id="hdfc-large-cap-direct-growth-expense_ratio-chunk-001",
        vector=[0.1] * 384,
        payload={
            "source_id": "hdfc-large-cap-direct-growth",
            "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "scheme_name": "HDFC Large Cap Fund Direct Growth",
            "section_key": "expense_ratio",
            "text": "HDFC Large Cap Fund Direct Growth — Expense Ratio: 0.96%",
        },
    )
    store.upsert_for_source("hdfc-large-cap-direct-growth", [record])

    validator = IngestValidator(store, sources_path=project_root / "config" / "sources.yaml")
    report = validator.validate(
        embedder=embedder,
        expected_min_chunks=1,
        full_corpus=False,
        run_dense_smoke=False,
    )

    check_names = {check.name for check in report.checks}
    assert "chroma_collection_reachable" in check_names
    assert "metadata_filter_expense_ratio" in check_names
    assert "dense_query_smoke" not in check_names
    assert report.checks[0].name == "chroma_backend_mode"
    assert report.checks[0].passed is True


def test_vector_store_reset_collection(tmp_path: Path) -> None:
    client = chromadb.EphemeralClient()
    store = VectorStore(
        VectorStoreConfig(collection="reset_test"),
        project_root=tmp_path,
        chroma_client=client,
        mode="ephemeral",
    )
    store.upsert_for_source(
        "hdfc-large-cap-direct-growth",
        [
            VectorRecord(
                id="chunk-1",
                vector=[0.1] * 384,
                payload={"source_id": "hdfc-large-cap-direct-growth", "text": "test"},
            )
        ],
    )
    assert store.count() == 1
    store.reset_collection()
    assert store.count() == 0
