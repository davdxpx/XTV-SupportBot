"""PII-redaction tests."""

from __future__ import annotations

from xtv_support.services.ai.redaction import redact


def test_disabled_returns_input_untouched() -> None:
    r = redact("email me at foo@bar.com please", enabled=False)
    assert r.redacted == "email me at foo@bar.com please"
    assert r.replaced == {}
    assert r.changed is False


def test_empty_string() -> None:
    r = redact("")
    assert r.redacted == ""
    assert r.replaced == {}


def test_redacts_credit_card() -> None:
    r = redact("card 4111 1111 1111 1111 expires 12/28")
    assert "4111" not in r.redacted
    assert "[REDACTED:credit_card]" in r.redacted
    assert r.replaced == {"credit_card": 1}


def test_redacts_ssn() -> None:
    r = redact("ssn 123-45-6789")
    assert "[REDACTED:ssn]" in r.redacted
    assert r.replaced == {"ssn": 1}


def test_redacts_api_key_like_token() -> None:
    r = redact("my sk-ABC123DEF456GHI7 key")
    assert "[REDACTED:api_key]" in r.redacted
    assert r.replaced == {"api_key": 1}


def test_hashed_email_is_stable() -> None:
    r1 = redact("write to foo@example.com")
    r2 = redact("and also foo@example.com twice")
    # Same email -> same hash -> same token in both outputs.
    token1 = _extract_token(r1.redacted, "email#")
    token2 = _extract_token(r2.redacted, "email#")
    assert token1 and token1 == token2


def test_hashed_phone_is_stable() -> None:
    r1 = redact("call +49 151 23456789")
    r2 = redact("also +49 151 23456789")
    t1 = _extract_token(r1.redacted, "phone#")
    t2 = _extract_token(r2.redacted, "phone#")
    assert t1 and t1 == t2


def test_multiple_entities_are_counted() -> None:
    text = (
        "Contact foo@example.com or bar@example.com, "
        "my card 4111 1111 1111 1111 and ssn 123-45-6789."
    )
    r = redact(text)
    assert r.replaced.get("email") == 2
    assert r.replaced.get("credit_card") == 1
    assert r.replaced.get("ssn") == 1


def test_plain_text_unchanged() -> None:
    r = redact("Hello, is my ticket resolved yet?")
    assert r.redacted == "Hello, is my ticket resolved yet?"
    assert r.replaced == {}


def _extract_token(text: str, prefix: str) -> str | None:
    import re

    m = re.search(rf"\[{re.escape(prefix)}[0-9a-f]+\]", text)
    return m.group(0) if m else None
