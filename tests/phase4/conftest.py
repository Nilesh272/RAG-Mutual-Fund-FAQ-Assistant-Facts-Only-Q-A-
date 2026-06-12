from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def phase4_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("VECTOR_STORE_MODE", "ephemeral")
    monkeypatch.setenv("GENERATION_PROVIDER", "extractive")
    monkeypatch.delenv("CHROMA_API_KEY", raising=False)
    monkeypatch.chdir(PROJECT_ROOT)
