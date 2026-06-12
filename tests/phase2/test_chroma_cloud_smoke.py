"""Optional live Chroma Cloud smoke test — skipped unless CHROMA_* env vars are set."""

import os

import pytest

from phases.phase2_rag_core.embedding.embedder import EmbeddingService
from phases.phase2_rag_core.validation.ingest_validator import IngestValidator

pytestmark = pytest.mark.skipif(
    not all(os.getenv(key) for key in ("CHROMA_API_KEY", "CHROMA_TENANT", "CHROMA_DATABASE")),
    reason="Set CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE for live Cloud smoke test",
)


@pytest.fixture
def cloud_embedder(project_root):
    return EmbeddingService.from_config_files(
        project_root / "config" / "embedding.yaml",
        project_root=project_root,
    )


def test_chroma_cloud_connectivity(cloud_embedder, project_root) -> None:
    store = cloud_embedder.vector_store
    assert store.is_cloud
    assert store.health_check()


def test_chroma_cloud_validate_index(cloud_embedder, project_root) -> None:
    validator = IngestValidator(
        cloud_embedder.vector_store,
        sources_path=project_root / "config" / "sources.yaml",
    )
    report = validator.validate(embedder=cloud_embedder, expected_min_chunks=1)
    assert report.checks[0].passed
    assert any(c.name == "chroma_collection_reachable" and c.passed for c in report.checks)
