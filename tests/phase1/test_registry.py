from pathlib import Path

from phases.phase1_corpus.registry.source_registry import SourceRegistryService


def test_loads_five_sources(sources_path: Path, tmp_path: Path) -> None:
    registry = SourceRegistryService(
        sources_path=sources_path,
        metadata_path=tmp_path / "source_state.json",
    )
    entries = registry.get_allowlisted_urls()

    assert len(entries) == 5
    assert all(entry.url.startswith("https://groww.in/mutual-funds/") for entry in entries)
    assert {e.source_id for e in entries} == {
        "hdfc-mid-cap-direct-growth",
        "hdfc-equity-direct-growth",
        "hdfc-focused-direct-growth",
        "hdfc-elss-tax-saver-direct-growth",
        "hdfc-large-cap-direct-growth",
    }


def test_persists_content_hash(sources_path: Path, tmp_path: Path) -> None:
    metadata_path = tmp_path / "source_state.json"
    registry = SourceRegistryService(sources_path=sources_path, metadata_path=metadata_path)

    registry.update_source_state(
        "hdfc-large-cap-direct-growth",
        content_hash="abc123",
        last_fetched="2026-06-05T09:15:12+05:30",
        http_status=200,
    )

    reloaded = SourceRegistryService(sources_path=sources_path, metadata_path=metadata_path)
    assert reloaded.get_stored_hash("hdfc-large-cap-direct-growth") == "abc123"
    assert reloaded.get_last_fetched("hdfc-large-cap-direct-growth") == "2026-06-05T09:15:12+05:30"
