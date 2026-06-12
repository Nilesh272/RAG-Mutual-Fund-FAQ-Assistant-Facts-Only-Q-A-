from pathlib import Path
from unittest.mock import patch

import pytest

from phases.phase2_rag_core.embedding.chroma_client import create_chroma_client, resolve_chroma_mode
from phases.phase2_rag_core.embedding.models import VectorStoreConfig


def test_resolve_mode_defaults_to_cloud(monkeypatch) -> None:
    monkeypatch.delenv("VECTOR_STORE_MODE", raising=False)
    monkeypatch.delenv("CHROMA_API_KEY", raising=False)
    config = VectorStoreConfig(mode="cloud")
    assert resolve_chroma_mode(config) == "cloud"


def test_resolve_mode_ephemeral_override(monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "ephemeral")
    config = VectorStoreConfig(mode="cloud")
    assert resolve_chroma_mode(config) == "ephemeral"


def test_resolve_mode_rejects_local(monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "local")
    with pytest.raises(ValueError, match="VECTOR_STORE_MODE"):
        resolve_chroma_mode(VectorStoreConfig())


def test_create_ephemeral_client(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "ephemeral")
    client = create_chroma_client(VectorStoreConfig(), tmp_path)
    collection = client.get_or_create_collection("test_collection")
    collection.upsert(ids=["1"], embeddings=[[0.1] * 384])
    assert collection.count() == 1


def test_create_cloud_client_requires_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "cloud")
    monkeypatch.delenv("CHROMA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CHROMA_API_KEY"):
        create_chroma_client(VectorStoreConfig(), tmp_path)


def test_create_cloud_client_requires_tenant_and_database(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "cloud")
    monkeypatch.setenv("CHROMA_API_KEY", "test-key")
    monkeypatch.delenv("CHROMA_TENANT", raising=False)
    monkeypatch.delenv("CHROMA_DATABASE", raising=False)
    with pytest.raises(ValueError, match="CHROMA_TENANT"):
        create_chroma_client(VectorStoreConfig(tenant="", database=""), tmp_path)


def test_create_cloud_client_uses_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "cloud")
    monkeypatch.setenv("CHROMA_API_KEY", "test-key")
    monkeypatch.setenv("CHROMA_TENANT", "tenant-1")
    monkeypatch.setenv("CHROMA_DATABASE", "db-1")

    calls: list[dict] = []

    class FakeCloudClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    with patch("chromadb.CloudClient", FakeCloudClient):
        create_chroma_client(VectorStoreConfig(), tmp_path)

    assert calls[0]["api_key"] == "test-key"
    assert calls[0]["tenant"] == "tenant-1"
    assert calls[0]["database"] == "db-1"
