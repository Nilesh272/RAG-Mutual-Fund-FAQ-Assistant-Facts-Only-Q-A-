from pathlib import Path

import pytest

from phases.phase2_rag_core.embedding.chroma_client import create_chroma_client, resolve_chroma_mode
from phases.phase2_rag_core.embedding.models import VectorStoreConfig


def test_resolve_mode_defaults_to_local(monkeypatch) -> None:
    monkeypatch.delenv("VECTOR_STORE_MODE", raising=False)
    monkeypatch.delenv("CHROMA_API_KEY", raising=False)
    config = VectorStoreConfig(mode="local")
    assert resolve_chroma_mode(config) == "local"


def test_resolve_mode_cloud_from_api_key(monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_API_KEY", "test-key")
    monkeypatch.delenv("VECTOR_STORE_MODE", raising=False)
    config = VectorStoreConfig(mode="local")
    assert resolve_chroma_mode(config) == "cloud"


def test_resolve_mode_explicit_override(monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_API_KEY", "test-key")
    monkeypatch.setenv("VECTOR_STORE_MODE", "ephemeral")
    config = VectorStoreConfig(mode="local")
    assert resolve_chroma_mode(config) == "ephemeral"


def test_create_ephemeral_client(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "ephemeral")
    client = create_chroma_client(VectorStoreConfig(), tmp_path)
    collection = client.get_or_create_collection("test_collection")
    collection.upsert(ids=["1"], embeddings=[[0.1] * 384])
    assert collection.count() == 1


def test_create_persistent_client(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "local")
    config = VectorStoreConfig(persist_dir="chroma-data")
    client = create_chroma_client(config, tmp_path)
    collection = client.get_or_create_collection("test_persistent")
    collection.upsert(ids=["1"], embeddings=[[0.1] * 384])
    assert (tmp_path / "chroma-data").exists()
    assert collection.count() == 1


def test_create_cloud_client_requires_api_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "cloud")
    monkeypatch.delenv("CHROMA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CHROMA_API_KEY"):
        create_chroma_client(VectorStoreConfig(), tmp_path)


def test_create_cloud_client_uses_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VECTOR_STORE_MODE", "cloud")
    monkeypatch.setenv("CHROMA_API_KEY", "test-key")
    monkeypatch.setenv("CHROMA_TENANT", "tenant-1")
    monkeypatch.setenv("CHROMA_DATABASE", "db-1")

    calls: list[dict] = []

    class FakeCloudClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def get_or_create_collection(self, name: str, metadata=None):
            return self

        def count(self) -> int:
            return 0

    import chromadb

    monkeypatch.setattr(chromadb, "CloudClient", FakeCloudClient)
    create_chroma_client(VectorStoreConfig(), tmp_path)
    assert calls[0]["api_key"] == "test-key"
    assert calls[0]["tenant"] == "tenant-1"
    assert calls[0]["database"] == "db-1"
