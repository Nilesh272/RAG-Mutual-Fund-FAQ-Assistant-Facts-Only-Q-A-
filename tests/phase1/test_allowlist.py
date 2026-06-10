import pytest

from phases.phase1_corpus.registry.source_registry import SourceRegistryService
from phases.phase1_corpus.scraping.allowlist import AllowlistError, AllowlistValidator
from phases.phase1_corpus.scraping.models import ScrapingConfig


@pytest.fixture
def validator(sources_path):
    registry = SourceRegistryService(sources_path=sources_path)
    return AllowlistValidator(registry.get_allowlisted_urls(), ScrapingConfig())


def test_allows_registered_url(validator) -> None:
    url = "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    validator.validate_url(url)  # should not raise


def test_rejects_unknown_groww_url(validator) -> None:
    with pytest.raises(AllowlistError, match="not in Source Registry"):
        validator.validate_url("https://groww.in/mutual-funds/some-other-fund")


def test_rejects_wrong_domain(validator) -> None:
    with pytest.raises(AllowlistError, match="Domain not allowed"):
        validator.validate_url("https://example.com/mutual-funds/hdfc-large-cap-fund-direct-growth")


def test_rejects_wrong_path_prefix(validator) -> None:
    with pytest.raises(AllowlistError, match="Path not allowed"):
        validator.validate_url("https://groww.in/stocks/hdfc-large-cap-fund-direct-growth")
