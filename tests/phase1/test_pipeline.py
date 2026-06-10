from pathlib import Path

from ingest.pipeline import build_pipeline

SAMPLE_HTML = "<html><body>fund data</body></html>"


def test_pipeline_run_scrape_only(project_root: Path, tmp_path, httpx_mock) -> None:
    pipeline = build_pipeline(project_root=project_root)
    pipeline.scraper.registry.metadata_path = tmp_path / "source_state.json"
    pipeline.scraper.config.rate_limit_seconds = 0
    pipeline.scraper.config.save_raw_snapshots = False

    for entry in pipeline.scraper.registry.get_allowlisted_urls():
        httpx_mock.add_response(
            url=entry.url,
            text=SAMPLE_HTML,
            headers={"content-type": "text/html"},
        )

    summary = pipeline.run(scrape_only=True)

    assert summary.urls_fetched == 5
    assert summary.urls_changed == 5
    assert summary.urls_failed == 0
    assert summary.status == "success"
    assert len(summary.scrape_results) == 5


def test_pipeline_skips_unchanged_content(project_root: Path, tmp_path, httpx_mock) -> None:
    pipeline = build_pipeline(project_root=project_root)
    pipeline.scraper.registry.metadata_path = tmp_path / "source_state.json"
    pipeline.scraper.config.rate_limit_seconds = 0
    pipeline.scraper.config.save_raw_snapshots = False

    from phases.phase1_corpus.scraping.scraper import _content_hash

    content_hash = _content_hash(SAMPLE_HTML)
    for entry in pipeline.scraper.registry.get_allowlisted_urls():
        pipeline.scraper.registry.update_source_state(
            entry.source_id,
            content_hash=content_hash,
            last_fetched="2026-06-01T09:00:00+05:30",
            http_status=200,
        )

    for e in pipeline.scraper.registry.get_allowlisted_urls():
        httpx_mock.add_response(
            url=e.url,
            text=SAMPLE_HTML,
            headers={"content-type": "text/html"},
        )

    summary = pipeline.run(scrape_only=True)

    assert summary.urls_skipped == 5
    assert summary.urls_changed == 0
