from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def phase2_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("RUN_GOLDEN_QUERIES", "false")
    monkeypatch.setenv("VECTOR_STORE_MODE", "ephemeral")
    monkeypatch.delenv("CHROMA_API_KEY", raising=False)
    monkeypatch.chdir(PROJECT_ROOT)


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def sample_html(project_root: Path) -> str:
    return (project_root / "tests" / "fixtures" / "sample_groww_page.html").read_text(encoding="utf-8")


@pytest.fixture
def chroma_dir(tmp_path: Path) -> Path:
    return tmp_path / "chroma"
