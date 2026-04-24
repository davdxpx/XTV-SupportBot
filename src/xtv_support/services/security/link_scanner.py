"""Link-scanner — detects suspicious URLs in incoming messages.

Two layers:

1. **Local blocklists** (``BUILTIN_BAD_HOSTS`` + operator-supplied
   via ``add_host`` at runtime) — instant reject for exact host
   matches. Covers the "obvious phishing kit" case.
2. **Heuristic** — flags URLs that combine:
   * IP-address host (no domain at all)
   * "login/verify/reset" keyword in the path
   * Punycode host (``xn--``) with ASCII-looking domain

The scanner is a pure function. The pyrofork middleware
``middlewares/link_scan_mw.py`` (later phase) calls
:func:`scan_text` and decides what to do with the result.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

_URL_RE = re.compile(r"https?://([^\s/]+)(/[^\s]*)?", re.IGNORECASE)
_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_KEYWORDS_RE = re.compile(
    r"(login|signin|verify|reset|secure|account|update|wallet|seed)",
    re.IGNORECASE,
)

BUILTIN_BAD_HOSTS: frozenset[str] = frozenset(
    {
        # Placeholder set — real deployments extend via add_host().
        "phishing.example.com",
        "malicious.example.org",
    }
)


@dataclass(frozen=True, slots=True)
class Suspicion:
    url: str
    host: str
    reasons: tuple[str, ...]

    @property
    def is_blocked(self) -> bool:
        return "blocklist" in self.reasons


@dataclass(frozen=True, slots=True)
class ScanResult:
    suspicious: tuple[Suspicion, ...] = field(default_factory=tuple)

    @property
    def has_hits(self) -> bool:
        return bool(self.suspicious)

    @property
    def has_blocked(self) -> bool:
        return any(s.is_blocked for s in self.suspicious)


def scan_text(
    text: str,
    *,
    extra_bad_hosts: Iterable[str] | None = None,
) -> ScanResult:
    """Inspect ``text`` for suspicious URLs."""
    if not text:
        return ScanResult()

    bad_hosts = {h.lower() for h in (extra_bad_hosts or ())} | BUILTIN_BAD_HOSTS
    hits: list[Suspicion] = []
    for match in _URL_RE.finditer(text):
        host = (match.group(1) or "").lower().strip()
        path = match.group(2) or ""
        url = match.group(0)
        reasons: list[str] = []
        if host in bad_hosts:
            reasons.append("blocklist")
        if _IP_RE.match(host):
            reasons.append("ip_host")
        if host.startswith("xn--") or ".xn--" in host:
            reasons.append("punycode")
        if _KEYWORDS_RE.search(path or ""):
            reasons.append("keyword_in_path")
        if reasons:
            hits.append(Suspicion(url=url, host=host, reasons=tuple(reasons)))
    return ScanResult(suspicious=tuple(hits))
