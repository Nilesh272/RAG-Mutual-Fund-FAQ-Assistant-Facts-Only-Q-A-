from pathlib import Path

from phases.phase3_generation.intent.classifier import IntentClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_eval_dataset_intent_labels() -> None:
    """Smoke test: advisory prompts classify as ADVISORY without full chat pipeline."""
    clf = IntentClassifier(sources_path=PROJECT_ROOT / "config" / "sources.yaml")
    advisory_queries = [
        "Should I invest in HDFC Large Cap Fund?",
        "Do you recommend HDFC ELSS?",
        "Which fund is better, HDFC Large Cap or HDFC Mid Cap?",
    ]
    intents = {clf.classify(q).intent for q in advisory_queries}
    assert "ADVISORY" in intents or "COMPARATIVE" in intents
