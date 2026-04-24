"""Link-scanner tests — pure heuristics."""

from __future__ import annotations

from xtv_support.services.security.link_scanner import (
    BUILTIN_BAD_HOSTS,
    ScanResult,
    scan_text,
)


def test_empty_text() -> None:
    assert scan_text("").has_hits is False


def test_plain_link_no_hits() -> None:
    r = scan_text("visit https://example.com for docs")
    assert r.has_hits is False


def test_blocklist_host_hit() -> None:
    r = scan_text("reply to https://phishing.example.com/login")
    assert r.has_hits
    assert r.has_blocked
    first = r.suspicious[0]
    assert "blocklist" in first.reasons


def test_ip_host_detected() -> None:
    r = scan_text("download https://192.0.2.17/setup.exe")
    assert r.has_hits
    assert "ip_host" in r.suspicious[0].reasons


def test_keyword_in_path_detected() -> None:
    r = scan_text("https://example.com/account/verify?x=1")
    assert r.has_hits
    assert "keyword_in_path" in r.suspicious[0].reasons


def test_punycode_flagged() -> None:
    r = scan_text("https://xn--pple-43d.com/login")
    assert r.has_hits
    # Both punycode and keyword triggers should fire.
    reasons = set(r.suspicious[0].reasons)
    assert "punycode" in reasons
    assert "keyword_in_path" in reasons


def test_extra_bad_hosts_injected() -> None:
    r = scan_text(
        "link https://custom.attacker.tld/path",
        extra_bad_hosts=["custom.attacker.tld"],
    )
    assert r.has_blocked


def test_builtin_blocklist_not_empty() -> None:
    assert len(BUILTIN_BAD_HOSTS) >= 1


def test_scan_result_aggregators() -> None:
    r = ScanResult()
    assert r.has_hits is False and r.has_blocked is False


def test_multiple_urls_in_one_message() -> None:
    r = scan_text("first https://example.com second https://phishing.example.com/login")
    assert len(r.suspicious) == 1  # only the blocklisted URL fires
    assert r.suspicious[0].host == "phishing.example.com"
