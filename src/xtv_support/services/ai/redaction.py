"""Pre-flight PII redaction.

Runs on every outbound prompt before the AI client sees it. Redactions
are conservative — we'd rather under-redact and keep answers useful
than over-redact and send the user nonsense. The flag
``AI_PII_REDACTION=false`` disables the scrub entirely for deployments
where the AI provider is already contractually scoped (on-prem
Ollama, private Azure).

Redaction strategy
------------------
* Credit-card numbers, SSN-shaped strings, and API-key-shaped tokens
  are replaced with ``[REDACTED:<kind>]``.
* Email addresses and phone numbers are hashed into short stable
  tokens (``[email#a1b2]``) so the AI can still reason about "the
  same email appears twice" without seeing the actual value.

The regexes are deliberately simple and permissive — tight rules
false-positive on legitimate content ("my ticket #4534-1234-5678-9012
was closed"), and false-negatives on PII slip through to the provider
anyway. In practice operators should rely on their provider contract
as the primary control and treat this scrubber as defence in depth.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Tight CC regex — requires 4-digit groups so phone numbers like
# "+49 151 23456789" don't false-positive. Matches 4-4-4-4(-opt) with
# optional hyphen/space separators, or a bare 13-19 digit run.
_CC_RE = re.compile(
    r"\b(?:\d{4}[ -]?){3}\d{4,7}\b"
    r"|\b\d{13,19}\b"
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
_API_KEY_RE = re.compile(r"\b(?:sk|pk|api|key|token)[-_][A-Za-z0-9]{16,}\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RedactionReport:
    redacted: str
    replaced: dict[str, int]  # {kind: count}

    @property
    def changed(self) -> bool:
        return bool(self.replaced)


def _stable_token(kind: str, value: str) -> str:
    """Short deterministic token so repeated PII maps to the same label."""
    digest = hashlib.sha256(value.encode()).hexdigest()[:4]
    return f"[{kind}#{digest}]"


def redact(text: str, *, enabled: bool = True) -> RedactionReport:
    """Return ``(redacted_text, counts)``.

    ``enabled=False`` short-circuits and returns the input untouched so
    callers can keep the same code path regardless of the configuration.
    """
    if not enabled or not text:
        return RedactionReport(redacted=text or "", replaced={})

    counts: dict[str, int] = {}
    out = text

    def _replace_all(pattern: re.Pattern[str], kind: str, *, hashed: bool) -> str:
        nonlocal out
        n = 0

        def _sub(match: re.Match[str]) -> str:
            nonlocal n
            n += 1
            if hashed:
                return _stable_token(kind, match.group(0))
            return f"[REDACTED:{kind}]"

        out = pattern.sub(_sub, out)
        if n:
            counts[kind] = counts.get(kind, 0) + n
        return out

    # Order matters: API keys and credit cards first so a 16-digit
    # string isn't mistaken for a phone number.
    _replace_all(_API_KEY_RE, "api_key", hashed=False)
    _replace_all(_CC_RE, "credit_card", hashed=False)
    _replace_all(_SSN_RE, "ssn", hashed=False)
    _replace_all(_EMAIL_RE, "email", hashed=True)
    _replace_all(_PHONE_RE, "phone", hashed=True)

    return RedactionReport(redacted=out, replaced=counts)
