from pathlib import Path
from unittest.mock import patch

import yaml

from ingest.pipeline import build_pipeline
from phases.phase1_corpus.scraping.models import ScrapeResult
from phases.phase2_rag_core.embedding.embedder import EmbeddingService
from phases.phase2_rag_core.retrieval.hybrid_retriever import HybridRetriever


def _scrape_result(source_id: str, url: str, scheme_slug: str, html: str) -> ScrapeResult:
    return ScrapeResult(
        source_id=source_id,
        url=url,
        status="success",
        http_status=200,
        html=html,
        content_hash=f"hash-{scheme_slug}",
        fetched_at="2026-06-05T09:15:12+05:30",
        changed=True,
    )


def test_full_pipeline_indexes_html(
    project_root: Path, sample_html: str, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("RUN_GOLDEN_QUERIES", "false")

    embedding_config = tmp_path / "embedding.yaml"
    embedding_config.write_text(
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
                    "collection": "mf_faq_hdfc_groww",
                    "distance": "cosine",
                    "persist_dir": "chroma",
                },
            }
        ),
        encoding="utf-8",
    )

    pipeline = build_pipeline(project_root=project_root)
    pipeline.scraper.registry.metadata_path = tmp_path / "source_state.json"
    pipeline.scraper.config.save_raw_snapshots = False
    pipeline.embedder = EmbeddingService.from_config_files(
        embedding_config, project_root=tmp_path
    )
    pipeline.retriever = HybridRetriever.from_config_files(
        embedding_config,
        project_root / "config" / "retrieval.yaml",
        project_root / "config" / "sources.yaml",
        project_root=tmp_path,
    )

    results = [
        _scrape_result(
            "hdfc-large-cap-direct-growth",
            "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "large-cap",
            sample_html,
        )
    ]

    with patch.object(pipeline.scraper, "start_scrape", return_value=results):
        summary = pipeline.run(trigger="manual")

    assert summary.status == "success"
    assert summary.urls_fetched == 1
    assert summary.urls_changed == 1
    assert summary.chunks_created > 0
    assert summary.embeddings_upserted == summary.chunks_created
