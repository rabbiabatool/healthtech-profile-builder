"""Sanitization, PII/PHI Redaction, and Prompt Injection Defense for LLM Agents (Week 5).

Ensures zero personal data or secrets enter LLM prompts, tool execution traces, or logs.
Detects and neutralizes prompt injection attacks and out-of-scope medical requests.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple


# ─── PII / PHI & Secret Redaction Patterns ───────────────────────────────────

REDACTION_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # US Social Security Number
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    # Credit Card Numbers (16-digit variations)
    ("CARD", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[REDACTED_PAYMENT_CARD]"),
    # Email Addresses
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    # Phone Numbers (US & International formats)
    ("PHONE", re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b"), "[REDACTED_PHONE]"),
    # Bearer Tokens & API Keys (Gemini, OpenAI, Generic API tokens)
    ("SECRET_API_KEY", re.compile(r"\b(?:AIza[0-9A-Za-z-_]{35}|sk-[a-zA-Z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})\b", re.IGNORECASE), "[REDACTED_SECRET_KEY]"),
    # Passwords in query strings or config blobs
    ("PASSWORD", re.compile(r"(?i)\bpassword\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?", re.IGNORECASE), "password=[REDACTED_PASSWORD]"),
    # Medical Record Numbers (MRN)
    ("MRN", re.compile(r"\bMRN[-:]?\s*\d{6,}\b", re.IGNORECASE), "[REDACTED_MRN]"),
]


def redact_sensitive_data(text: str) -> Tuple[str, List[str]]:
    """Redacts PII, PHI, and credentials from string input.
    
    Returns:
        redacted_text: Sanitized string with sensitive entities masked.
        redacted_types: List of detected entity types that were redacted.
    """
    if not text:
        return "", []

    redacted = text
    detected_types = []

    for name, pattern, replacement in REDACTION_PATTERNS:
        if pattern.search(redacted):
            detected_types.append(name)
            redacted = pattern.sub(replacement, redacted)

    return redacted, detected_types


def sanitize_dict_deep(obj: any) -> any:
    """Recursively walks a dictionary/list structure and redacts all string values."""
    if isinstance(obj, dict):
        return {k: sanitize_dict_deep(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_dict_deep(item) for item in obj]
    elif isinstance(obj, str):
        cleaned, _ = redact_sensitive_data(obj)
        return cleaned
    return obj


# ─── Prompt Injection & Adversarial Defense ──────────────────────────────────

INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(policy|safety|guidelines|rules)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+prompt|hidden\s+prompt|developer\s+mode)", re.IGNORECASE),
    re.compile(r"\b(dan\s+mode|jailbreak|unrestricted\s+ai|evil\s+twin)\b", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|you're)\s+an\s+unrestricted", re.IGNORECASE),
    re.compile(r"bypass\s+(authorization|permission|security)", re.IGNORECASE),
    re.compile(r"output\s+the\s+system\s+message\s+verbatim", re.IGNORECASE),
]

MEDICAL_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(chest\s+pain|heart\s+attack|shortness\s+of\s+breath|stroke|trauma|bleeding)\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+medication\s+(should|can)\s+i\s+take\b", re.IGNORECASE),
    re.compile(r"\bdiagnose\s+my\s+(symptoms|condition|illness)\b", re.IGNORECASE),
    re.compile(r"\b(prescribe|dosage\s+for|take\s+for\s+my)\b", re.IGNORECASE),
]


def check_prompt_security(text: str) -> Dict[str, any]:
    """Inspects text for prompt injection attacks and clinical medical queries.
    
    Returns:
        {
            "is_safe": bool,
            "is_injection": bool,
            "is_medical": bool,
            "reason": str,
        }
    """
    if not text:
        return {"is_safe": True, "is_injection": False, "is_medical": False, "reason": ""}

    # Check for prompt injection
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return {
                "is_safe": False,
                "is_injection": True,
                "is_medical": False,
                "reason": "Prompt injection pattern detected. Instruction override blocked.",
            }

    # Check for medical diagnosis/prescription requests
    for pattern in MEDICAL_PATTERNS:
        if pattern.search(text):
            return {
                "is_safe": False,
                "is_injection": False,
                "is_medical": True,
                "reason": (
                    "Clinical medical advice or emergency triage requested. "
                    "Greenleaf assistant is strictly limited to administrative policy and scheduling."
                ),
            }

    return {"is_safe": True, "is_injection": False, "is_medical": False, "reason": ""}
