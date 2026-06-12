from __future__ import annotations

import re

_PII_PATTERNS = (
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "PAN-like pattern"),
    (re.compile(r"\b\d{12}\b"), "Aadhaar-like pattern"),
    (re.compile(r"\b\d{16}\b"), "card-like pattern"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "email"),
    (re.compile(r"\b\+?\d{10,13}\b"), "phone number"),
)


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern, _ in _PII_PATTERNS)
