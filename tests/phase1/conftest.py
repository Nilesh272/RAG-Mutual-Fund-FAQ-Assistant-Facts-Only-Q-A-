from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def sources_path(project_root: Path) -> Path:
    return project_root / "config" / "sources.yaml"


@pytest.fixture
def scraping_config_path(project_root: Path) -> Path:
    return project_root / "config" / "scraping.yaml"
