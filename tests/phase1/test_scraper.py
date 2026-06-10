from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from phases.phase1_corpus.scraping.scraper import ScrapingService


SAMPLE_HTML = "<html><body><h1>HDFC Large Cap Fund</h1></body></html>"


@pytest.fixture
def scraper(project_root: Path, sources_path: Path, scraping_config_path: Path, tmp_path: Path):
    service = ScrapingService.from_config_files(
        sources_path=sources_path,
        scraping_config_path=scraping_config_path,
        project_root=project_root,
    )
    service.registry.metadata_path = tmp_path / "source_state.json"
    service.config.rate_limit_seconds = 0
    service.config.save_raw_snapshots = False
    return service


def test_scrape_success(httpx_mock, scraper) -> None:
    entry = scraper.registry.get_by_id("hdfc-large-cap-direct-growth")
    assert entry is not None

    httpx_mock.add_response(
        url=entry.url,
        text=SAMPLE_HTML,
        headers={"content-type": "text/html; charset=utf-8"},
    )

    result = scraper.scrape_entry(entry)

    assert result.status == "success"
    assert result.http_status == 200
    assert result.html == SAMPLE_HTML
    assert result.content_hash is not None
    assert len(result.content_hash) == 64
    assert result.changed is True


def test_scrape_rejects_non_html(httpx_mock, scraper) -> None:
    entry = scraper.registry.get_by_id("hdfc-equity-direct-growth")
    assert entry is not None

    httpx_mock.add_response(
        url=entry.url,
        text="{}",
        headers={"content-type": "application/json"},
    )

    result = scraper.scrape_entry(entry)

    assert result.status == "failed"
    assert "Non-HTML" in (result.error or "")


def test_scrape_retries_on_500(httpx_mock, scraper) -> None:
    entry = scraper.registry.get_by_id("hdfc-focused-direct-growth")
    assert entry is not None

    httpx_mock.add_response(url=entry.url, status_code=500)
    httpx_mock.add_response(url=entry.url, status_code=500)
    httpx_mock.add_response(
        url=entry.url,
        text=SAMPLE_HTML,
        headers={"content-type": "text/html"},
    )

    with patch("phases.phase1_corpus.scraping.scraper.time.sleep"):
        result = scraper.scrape_entry(entry)

    assert result.status == "success"


def test_start_scrape_all_urls(httpx_mock, scraper) -> None:
    for entry in scraper.registry.get_allowlisted_urls():
        httpx_mock.add_response(
            url=entry.url,
            text=f"<html>{entry.source_id}</html>",
            headers={"content-type": "text/html"},
        )

    results = scraper.start_scrape()

    assert len(results) == 5
    assert all(r.status == "success" for r in results)
