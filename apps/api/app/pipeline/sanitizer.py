"""
Input Sanitizer
Strips prompt injection vectors and dangerous patterns from user-supplied text
before it reaches LLM prompts.
"""
from __future__ import annotations

import re


# Patterns that attempt to hijack LLM instructions
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?instructions?",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a|an)\s+\w+",
    r"(system|assistant|user)\s*:\s*",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"###\s*(instruction|system|prompt)",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_text(value: str, max_length: int = 500) -> str:
    """
    - Truncate to max_length
    - Strip null bytes
    - Collapse excessive whitespace
    - Remove prompt injection patterns
    """
    value = value.replace("\x00", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = value[:max_length]
    if _INJECTION_RE.search(value):
        # Replace the matched segment with a placeholder rather than rejecting outright
        value = _INJECTION_RE.sub("[removed]", value)
    return value


def sanitize_company_name(value: str) -> str:
    return sanitize_text(value, max_length=100)


def sanitize_description(value: str) -> str:
    return sanitize_text(value, max_length=500)


def sanitize_url(value: str) -> str:
    """Ensure URL uses http/https scheme only."""
    value = value.strip()
    if not re.match(r"^https?://", value, re.IGNORECASE):
        raise ValueError("URL must use http or https scheme")
    return value
