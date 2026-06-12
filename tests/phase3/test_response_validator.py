from pathlib import Path

from phases.phase3_generation.compliance.link_registry import ComplianceLinkRegistry
from phases.phase3_generation.generation.models import GeneratedResponse
from phases.phase3_generation.validation.response_validator import ResponseValidator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_valid_factual_response() -> None:
    compliance = ComplianceLinkRegistry.from_config_file(
        PROJECT_ROOT / "config" / "compliance_links.yaml"
    )
    validator = ResponseValidator(
        sources_path=PROJECT_ROOT / "config" / "sources.yaml",
        compliance=compliance,
    )
    response = GeneratedResponse(
        answer="The expense ratio is listed on the Groww scheme page.",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_updated="2026-06-01",
        intent="FACTUAL_SCHEME",
    )
    result = validator.validate(response, context_text="expense ratio 1.00%")
    assert result.passed


def test_blocks_advisory_language() -> None:
    compliance = ComplianceLinkRegistry.from_config_file(
        PROJECT_ROOT / "config" / "compliance_links.yaml"
    )
    validator = ResponseValidator(
        sources_path=PROJECT_ROOT / "config" / "sources.yaml",
        compliance=compliance,
    )
    response = GeneratedResponse(
        answer="I recommend you should invest in this fund now.",
        citation="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        last_updated=None,
        intent="FACTUAL_SCHEME",
    )
    result = validator.validate(response)
    assert not result.passed
    assert any(i.check == "advisory_language" for i in result.issues)
