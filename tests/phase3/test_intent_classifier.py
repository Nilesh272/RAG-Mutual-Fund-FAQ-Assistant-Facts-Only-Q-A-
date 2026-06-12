from pathlib import Path

from phases.phase3_generation.intent.classifier import IntentClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_advisory_intent() -> None:
    clf = IntentClassifier(sources_path=PROJECT_ROOT / "config" / "sources.yaml")
    assert clf.classify("Should I invest in HDFC Large Cap Fund?").intent == "ADVISORY"


def test_comparative_intent() -> None:
    clf = IntentClassifier(sources_path=PROJECT_ROOT / "config" / "sources.yaml")
    assert clf.classify("Which fund is better, HDFC Large Cap or Mid Cap?").intent == "COMPARATIVE"


def test_factual_intent() -> None:
    clf = IntentClassifier(sources_path=PROJECT_ROOT / "config" / "sources.yaml")
    assert clf.classify("What is the expense ratio of HDFC Large Cap Fund?").intent == "FACTUAL_SCHEME"


def test_performance_intent() -> None:
    clf = IntentClassifier(sources_path=PROJECT_ROOT / "config" / "sources.yaml")
    assert clf.classify("What returns did HDFC Large Cap give last year?").intent == "PERFORMANCE"
