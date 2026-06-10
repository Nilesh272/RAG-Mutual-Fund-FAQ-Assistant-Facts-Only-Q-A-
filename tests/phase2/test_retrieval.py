from pathlib import Path
from unittest.mock import patch

import yaml

from ingest.pipeline import build_pipeline
from phases.phase1_corpus.scraping.models import ScrapeResult
from phases.phase2_rag_core.embedding.embedder import EmbeddingService
from phases.phase2_rag_core.retrieval.hybrid_retriever import HybridRetriever
from phases.phase2_rag_core.validation.golden_runner import GoldenQueryRunner


def _write_configs(tmp_path: Path, project_root: Path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "sources.yaml").write_text(
        (project_root / "config" / "sources.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "config" / "retrieval.yaml").write_text(
        (project_root / "config" / "retrieval.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "config" / "chunking.yaml").write_text(
        (project_root / "config" / "chunking.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "config" / "embedding.yaml").write_text(
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


def _scheme_html(scheme_name: str, *, elss: bool = False) -> str:
    lock_in = "<h2>Lock-in Period</h2><p>3 years lock-in period applies.</p>" if elss else ""
    return f"""
    <html><body><main>
      <h1>{scheme_name}</h1>
      <h2>Expense Ratio</h2><p>Expense ratio is 1.00%.</p>
      <h2>Exit Load</h2><p>Exit load is 1% within 1 year.</p>
      <h2>Minimum Investment</h2><p>Minimum SIP is Rs 100.</p>
      <h2>Benchmark</h2><p>NIFTY 100 Total Return Index.</p>
      {lock_in}
    </main></body></html>
    """


def test_hybrid_retriever_and_golden_queries(project_root: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("RUN_GOLDEN_QUERIES", "false")
    _write_configs(tmp_path, project_root)

    schemes = [
        ("hdfc-large-cap-direct-growth", "HDFC Large Cap Fund Direct Growth", False),
        ("hdfc-mid-cap-direct-growth", "HDFC Mid Cap Fund Direct Growth", False),
        ("hdfc-focused-direct-growth", "HDFC Focused Fund Direct Growth", False),
        ("hdfc-equity-direct-growth", "HDFC Equity Fund Direct Growth", False),
        ("hdfc-elss-tax-saver-direct-growth", "HDFC ELSS Tax Saver Fund Direct Plan Growth", True),
    ]
    urls = {
        "hdfc-large-cap-direct-growth": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "hdfc-mid-cap-direct-growth": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "hdfc-focused-direct-growth": "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
        "hdfc-equity-direct-growth": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "hdfc-elss-tax-saver-direct-growth": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    }

    scrape_results = [
        ScrapeResult(
            source_id=source_id,
            url=urls[source_id],
            status="success",
            http_status=200,
            html=_scheme_html(name, elss=elss),
            content_hash=f"hash-{source_id}",
            fetched_at="2026-06-05T09:15:12+05:30",
            changed=True,
        )
        for source_id, name, elss in schemes
    ]

    pipeline = build_pipeline(project_root=project_root)
    pipeline.scraper.registry.metadata_path = tmp_path / "source_state.json"
    pipeline.scraper.config.save_raw_snapshots = False
    pipeline.embedder = EmbeddingService.from_config_files(
        tmp_path / "config" / "embedding.yaml", project_root=tmp_path
    )
    pipeline.retriever = HybridRetriever.from_config_files(
        tmp_path / "config" / "embedding.yaml",
        tmp_path / "config" / "retrieval.yaml",
        tmp_path / "config" / "sources.yaml",
        project_root=tmp_path,
    )

    with patch.object(pipeline.scraper, "start_scrape", return_value=scrape_results):
        summary = pipeline.run(trigger="manual")

    assert summary.chunks_created > 0
    assert summary.validation_report is not None
    assert summary.validation_report["passed"] is True

    report = GoldenQueryRunner(pipeline.retriever).run()
    assert report.passed_count >= 4
