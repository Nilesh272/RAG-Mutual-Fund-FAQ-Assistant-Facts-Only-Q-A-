from __future__ import annotations

import re


_DEFINITION_MARKERS = (
    "a fee payable",
    "mutual fund house for managing",
    "percentage of your capital gains payable",
    "form of tax payable",
)

_METRIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "expense_ratio",
        re.compile(
            r"expense ratio[:\s]+(\d+(?:\.\d+)?%)",
            re.IGNORECASE,
        ),
    ),
    (
        "exit_load",
        re.compile(
            r"(exit load of \d+(?:\.\d+)?%[^.]*(?:within[^.]+)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "minimum_investment",
        re.compile(
            r"(?:min(?:imum)?\.?\s+for\s+sip|minimum sip)[:\s]+(?:rs\.?\s*)?([\d,]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "lock_in_period",
        re.compile(
            r"((?:\d+\s*y(?:ear)?(?:s)?)\s*lock[- ]?in|lock[- ]?in[^.]{0,40}\d+\s*y(?:ear)?(?:s)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "benchmark",
        re.compile(
            r"(?:benchmark|fund benchmark)[:\s]+([A-Z0-9][A-Za-z0-9\s\-]+(?:Index|TRI))",
            re.IGNORECASE,
        ),
    ),
]


def is_definition_text(text: str) -> bool:
    lowered = text.lower()
    if not any(marker in lowered for marker in _DEFINITION_MARKERS):
        return False
    if re.search(r"\d+(?:\.\d+)?%", text):
        return False
    if re.search(r"rs\.?\s*\d", text, re.IGNORECASE):
        return False
    return True


def extract_fact(*, query: str, text: str, section_key: str) -> str | None:
    """Pull a concise numeric/categorical fact from chunk text."""
    if is_definition_text(text):
        return None

    lowered_query = query.lower()

    keys_to_try: list[str] = []
    if "expense ratio" in lowered_query or "ter" in lowered_query:
        keys_to_try.append("expense_ratio")
    if "exit load" in lowered_query:
        keys_to_try.append("exit_load")
    if "sip" in lowered_query or "minimum" in lowered_query:
        keys_to_try.append("minimum_investment")
    if "lock" in lowered_query or "elss" in lowered_query:
        keys_to_try.append("lock_in_period")
    if "benchmark" in lowered_query:
        keys_to_try.append("benchmark")
    if section_key not in keys_to_try:
        keys_to_try.append(section_key)

    for key in keys_to_try:
        pattern = next((p for k, p in _METRIC_PATTERNS if k == key), None)
        if pattern is None:
            continue
        match = pattern.search(text)
        if not match:
            continue
        if key == "expense_ratio":
            return f"The expense ratio is {match.group(1)}."
        if key == "exit_load":
            value = match.group(1).strip().rstrip(".")
            return f"The {value[0].lower()}{value[1:]}."
        if key == "minimum_investment":
            return f"The minimum SIP amount is Rs {match.group(1)}."
        if key == "lock_in_period":
            value = match.group(1).strip()
            return f"The lock-in period is {value}."
        if key == "benchmark":
            return f"The benchmark is {match.group(1).strip()}."

    # Fallback: standalone percentage (e.g. chunk content is just "0.99%").
    if section_key == "expense_ratio" and not is_definition_text(text):
        pct = re.search(r"\b(\d+(?:\.\d+)?%)\b", text)
        if pct:
            return f"The expense ratio is {pct.group(1)}."

    if section_key == "minimum_investment":
        amount = re.search(r"(?:rs\.?\s*)?([\d,]+)", text, re.IGNORECASE)
        if amount:
            return f"The minimum SIP amount is Rs {amount.group(1)}."

    return None
